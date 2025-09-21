# --- Ashu AI: Vapi-style Web Voice Widget (floating mic) ---
# Drop-in upgrade for your existing voice_agent_app.py

import io, re, requests, feedparser, base64
import streamlit as st

# ===== Optional Voice I/O libs =====
try:
    from audio_recorder_streamlit import audio_recorder  # custom mic widget
except Exception:
    audio_recorder = None

try:
    from streamlit_TTS import text_to_speech  # TTS playback
except Exception:
    text_to_speech = None

try:
    import speech_recognition as sr  # STT
except Exception:
    sr = None

# ===== Secrets (unchanged) =====
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
CORE_API_KEY = st.secrets.get("CORE_API_KEY", "")
GOOGLE_BOOKS_API_KEY = st.secrets.get("GOOGLE_BOOKS_API_KEY", "")

# ====== Styles: page + floating voice bubble (Vapi-like) ======
st.markdown("""
<style>
:root { --ashu:#2e86c1; }
.main .block-container{max-width:900px;padding:2rem 1rem;}
.profile-container{text-align:center;margin-bottom:1rem;}
.quick-actions-row{display:flex;justify-content:center;gap:10px;margin:1rem 0 2rem;width:100%;}
.quick-action-btn{background:var(--ashu);color:#fff!important;padding:10px 15px;border-radius:20px;border:none;box-shadow:0 2px 5px rgba(0,0,0,.1);transition:.3s;font-size:14px;text-decoration:none;text-align:center;cursor:pointer;white-space:nowrap;flex:1;max-width:200px;}
.quick-action-btn:hover{transform:translateY(-2px);box-shadow:0 4px 8px rgba(0,0,0,.15);}
.static-chat-input{position:fixed;bottom:80px;left:50%;transform:translateX(-50%);width:100%;max-width:800px;z-index:90;}
.stChatInput input{border-radius:25px!important;padding:12px 20px!important;}
.stChatInput button{border-radius:50%!important;background:var(--ashu)!important;}
.footer{position:fixed;bottom:0;left:0;right:0;text-align:center;color:#666;padding:1rem;background:#fff;z-index:80;}

 /* --- Floating mic bubble --- */
.voice-fab{
  position:fixed;right:24px;bottom:96px;z-index:120;
  width:62px;height:62px;border-radius:50%;
  display:flex;align-items:center;justify-content:center;
  background:var(--ashu);color:#fff;box-shadow:0 10px 25px rgba(46,134,193,.35);
  cursor:pointer;transition:transform .08s ease-in-out;user-select:none;
}
.voice-fab:hover{transform:scale(1.04);}
.voice-fab .pulse{position:absolute;width:62px;height:62px;border-radius:50%;box-shadow:0 0 0 0 rgba(46,134,193,.5);animation:pulse 1.6s infinite;}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(46,134,193,.45)}70%{box-shadow:0 0 0 18px rgba(46,134,193,0)}100%{box-shadow:0 0 0 0 rgba(46,134,193,0)}}
.voice-sheet{
  position:fixed;right:24px;bottom:170px;max-width:360px;width:calc(100vw - 48px);
  background:#fff;border:1px solid #e7eef6;border-radius:16px;padding:12px 14px;
  box-shadow:0 12px 36px rgba(0,0,0,.12);z-index:121;font-size:.95rem;
}
.voice-row{display:flex;align-items:center;gap:10px;}
.badge{font-size:.76rem;background:#eef6fc;color:#1f6ca1;padding:4px 8px;border-radius:999px;}
.partial{margin-top:8px;color:#444;min-height:20px;font-style:italic;}
.err{margin-top:6px;color:#b00020;font-size:.85rem;}
@media(max-width:700px){.main .block-container{padding:.5rem .2rem}}
</style>
""", unsafe_allow_html=True)

# ====== Quick links UI ======
def create_quick_action_button(text, url):
    return f'<a href="{url}" target="_blank" class="quick-action-btn">{text}</a>'

def show_quick_actions():
    quick_actions = [
        ("Find e-Resources", "https://bennett.refread.com/#/home"),
        ("Find Books", "https://libraryopac.bennett.edu.in/"),
        ("Working Hours", "https://library.bennett.edu.in/index.php/working-hours/"),
        ("Book GD Rooms", "http://10.6.0.121/gdroombooking/"),
    ]
    st.markdown(
        '<div class="quick-actions-row">' +
        "".join([create_quick_action_button(t, u) for t, u in quick_actions]) +
        '</div>',
        unsafe_allow_html=True
    )

