# app.py — Ashu AI (light-only, iframe-safe, badge-free)

import streamlit as st
import requests, re, feedparser  # pip install feedparser

# ==== KEYS ====
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
CORE_API_KEY = st.secrets.get("CORE_API_KEY", "")
GOOGLE_BOOKS_API_KEY = st.secrets.get("GOOGLE_BOOKS_API_KEY", "")

# ==== HARD CSS: force light + hide all chrome (robust) ====
st.markdown("""
<style>
  :root{ --brand-a:#960820; --brand-b:#0D335E; }

  html, body, .stApp{ background:#fff !important; color:#0D335E !important; color-scheme:light !important; }
  .main .block-container{ max-width:460px; padding:1rem .75rem; }

  .profile-container{ text-align:center; margin:.25rem 0 .5rem 0; }
  .profile-container img{ width:110px; height:auto; border-radius:50%; border:3px solid var(--brand-b); margin-bottom:.5rem; }
  .profile-container h1{ color:var(--brand-b) !important; font-size:1.28rem !important; line-height:1.25; margin:0 .25rem; }

  .quick-actions-row{ display:flex; flex-wrap:wrap; justify-content:center; gap:8px; margin:.5rem 0 1rem 0; width:100%; }
  .quick-action-btn{
    background:var(--brand-b); color:#fff !important; padding:8px 12px; border-radius:18px; border:0;
    box-shadow:0 2px 5px rgba(0,0,0,.08); transition:all .2s; font-size:13px; text-decoration:none; text-align:center;
    cursor:pointer; white-space:nowrap; flex:1 1 46%; max-width:46%;
  }
  .quick-action-btn:hover{ transform:translateY(-1px); box-shadow:0 4px 8px rgba(0,0,0,.12); }
  @media (max-width:400px){ .quick-action-btn{ flex:1 1 100%; max-width:100%; } }

  .static-chat-input{ position:unset !important; }
  .stChatInput input{ border-radius:24px !important; padding:10px 16px !important; }
  .stChatInput button{ border-radius:50% !important; background:var(--brand-b) !important; }
  a, .stMarkdown a{ color:var(--brand-a) !important; }

  /* HIDE Streamlit chrome (multiple selectors for future-proofing) */
  #MainMenu, header, footer,
  [data-testid="stToolbar"], [data-testid="stDecoration"],
  .viewerBadge_container__1QSob, .viewerBadge_link__1S137,
  .stApp a[href*="streamlit.io"], .stApp a[href*="Fullscreen"],
  .stDeployButton, .stAppDeployButton,
  button[title="View fullscreen"],
  [data-testid="stStatusWidget"] { display:none !important; visibility:hidden !important; height:0 !important; }

  /* Bottom white cover just in case */
  .stApp::after{ content:""; position:fixed; left:0; right:0; bottom:0; height:84px; background:#fff; pointer-events:none; z-index:999; }

  html, body, .stApp{ overflow-x:hidden; }
</style>

<!-- JS guard: remove any badge/fullscreen injected later -->
<script>
(function(){
  const kill=()=>{
    const sel=[
      'footer','[data-testid="stToolbar"]','[data-testid="stDecoration"]',
      '.viewerBadge_container__1QSob','.viewerBadge_link__1S137',
      'a[href*="streamlit.io"]','a[href*="Fullscreen"]','button[title="View fullscreen"]',
      '.stDeployButton','.stAppDeployButton','[data-testid="stStatusWidget"]'
    ];
    sel.forEach(s => document.querySelectorAll(s).forEach(n => { n.style.display='none'; n.remove?.(); }));
  };
  new MutationObserver(kill).observe(document.documentElement,{subtree:true,childList:true});
  window.addEventListener('load',kill); kill();
})();
</script>
""", unsafe_allow_html=True)

# ==== QUICK ACTION BUTTONS ====
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
        '</div>', unsafe_allow_html=True
    )

# ==== SEARCH HELPERS ====
def google_books_search(query, limit=5):
    if not GOOGLE_BOOKS_API_KEY: return []
    url = f"https://www.googleapis.com/books/v1/volumes?q={query}&maxResults={limit}&key={GOOGLE_BOOKS_API_KEY}"
    try:
        resp = requests.get(url, timeout=10)
        items = resp.json().get("items", []) or []
        out=[]
        for it in items:
            v=it.get("volumeInfo", {}) or {}
            out.append({
                "title": v.get("title","No Title"),
                "authors": ", ".join(v.get("authors",[]) or []),
                "url": v.get("infoLink","#"),
                "publisher": v.get("publisher",""),
                "year": (v.get("publishedDate","") or "")[:4]
            })
        return out
    except Exception:
        return []

