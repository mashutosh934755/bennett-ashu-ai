# app.py — Ashu AI (text-only, popup-friendly)

import re
import requests
import feedparser
import streamlit as st

# ---------- APP CONFIG ----------
st.set_page_config(page_title="Ashu AI", page_icon="🔎", layout="centered")

# ===== KEYS FROM SECRETS =====
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
CORE_API_KEY = st.secrets.get("CORE_API_KEY", "")
GOOGLE_BOOKS_API_KEY = st.secrets.get("GOOGLE_BOOKS_API_KEY", "")

# ---------- THEME & LAYOUT CSS ----------
st.markdown(
    """
<style>
  :root { --brand-a:#960820; --brand-b:#0D335E; }

  html,body,.stApp{ background:#fff!important; color:#0D335E!important; color-scheme:light!important; }
  /* narrow, popup-friendly canvas + extra bottom space for input */
  .main .block-container{ max-width:480px; padding:1rem .75rem 6rem .75rem; }

  /* header */
  .profile-container{ text-align:center; margin:.25rem 0 .6rem 0; }
  .profile-container img{
    width:96px;height:96px;border-radius:50%;object-fit:cover;
    border:3px solid var(--brand-b); margin-bottom:.5rem;
  }
  .profile-container h1{
    font-size:1.15rem!important; line-height:1.25; margin:0 .25rem;
    color:var(--brand-b)!important; font-weight:800;
  }

  /* quick actions (2 per row) */
  .quick-actions-row{ display:flex; flex-wrap:wrap; gap:10px; justify-content:center; margin:.4rem 0 1rem 0; }
  .quick-action-btn,
  .quick-action-btn:link,
  .quick-action-btn:visited{
    background:var(--brand-b); color:#fff!important; padding:10px 14px; border-radius:22px; border:0;
    font-size:13px; text-decoration:none!important; box-shadow:0 2px 6px rgba(0,0,0,.08);
    flex:1 1 46%; max-width:46%; text-align:center; display:inline-block;
  }
  .quick-action-btn:hover{ filter:brightness(1.05); transform:translateY(-1px); }

  /* chat input always visible, not obscured */
  .static-chat-input{
    position:sticky; bottom:0; z-index:5;
    background:linear-gradient(to top,#ffffff 70%, rgba(255,255,255,0));
    padding-top:8px; margin-top:16px;
  }
  .stChatInput input{ border-radius:22px!important; padding:10px 16px!important; }
  .stChatInput button{ border-radius:50%!important; background:var(--brand-a)!important; }

  a,.stMarkdown a{ color:var(--brand-a)!important; }

  /* Hide all Streamlit chrome/badges/toolbars/fullscreen */
  #MainMenu, header, footer,
  [data-testid="stToolbar"], [data-testid="stDecoration"],
  [data-testid="stStatusWidget"], .stDeployButton, .stAppDeployButton,
  .viewerBadge_container__1QSob, .viewerBadge_link__1S137,
  a[href*="streamlit.io"], a[href*="Fullscreen"], button[title="View fullscreen"]
  { display:none!important; visibility:hidden!important; height:0!important; overflow:hidden!important; }

  /* Remove any previous bottom mask that could hide the input */
  .stApp::after{ display:none!important; content:none!important; }
</style>
""",
    unsafe_allow_html=True,
)

# ---------- QUICK LINKS ----------
def create_quick_action_button(text: str, url: str) -> str:
    return f'<a href="{url}" target="_blank" class="quick-action-btn">{text}</a>'

def show_quick_actions() -> None:
    quick_actions = [
        ("Find e-Resources", "https://bennett.refread.com/#/home"),
        ("Find Books", "https://libraryopac.bennett.edu.in/"),
        ("Working Hours", "https://library.bennett.edu.in/index.php/working-hours/"),
        ("Book GD Rooms", "http://10.6.0.121/gdroombooking/"),
    ]
    st.markdown(
        '<div class="quick-actions-row">'
        + "".join([create_quick_action_button(t, u) for t, u in quick_actions])
        + "</div>",
        unsafe_allow_html=True,
    )

# ---------- SEARCH HELPERS ----------
def google_books_search(query: str, limit: int = 5):
    if not GOOGLE_BOOKS_API_KEY: return []
    url = f"https://www.googleapis.com/books/v1/volumes?q={query}&maxResults={limit}&key={GOOGLE_BOOKS_API_KEY}"
    try:
        resp = requests.get(url, timeout=10)
        items = resp.json().get("items", [])
        result = []
        for item in items:
            v = item.get("volumeInfo", {})
            result.append({
                "title": v.get("title", "No Title"),
                "authors": ", ".join(v.get("authors", [])),
                "url": v.get("infoLink", "#"),
                "publisher": v.get("publisher", ""),
                "year": v.get("publishedDate", "")[:4],
            })
        return result
    except Exception:
        return []