# ====== External APIs (same as before) ======
def google_books_search(query, limit=5):
    if not GOOGLE_BOOKS_API_KEY: return []
    url = f"https://www.googleapis.com/books/v1/volumes?q={query}&maxResults={limit}&key={GOOGLE_BOOKS_API_KEY}"
    try:
        resp = requests.get(url, timeout=12)
        items = resp.json().get("items", [])
        out = []
        for it in items:
            v = it.get("volumeInfo", {})
            out.append({
                "title": v.get("title","No Title"),
                "authors": ", ".join(v.get("authors",[])),
                "url": v.get("infoLink","#"),
                "publisher": v.get("publisher",""),
                "year": v.get("publishedDate","")[:4]
            })
        return out
    except Exception:
        return []

def core_article_search(query, limit=5):
    if not CORE_API_KEY: return []
    url = "https://api.core.ac.uk/v3/search/works"
    headers = {"Authorization": f"Bearer {CORE_API_KEY}"}
    params = {"q": query, "limit": limit}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=15)
        return r.json().get("results", []) if r.status_code==200 else []
    except Exception:
        return []

def arxiv_article_search(query, limit=5):
    url = f"http://export.arxiv.org/api/query?search_query=all:{query}&start=0&max_results={limit}"
    try:
        feed = feedparser.parse(url)
        out=[]
        for e in feed.entries:
            pdfs = [l.href for l in e.links if getattr(l,"type","")=="application/pdf"]
            out.append({"title": e.title, "url": (pdfs[0] if pdfs else e.link), "year": e.published[:4]})
        return out
    except Exception:
        return []

def doaj_article_search(query, limit=5):
    url = f"https://doaj.org/api/search/articles/title:{query}"
    try:
        r = requests.get(url, timeout=12)
        if r.status_code!=200: return []
        res = []
        for art in r.json().get("results", [])[:limit]:
            b = art.get("bibjson", {})
            res.append({
                "title": b.get("title","No Title"),
                "url": (b.get("link",[{}])[0].get("url","#")),
                "journal": b.get("journal",{}).get("title",""),
                "year": b.get("year","")
            })
        return res
    except Exception:
        return []

def datacite_article_search(query, limit=5):
    url = f"https://api.datacite.org/dois?query={query}&page[size]={limit}"
    try:
        r = requests.get(url, timeout=12)
        if r.status_code!=200: return []
        out=[]
        for item in r.json().get("data", []):
            a=item.get("attributes",{})
            title = (a.get("titles",[{}])[0].get("title","No Title") if a.get("titles") else "No Title")
            out.append({"title": title, "url": a.get("url","#"), "journal": a.get("publisher",""), "year": a.get("publicationYear","")})
        return out
    except Exception:
        return []

# ====== LLM (Gemini) ======
def create_payload(prompt):
    sys = (
        "You are Ashu, an AI assistant for Bennett University Library. "
        "Provide accurate and concise answers based on the following FAQ and library information. "
        "Key information: "
        "- Library website: https://library.bennett.edu.in/. "
        "- Library timings: Weekdays 8:00 AM to 12:00 AM (midnight), Weekends & Holidays 9:00 AM to 5:00 PM (may vary during vacations, check https://library.bennett.edu.in/index.php/working-hours/). "
        "- Physical book search: Use https://libraryopac.bennett.edu.in/. "
        "- e-Resources: Access at https://bennett.refread.com/#/home. "
        "- Group Discussion Rooms: http://10.6.0.121/gdroombooking/. "
        "FAQ highlights: borrowing/returns/drop box/overdue/printing/alumni/holds/ILL, etc. "
        f"User question: {prompt}"
    )
    return {"contents":[{"parts":[{"text":sys}]}]}

def call_gemini_api_v2(payload)->str:
    if not GEMINI_API_KEY: return "Gemini API Key is missing. Please set it in Streamlit secrets."
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    try:
        r = requests.post(url, json=payload, headers={"Content-Type":"application/json","X-goog-api-key":GEMINI_API_KEY}, timeout=15)
        if r.status_code==200:
            cand = r.json().get("candidates",[{}])
            return cand[0].get("content",{}).get("parts",[{}])[0].get("text","No answer found.")
        return f"Connection error: {r.status_code} - {r.text}"
    except Exception:
        return "A network error occurred. Please try again later."