def core_article_search(query, limit=5):
    if not CORE_API_KEY: return []
    try:
        r = requests.get("https://api.core.ac.uk/v3/search/works",
                         headers={"Authorization": f"Bearer {CORE_API_KEY}"},
                         params={"q": query, "limit": limit}, timeout=15)
        return r.json().get("results", []) if r.status_code==200 else []
    except Exception:
        return []

def arxiv_article_search(query, limit=5):
    try:
        feed = feedparser.parse(f"http://export.arxiv.org/api/query?search_query=all:{query}&start=0&max_results={limit}")
        out=[]
        for e in getattr(feed,"entries",[]):
            pdf=[l.href for l in e.links if l.type=="application/pdf"]
            out.append({"title":e.title,"url":(pdf[0] if pdf else e.link),"year":e.published[:4]})
        return out
    except Exception:
        return []

def doaj_article_search(query, limit=5):
    try:
        r = requests.get(f"https://doaj.org/api/search/articles/title:{query}", timeout=10)
        if r.status_code!=200: return []
        arts=(r.json().get("results",[]) or [])[:limit]; out=[]
        for a in arts:
            b=a.get("bibjson",{}) or {}
            out.append({
              "title": b.get("title","No Title"),
              "url": (b.get("link",[{}]) or [{}])[0].get("url","#"),
              "journal": (b.get("journal",{}) or {}).get("title",""),
              "year": b.get("year","")
            })
        return out
    except Exception:
        return []

def datacite_article_search(query, limit=5):
    try:
        r = requests.get(f"https://api.datacite.org/dois?query={query}&page[size]={limit}", timeout=10)
        if r.status_code!=200: return []
        out=[]
        for d in r.json().get("data",[]) or []:
            a=d.get("attributes",{}) or {}
            t=(a.get("titles",[{}]) or [{}])[0].get("title","No Title")
            out.append({"title":t,"url":a.get("url","#"),"journal":a.get("publisher",""),"year":a.get("publicationYear","")})
        return out
    except Exception:
        return []

# ==== LLM ====
def create_payload(prompt:str):
    sys = (
        "You are Ashu, an AI assistant for Bennett University Library. "
        "Provide accurate and concise answers based on the following FAQ and library information. "
        "Key information: "
        "- Library website: https://library.bennett.edu.in/. "
        "- Library timings: Weekdays 8:00 AM to 12:00 AM (midnight), Weekends & Holidays 9:00 AM to 5:00 PM (may vary during vacations, check https://library.bennett.edu.in/index.php/working-hours/). "
        "- Physical book search: Use https://libraryopac.bennett.edu.in/. "
        "- e-Resources: https://bennett.refread.com/#/home. "
        "- Group Discussion Rooms: http://10.6.0.121/gdroombooking/. "
        "FAQ points: borrowing/return/overdues/printing/alumni/holds/fines/ILL/snacks etc. "
        f"User question: {prompt}"
    )
    return {"contents":[{"parts":[{"text":sys}]}]}

def call_gemini_api_v2(payload:dict)->str:
    if not GEMINI_API_KEY: return "Gemini API Key is missing. Please set it in Streamlit secrets."
    try:
        r = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
            json=payload, headers={"Content-Type":"application/json","X-goog-api-key":GEMINI_API_KEY}, timeout=15
        )
        if r.status_code==200:
            cand=r.json().get("candidates",[{}])
            return cand[0].get("content",{}).get("parts",[{}])[0].get("text","No answer found.")
        return f"Connection error: {r.status_code} - {r.text}"
    except Exception:
        return "A network error occurred. Please try again later."

# ==== Helpers & router ====
def get_topic_from_prompt(p:str)->str:
    m=re.search(r"(?:on|par|about|ke bare mein|पर|के बारे में|का|की)\\s+([a-zA-Z0-9\\-अ-ह ]+)", p, re.IGNORECASE)
    if m: return m.group(1).strip()
    w=p.strip().split()
    return (w[-2] if len(w)>1 and w[-1].lower() in ["articles","पर","on"] else w[-1]) if w else p.strip()