def core_article_search(query: str, limit: int = 5):
    if not CORE_API_KEY: return []
    url = "https://api.core.ac.uk/v3/search/works"
    headers = {"Authorization": f"Bearer {CORE_API_KEY}"}
    params = {"q": query, "limit": limit}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=15)
        if r.status_code == 200:
            return r.json().get("results", [])
        return []
    except Exception:
        return []

def arxiv_article_search(query: str, limit: int = 5):
    url = f"http://export.arxiv.org/api/query?search_query=all:{query}&start=0&max_results={limit}"
    try:
        feed = feedparser.parse(url)
        out = []
        for e in feed.entries:
            pdfs = [l.href for l in e.links if getattr(l, "type", "") == "application/pdf"]
            out.append({"title": e.title, "url": (pdfs[0] if pdfs else e.link), "year": e.published[:4]})
        return out
    except Exception:
        return []

def doaj_article_search(query: str, limit: int = 5):
    url = f"https://doaj.org/api/search/articles/title:{query}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            arts = resp.json().get("results", [])[:limit]
            out = []
            for art in arts:
                b = art.get("bibjson", {})
                out.append({
                    "title": b.get("title", "No Title"),
                    "url": (b.get("link", [{}])[0].get("url", "#")),
                    "journal": b.get("journal", {}).get("title", ""),
                    "year": b.get("year", ""),
                })
            return out
        return []
    except Exception:
        return []

def datacite_article_search(query: str, limit: int = 5):
    url = f"https://api.datacite.org/dois?query={query}&page[size]={limit}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            out = []
            for item in resp.json().get("data", []):
                a = item.get("attributes", {})
                titles = a.get("titles", [{}])
                out.append({
                    "title": (titles[0].get("title", "No Title") if titles else "No Title"),
                    "url": a.get("url", "#"),
                    "journal": a.get("publisher", ""),
                    "year": a.get("publicationYear", ""),
                })
            return out
        return []
    except Exception:
        return []

# ---------- LLM FALLBACK ----------
def create_payload(prompt: str):
    sys = (
        "You are Ashu, an AI assistant for Bennett University Library. "
        "Provide accurate, concise answers using this info: "
        "- Website: https://library.bennett.edu.in/ "
        "- Timings: Weekdays 8:00–24:00; Weekends/Holidays 9:00–17:00 (check Working Hours page for changes). "
        "- Physical books: https://libraryopac.bennett.edu.in/ "
        "- e-Resources (24/7): https://bennett.refread.com/#/home "
        "- GD Rooms: http://10.6.0.121/gdroombooking/ "
        "FAQs: borrowing via kiosks; returns via 24/7 Drop Box; overdue notices via email or OPAC; "
        "printing/scanning 9:00–17:30 (email libraryhelpdesk@bennett.edu.in for official prints); "
        "alumni reference access; fines via BU Payment Portal; book recommendation form; "
        "holds via OPAC; ILL via DELNET; snacks not allowed; water bottles allowed. "
        f"User question: {prompt}"
    )
    return {"contents": [{"parts": [{"text": sys}]}]}

def call_gemini_api_v2(payload: dict) -> str:
    if not GEMINI_API_KEY:
        return "Gemini API key missing in secrets."
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    try:
        r = requests.post(url, json=payload,
                          headers={"Content-Type":"application/json","X-goog-api-key":GEMINI_API_KEY},
                          timeout=15)
        if r.status_code == 200:
            c = r.json().get("candidates", [{}])
            return c[0].get("content", {}).get("parts", [{}])[0].get("text", "No answer found.")
        return f"Connection error: {r.status_code} - {r.text}"
    except Exception:
        return "A network error occurred. Please try again later."

# ---------- PROMPT PARSING ----------
def get_topic_from_prompt(prompt: str) -> str:
    pattern = r"(?:on|par|about|ke bare mein|पर|के बारे में|का|की)\s+([a-zA-Z0-9\-अ-ह ]+)"
    m = re.search(pattern, prompt, re.IGNORECASE)
    if m: return m.group(1).strip()
    words = prompt.strip().split()
    if len(words) > 1:
        return words[-2] if words[-1].lower() in ["articles","पर","on"] else words[-1]
    return prompt.strip()