# ====== NLP routing ======
def get_topic_from_prompt(prompt:str)->str:
    pattern = r"(?:on|par|about|ke bare mein|पर|के बारे में|का|की)\\s+([a-zA-Z0-9\\-अ-ह ]+)"
    m = re.search(pattern, prompt, re.IGNORECASE)
    if m: return m.group(1).strip()
    words = prompt.strip().split()
    if len(words)>1: return words[-2] if words[-1].lower() in ["articles","पर","on"] else words[-1]
    return prompt.strip()

def handle_user_query(prompt:str)->str:
    # Book search
    if "find books on" in prompt.lower() or "find book on" in prompt.lower():
        topic = prompt.lower().replace("find books on","").replace("find book on","").strip()
        books = google_books_search(topic, 5)
        ans = f"### 📚 Books on **{topic.title()}** (Google Books)\n"
        if books:
            for b in books:
                authors = f" by {b['authors']}" if b['authors'] else ""
                pub = f", {b['publisher']}" if b['publisher'] else ""
                year = f" ({b['year']})" if b['year'] else ""
                ans += f"- [{b['title']}]({b['url']}){authors}{pub}{year}\n"
        else:
            ans += "No relevant books found from Google Books.\n"
        ans += "\n**For more, search [BU OPAC](https://libraryopac.bennett.edu.in/) or [Refread](https://bennett.refread.com/#/home).**"
        return ans

    # Articles
    article_keywords = ["article","articles","research paper","journal","preprint","open access","dataset","साहित्य","आर्टिकल","पत्रिका","जर्नल","शोध","पेपर"]
    if any(kw in prompt.lower() for kw in article_keywords):
        topic = get_topic_from_prompt(prompt)
        if not topic or len(topic)<2:
            return "Please specify a topic for article search. उदाहरण: 'articles on AI' या 'हिंदी साहित्य पर articles'।"
        ans = f"### 🟦 Bennett University e-Resources (Refread)\n"
        ans += f"Find e-books and journal articles on **'{topic.title()}'** 24/7 here: [Refread](https://bennett.refread.com/#/home)\n\n"

        gb = google_books_search(topic,3)
        ans += "### 📚 Books from Google Books\n"
        if gb:
            for b in gb:
                authors = f" by {b['authors']}" if b['authors'] else ""
                pub = f", {b['publisher']}" if b['publisher'] else ""
                year = f" ({b['year']})" if b['year'] else ""
                ans += f"- [{b['title']}]({b['url']}){authors}{pub}{year}\n"
        else:
            ans += "No relevant books found from Google Books.\n"

        core = core_article_search(topic,3)
        ans += "### 🌐 Open Access (CORE)\n"
        if core:
            for a in core:
                title = a.get("title","No Title")
                url = a.get("downloadUrl", a.get("urls",[{}])[0].get("url","#"))
                year = a.get("createdDate","")[:4]
                ans += f"- [{title}]({url}) {'('+year+')' if year else ''}\n"
        else:
            ans += "No recent articles found on this topic from CORE.\n"

        ax = arxiv_article_search(topic,3)
        ans += "### 📄 Preprints (arXiv)\n"
        if ax:
            for a in ax: ans += f"- [{a['title']}]({a['url']}) ({a['year']})\n"
        else:
            ans += "No recent preprints found on this topic from arXiv.\n"

        dj = doaj_article_search(topic,3)
        ans += "### 📚 Open Access Journals (DOAJ)\n"
        if dj:
            for a in dj: ans += f"- [{a['title']}]({a['url']}) ({a['year']}) - {a['journal']}\n"
        else:
            ans += "No open access journal articles found on this topic from DOAJ.\n"

        dc = datacite_article_search(topic,3)
        ans += "### 🏷️ Research Data/Articles (DataCite)\n"
        if dc:
            for a in dc: ans += f"- [{a['title']}]({a['url']}) ({a['year']}) - {a['journal']}\n"
        else:
            ans += "No research datasets/articles found on this topic from DataCite.\n"
        return ans

    # Fallback to Gemini
    return call_gemini_api_v2(create_payload(prompt))

# ====== STT + TTS helpers ======
def transcribe_audio(audio_bytes: bytes) -> str:
    if sr is None: return ""
    recog = sr.Recognizer()
    try:
        with sr.AudioFile(io.BytesIO(audio_bytes)) as src:
            audio_data = recog.record(src)
            return recog.recognize_google(audio_data)  # quick free recognizer
    except Exception:
        return ""

def speak_text(text: str):
    if text_to_speech is None: return
    try:
        text_to_speech(text=text, language="en", wait=False)
    except Exception:
        pass