def handle_user_query(prompt:str)->str:
    if "find books on" in prompt.lower() or "find book on" in prompt.lower():
        topic = (prompt.lower().replace("find books on","").replace("find book on","").strip())
        books = google_books_search(topic, 5)
        ans = f"### 📚 Books on **{topic.title()}** (Google Books)\\n"
        if books:
            for b in books:
                authors=f" by {b['authors']}" if b['authors'] else ""
                pub=f", {b['publisher']}" if b['publisher'] else ""
                year=f" ({b['year']})" if b['year'] else ""
                ans += f"- [{b['title']}]({b['url']}){authors}{pub}{year}\\n"
        else:
            ans += "No relevant books found from Google Books.\\n"
        ans += "\\n**For more, search [BU OPAC](https://libraryopac.bennett.edu.in/) or [Refread](https://bennett.refread.com/#/home).**"
        return ans

    kws=["article","articles","research paper","journal","preprint","open access","dataset","साहित्य","आर्टिकल","पत्रिका","जर्नल","शोध","पेपर"]
    if any(k in prompt.lower() for k in kws):
        topic=get_topic_from_prompt(prompt)
        if not topic or len(topic)<2: return "Please specify a topic for article search. उदाहरण: 'articles on AI' या 'हिंदी साहित्य पर articles'।"
        topic=topic.strip()

        ans = "### 🟦 Bennett University e-Resources (Refread)\\n"
        ans += f"Find e-books and journal articles on **'{topic.title()}'** 24/7 here: [Refread](https://bennett.refread.com/#/home)\\n\\n"

        g=google_books_search(topic,3); ans += "### 📚 Books from Google Books\\n"
        if g:
            for b in g:
                authors=f" by {b['authors']}" if b['authors'] else ""
                pub=f", {b['publisher']}" if b['publisher'] else ""
                year=f" ({b['year']})" if b['year'] else ""
                ans += f"- [{b['title']}]({b['url']}){authors}{pub}{year}\\n"
        else: ans += "No relevant books found from Google Books.\\n"

        c=core_article_search(topic,3); ans += "### 🌐 Open Access (CORE)\\n"
        if c:
            for a in c:
                title=a.get("title","No Title")
                url=a.get("downloadUrl",(a.get("urls",[{}]) or [{}])[0].get("url","#"))
                year=(a.get("createdDate","") or "")[:4]
                ans += f"- [{title}]({url}) {'('+year+')' if year else ''}\\n"
        else: ans += "No recent articles found on this topic from CORE.\\n"

        ax=arxiv_article_search(topic,3); ans += "### 📄 Preprints (arXiv)\\n"
        if ax:
            for a in ax: ans += f"- [{a['title']}]({a['url']}) ({a['year']})\\n"
        else: ans += "No recent preprints found on this topic from arXiv.\\n"

        dj=doaj_article_search(topic,3); ans += "### 📚 Open Access Journals (DOAJ)\\n"
        if dj:
            for a in dj: ans += f"- [{a['title']}]({a['url']}) ({a['year']}) - {a['journal']}\\n"
        else: ans += "No open access journal articles found on this topic from DOAJ.\\n"

        dc=datacite_article_search(topic,3); ans += "### 🏷️ Research Data/Articles (DataCite)\\n"
        if dc:
            for a in dc: ans += f"- [{a['title']}]({a['url']}) ({a['year']}) - {a['journal']}\\n"
        else: ans += "No research datasets/articles found on this topic from DataCite.\\n"

        return ans

    return call_gemini_api_v2(create_payload(prompt))

# ==== UI ====
if "messages" not in st.session_state:
    st.session_state.messages = []

st.markdown("""
<div class="profile-container">
  <img src="https://library.bennett.edu.in/wp-content/uploads/2024/05/WhatsApp-Image-2024-05-01-at-12.41.02-PM-e1714549052999-150x150.jpeg" />
  <!-- SHORT TITLE (your removed) -->
  <h1>Ashu — AI assistant, Bennett University Library</h1>
</div>
""", unsafe_allow_html=True)

show_quick_actions()

st.markdown("""
<div style="text-align:center;margin:1rem 0 .5rem 0;">
  <p style="font-size:1rem;color:#0D335E;">Hello! I am Ashu. How can I help you today?</p>
</div>
""", unsafe_allow_html=True)

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])

st.markdown('<div class="static-chat-input">', unsafe_allow_html=True)
prompt = st.chat_input("Type your query about books, research papers, journals, library services...")
if prompt:
    st.session_state.messages.append({"role":"user","content":prompt})
    with st.spinner("Ashu is typing..."):
        ans = handle_user_query(prompt)
    st.session_state.messages.append({"role":"assistant","content":ans})
    st.rerun()
st.markdown('</div>', unsafe_allow_html=True)