def handle_user_query(prompt: str) -> str:
    pl = prompt.lower()

    if "find books on" in pl or "find book on" in pl:
        topic = pl.replace("find books on","").replace("find book on","").strip()
        books = google_books_search(topic, limit=5)
        ans = f"### 📚 Books on **{topic.title()}** (Google Books)\n"
        if books:
            for b in books:
                authors = f" by {b['authors']}" if b['authors'] else ""
                pub = f", {b['publisher']}" if b['publisher'] else ""
                year = f" ({b['year']})" if b['year'] else ""
                ans += f"- [{b['title']}]({b['url']}){authors}{pub}{year}\n"
        else:
            ans += "No relevant books found from Google Books.\n"
        ans += "\n**For more, try [BU OPAC](https://libraryopac.bennett.edu.in/) or [Refread](https://bennett.refread.com/#/home).**"
        return ans

    article_keywords = ["article","articles","research paper","journal","preprint","open access","dataset",
                        "साहित्य","आर्टिकल","पत्रिका","जर्नल","शोध","पेपर"]
    if any(k in pl for k in article_keywords):
        topic = get_topic_from_prompt(prompt)
        if not topic or len(topic)<2:
            return "Please specify a topic. उदाहरण: 'articles on AI' या 'हिंदी साहित्य पर articles'."
        ans = "### 🟦 Bennett University e-Resources (Refread)\n"
        ans += f"Find e-books & journal articles on **'{topic.title()}'** 24/7: [Refread](https://bennett.refread.com/#/home)\n\n"

        gb = google_books_search(topic, 3)
        ans += "### 📚 Books (Google Books)\n"
        if gb:
            for b in gb:
                authors = f" by {b['authors']}" if b['authors'] else ""
                pub = f", {b['publisher']}" if b['publisher'] else ""
                year = f" ({b['year']})" if b['year'] else ""
                ans += f"- [{b['title']}]({b['url']}){authors}{pub}{year}\n"
        else:
            ans += "No relevant books found.\n"

        core = core_article_search(topic, 3)
        ans += "### 🌐 Open Access (CORE)\n"
        if core:
            for a in core:
                title = a.get("title", "No Title")
                url = a.get("downloadUrl", a.get("urls", [{}])[0].get("url", "#"))
                year = a.get("createdDate", "")[:4]
                ans += f"- [{title}]({url}) {'('+year+')' if year else ''}\n"
        else:
            ans += "No recent results on CORE.\n"

        ax = arxiv_article_search(topic, 3)
        ans += "### 📄 Preprints (arXiv)\n"
        if ax:
            for a in ax: ans += f"- [{a['title']}]({a['url']}) ({a['year']})\n"
        else:
            ans += "No recent preprints on arXiv.\n"

        do = doaj_article_search(topic, 3)
        ans += "### 📚 Open Access Journals (DOAJ)\n"
        if do:
            for a in do: ans += f"- [{a['title']}]({a['url']}) ({a['year']}) - {a['journal']}\n"
        else:
            ans += "No open-access journal hits on DOAJ.\n"

        dc = datacite_article_search(topic, 3)
        ans += "### 🏷️ Research Data/Articles (DataCite)\n"
        if dc:
            for a in dc: ans += f"- [{a['title']}]({a['url']}) ({a['year']}) - {a['journal']}\n"
        else:
            ans += "No datasets/articles on DataCite.\n"

        return ans

    return call_gemini_api_v2(create_payload(prompt))

# ---------- UI ----------
def render_app():
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Title (short; “your” removed)
    st.markdown(
        """
        <div class="profile-container">
          <img src="https://library.bennett.edu.in/wp-content/uploads/2024/05/WhatsApp-Image-2024-05-01-at-12.41.02-PM-e1714549052999-150x150.jpeg" />
          <h1>Ashu — AI assistant, Bennett University Library</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )

    show_quick_actions()

    st.markdown(
        '<p style="text-align:center; margin:.5rem 0 1rem 0;">Hello! I am Ashu. How can I help you today?</p>',
        unsafe_allow_html=True,
    )

    # Previous messages
    for m in st.session_state.messages:
        with st.chat_message(m["role"]):
            st.markdown(m["content"], unsafe_allow_html=True)

    # Chat input (sticky)
    st.markdown('<div class="static-chat-input">', unsafe_allow_html=True)
    prompt = st.chat_input("Type your query about books, research papers, journals, library services...")
    st.markdown('</div>', unsafe_allow_html=True)

    if prompt:
        st.session_state.messages.append({"role":"user","content":prompt})
        with st.spinner("Ashu is typing..."):
            answer = handle_user_query(prompt)
        st.session_state.messages.append({"role":"assistant","content":answer})
        st.rerun()

if __name__ == "__main__":
    render_app()