# ====== UI ======
def page_header():
    st.markdown("""
    <div class="profile-container">
        <img src="https://library.bennett.edu.in/wp-content/uploads/2024/05/WhatsApp-Image-2024-05-01-at-12.41.02-PM-e1714549052999-150x150.jpeg" 
             width="150" style="border-radius:50%; border:3px solid var(--ashu); margin-bottom:1rem;">
        <h1 style="color:var(--ashu); margin-bottom:.5rem; font-size:2em;">Ashu AI Assistant at Bennett University Library</h1>
    </div>
    """, unsafe_allow_html=True)
    show_quick_actions()
    st.markdown('<div style="text-align:center;margin:2rem 0;"><p style="font-size:1.05em;">Hello! I am Ashu, your AI assistant at Bennett University Library. How can I help you today?</p></div>', unsafe_allow_html=True)

def render_messages():
    if "messages" not in st.session_state:
        st.session_state.messages=[]
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"], unsafe_allow_html=True)

def push_message(role, content):
    st.session_state.messages.append({"role": role, "content": content})

def voice_bubble():
    """Floating mic bubble + small sheet (Vapi-like)."""
    # state
    if "voice_open" not in st.session_state: st.session_state.voice_open=False
    if "partial_tx" not in st.session_state: st.session_state.partial_tx=""

    # Bubble HTML
    st.markdown("""
    <div class="voice-fab" onclick="window.dispatchEvent(new Event('open-voice'))" title="Speak">
      <div class="pulse"></div>
      <svg width="26" height="26" viewBox="0 0 24 24" fill="none">
        <path d="M12 14a3 3 0 0 0 3-3V7a3 3 0 0 0-6 0v4a3 3 0 0 0 3 3Z" stroke="white" stroke-width="2"/>
        <path d="M19 11v1a7 7 0 0 1-14 0v-1M12 19v3" stroke="white" stroke-width="2" />
      </svg>
    </div>
    """, unsafe_allow_html=True)

    # Tiny script to flip a boolean in session via query param trick
    st.markdown("""
    <script>
    window.addEventListener('open-voice', () => {
      const url = new URL(window.location.href);
      const k = url.searchParams.get('voice') === '1' ? '0' : '1';
      url.searchParams.set('voice', k);
      window.location.href = url.toString();
    });
    </script>
    """, unsafe_allow_html=True)

    # Read the param
    voice_param = st.query_params.get("voice")
    if voice_param == "1":
        st.session_state.voice_open = True
    elif voice_param == "0":
        st.session_state.voice_open = False

    # Voice sheet
    if st.session_state.voice_open:
        st.markdown('<div class="voice-sheet">', unsafe_allow_html=True)
        st.markdown('<div class="voice-row"><span class="badge">Listening</span><span>Press & speak…</span></div>', unsafe_allow_html=True)

        audio_bytes=None
        # Prefer custom component for snappy UX
        if audio_recorder is not None:
            audio_bytes = audio_recorder(text="", recording_color="#e8b62c", neutral_color="#2e86c1", icon_name="microphone", icon_size="2x")
        else:
            try:
                up = st.audio_input("Record a voice message")  # Streamlit built-in
                if up: audio_bytes = up.getvalue()
            except Exception:
                pass

        if audio_bytes:
            # transcribe
            transcript = transcribe_audio(audio_bytes)
            st.session_state.partial_tx = transcript[:120] + ("…" if len(transcript)>120 else "")
            if transcript:
                push_message("user", transcript)
                with st.spinner("Thinking…"):
                    ans = handle_user_query(transcript)
                push_message("assistant", ans)
                speak_text(ans)
                # close the sheet by toggling query param
                st.query_params["voice"]="0"
                st.rerun()
            else:
                st.markdown('<div class="err">Could not recognize speech. Please try again.</div>', unsafe_allow_html=True)

        st.markdown(f'<div class="partial">{st.session_state.partial_tx}</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

def main():
    page_header()
    render_messages()
    # Floating mic bubble
    voice_bubble()

    # Text chat input (fixed)
    st.markdown('<div class="static-chat-input">', unsafe_allow_html=True)
    prompt = st.chat_input("Type your query about books, research papers, journals, library services…")
    if prompt:
        push_message("user", prompt)
        with st.spinner("Thinking…"):
            ans = handle_user_query(prompt)
        push_message("assistant", ans)
        speak_text(ans)
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="footer">© 2025 - Ashutosh Mishra | All Rights Reserved</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
