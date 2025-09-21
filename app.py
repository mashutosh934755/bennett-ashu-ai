# app.py  — Ashu (text-only, polished UI)

import re
import requests
import feedparser
import streamlit as st

# ==== KEYS ====
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
CORE_API_KEY = st.secrets.get("CORE_API_KEY", "")
GOOGLE_BOOKS_API_KEY = st.secrets.get("GOOGLE_BOOKS_API_KEY", "")

# ==== THEME / CSS ====
st.set_page_config(page_title="Ashu — AI assistant", page_icon="🤖", layout="centered")

st.markdown("""
<style>
:root{
  --brand-a:#960820; /* primary */
  --brand-b:#0D335E; /* secondary */
}

/* Kill Streamlit footer / toolbar / viewer badge everywhere */
footer, [data-testid="stStatusWidget"], [data-testid="stToolbar"],
.viewerBadge_container__*, .viewerBadge_link__*, .viewerBadge___,
a[href*="streamlit.io"], div:has(> a[href*="streamlit.io"]) {
  display:none !important; visibility:hidden !important; height:0 !important;
}

/* App shell */
.main .block-container { max-width: 950px; padding: 1.2rem 1rem 7rem; } /* bottom padding for our custom footer */
.profile-container { text-align:center; margin: 0.5rem 0 1rem; }
.profile-container img{ border-radius:50%; border:3px solid var(--brand-b); }

/* Title */
h1.app-title{
  margin: .25rem 0 1.25rem;
  color: var(--brand-b);
  font-weight: 800; font-size: clamp(20px, 2.6vw, 30px);
  text-align: center;
}

/* Quick actions – two-by-two grid that never overflows */
.quick-actions{
  margin: 10px auto 18px; width: 100%; display: grid; gap: 14px;
  grid-template-columns: repeat(2, minmax(200px,1fr));
}
@media (max-width: 560px){
  .quick-actions{ grid-template-columns: 1fr; }
}
.quick-actions a{
  display:inline-flex; align-items:center; justify-content:center;
  background: var(--brand-b); color:#fff !important; text-decoration:none;
  padding: 14px 16px; border-radius: 22px; font-weight: 700;
  box-shadow: 0 8px 18px rgba(13,51,94,.18);
  transition: transform .15s ease, box-shadow .15s ease;
}
.quick-actions a:hover{ transform: translateY(-2px); box-shadow: 0 10px 22px rgba(13,51,94,.24); }

/* Chat input pinned look */
.stChatInput > div > div{ border-radius: 24px !important; }
.stChatInput button{
  border-radius: 50% !important;
  background: var(--brand-b) !important;
}

/* Cards / message body spacing */
.chat-intro{ text-align:center; color: var(--brand-b); margin: 12px 0 8px; font-weight:600; }

/* Make sure the first input is not pushed off-screen in small iframes */
@media (max-height: 700px){
  .main .block-container{ padding-top: .5rem; }
}

/* Custom sticky footer */
.custom-footer{
  position: fixed; left:0; right:0; bottom:0;
  background:#fff; border-top:1px solid #eef1f5;
  text-align:center; padding:.7rem .5rem; z-index: 9999;
  color: var(--brand-b); font-weight:700;
}
</style>
""", unsafe_allow_html=True)

# ==== UI HEADER ====
st.markdown(
    """
    <div class="profile-container">
      <img src="https://library.bennett.edu.in/wp-content/uploads/2024/05/WhatsApp-Image-2024-05-01-at-12.41.02-PM-e1714549052999-150x150.jpeg"
           width="120" alt="Ashu">
      <h1 class="app-title">Ashu — AI assistant, Bennett University Library</h1>
    </div>
    """,
    unsafe_allow_html=True,
)

# ==== QUICK ACTIONS ====
def qa_button(text: str, url: str) -> str:
    return f'<a href="{url}" target="_blank" rel="noopener">{text}</a>'

st.markdown(
    '<div class="quick-actions">' +
    qa_button("Find e-Resources", "https://bennett.refread.com/#/home") +
    qa_button("Find Books", "https://libraryopac.bennett.edu.in/") +
    qa_button("Working Hours", "https://library.bennett.edu.in/index.php/working-hours/") +
    qa_button("Book GD Rooms", "http://10.6.0.121/gdroombooking/") +
    '</div>',
    unsafe_allow_html=True
)

st.markdown('<div class="chat-intro">Hello! I am Ashu. How can I help you today?</div>', unsafe_allow_html=True)

# ==== DATA HELPERS ====
def google_books_search(query: str, limit: int = 5):
    if not GOOGLE_BOOKS_API_KEY:
        return []
    url = f"https://www.googleapis.com/books/v1/volumes?q={query}&maxResults={limit}&key={GOOGLE_BOOKS_API_KEY}"
    try:
        r = requests.get(url, timeout=12)
        items = r.json().get("items", [])
        out = []
        for it in items:
            v = it.get("volumeInfo", {})
            out.append({
                "title": v.get("title", "No Title"),
                "authors": ", ".join(v.get("authors", [])),
                "url": v.get("infoLink", "#"),
                "publisher": v.get("publisher", ""),
                "year": (v.get("publishedDate","")[:4] if v.get("publishedDate") else "")
            })
        return out
    except Exception:
        return []

def core_article_search(query: str, limit: int = 5):
    if not CORE_API_KEY:
        return []
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
        data = []
        for e in feed.entries:
            pdfs = [l.href for l in e.links if l.type == "application/pdf"]
            data.append({"title": e.title, "url": (pdfs[0] if pdfs else e.link), "year": e.published[:4]})
        return data
    except Exception:
        return []

def doaj_article_search(query: str, limit: int = 5):
    url = f"https://doaj.org/api/search/articles/title:{query}"
    try:
        r = requests.get(url, timeout=12)
        if r.status_code == 200:
            items = r.json().get("results", [])[:limit]
            out = []
            for a in items:
                b = a.get("bibjson", {})
                out.append({
                    "title": b.get("title", "No Title"),
                    "url": (b.get("link", [{}])[0].get("url", "#")),
                    "journal": b.get("journal", {}).get("title", ""),
                    "year": b.get("year","")
                })
            return out
        return []
    except Exception:
        return []

def datacite_article_search(query: str, limit: int = 5):
    url = f"https://api.datacite.org/dois?query={query}&page[size]={limit}"
    try:
        r = requests.get(url, timeout=12)
        if r.status_code == 200:
            out = []
            for d in r.json().get("data", []):
                a = d.get("attributes", {})
                title = (a.get("titles",[{}])[0].get("title","No Title"))
                out.append({
                    "title": title,
                    "url": a.get("url", "#"),
                    "journal": a.get("publisher", ""),
                    "year": a.get("publicationYear", "")
                })
            return out
        return []
    except Exception:
        return []

def create_payload(prompt: str):
    system_instruction = (
        "You are Ashu, an AI assistant for Bennett University Library. "
        "Provide accurate and concise answers using the library info. "
        "Key links: Library website https://library.bennett.edu.in/ ; OPAC https://libraryopac.bennett.edu.in/ ; "
        "e-Resources https://bennett.refread.com/#/home ; GD Rooms http://10.6.0.121/gdroombooking/ . "
        f"User question: {prompt}"
    )
    return {"contents":[{"parts":[{"text":system_instruction}]}]}

def call_gemini_api_v2(payload: dict) -> str:
    if not GEMINI_API_KEY:
        return "Gemini API Key is missing. Please set it in Streamlit secrets."
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    try:
        res = requests.post(url, json=payload,
                            headers={"Content-Type":"application/json","X-goog-api-key":GEMINI_API_KEY},
                            timeout=15)
        if res.status_code == 200:
            cand = res.json().get("candidates", [{}])
            return cand[0].get("content", {}).get("parts", [{}])[0].get("text", "No answer found.")
        return f"Connection error: {res.status_code} - {res.text}"
    except Exception:
        return "A network error occurred. Please try again later."

def get_topic_from_prompt(prompt: str) -> str:
    pat = r"(?:on|par|about|ke bare mein|पर|के बारे में|का|की)\s+([a-zA-Z0-9\-अ-ह ]+)"
    m = re.search(pat, prompt, re.IGNORECASE)
    if m: return m.group(1).strip()
    w = prompt.strip().split()
    if len(w)>1: return w[-2] if w[-1].lower() in ["articles","पर","on"] else w[-1]
    return prompt.strip()

def handle_user_query(prompt: str) -> str:
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

    article_keywords = ["article","articles","research paper","journal","preprint",
                        "open access","dataset","साहित्य","आर्टिकल","पत्रिका","जर्नल","शोध","पेपर"]
    if any(k in prompt.lower() for k in article_keywords):
        topic = get_topic_from_prompt(prompt)
        if not topic or len(topic)<2:
            return "Please specify a topic for article search. उदाहरण: 'articles on AI' या 'हिंदी साहित्य पर articles'।"
        ans = f"### 🟦 Bennett University e-Resources (Refread)\nFind e-books and journal articles on **'{topic.title()}'** 24/7 here: [Refread](https://bennett.refread.com/#/home)\n\n"

        g = google_books_search(topic, 3)
        ans += "### 📚 Books from Google Books\n"
        ans += "".join([f"- [{b['title']}]({b['url']})"
                        f"{' by '+b['authors'] if b['authors'] else ''}"
                        f"{', '+b['publisher'] if b['publisher'] else ''}"
                        f"{' ('+b['year']+')' if b['year'] else ''}\n" for b in g]) or "No relevant books found from Google Books.\n"

        c = core_article_search(topic, 3)
        ans += "### 🌐 Open Access (CORE)\n"
        ans += "".join([f"- [{x.get('title','No Title')}]({x.get('downloadUrl', (x.get('urls',[{}])[0].get('url','#')))})"
                        f" {'('+x.get('createdDate','')[:4]+')' if x.get('createdDate') else ''}\n" for x in c]) or "No recent articles found on this topic from CORE.\n"

        a = arxiv_article_search(topic, 3)
        ans += "### 📄 Preprints (arXiv)\n"
        ans += "".join([f"- [{x['title']}]({x['url']}) ({x['year']})\n" for x in a]) or "No recent preprints found on this topic from arXiv.\n"

        d = doaj_article_search(topic, 3)
        ans += "### 📚 Open Access Journals (DOAJ)\n"
        ans += "".join([f"- [{x['title']}]({x['url']}) ({x['year']}) - {x['journal']}\n" for x in d]) or "No open access journal articles found on this topic from DOAJ.\n"

        dc = datacite_article_search(topic, 3)
        ans += "### 🏷️ Research Data/Articles (DataCite)\n"
        ans += "".join([f"- [{x['title']}]({x['url']}) ({x['year']}) - {x['journal']}\n" for x in dc]) or "No research datasets/articles found on this topic from DataCite.\n"
        return ans

    return call_gemini_api_v2(create_payload(prompt))

# ==== CHAT ====
if "messages" not in st.session_state:
    st.session_state.messages = []

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"], unsafe_allow_html=True)

# keep input visible (padding already added above)
prompt = st.chat_input("Type your query about books, research papers, journals, library services...")
if prompt:
    st.session_state.messages.append({"role":"user","content":prompt})
    with st.spinner("Ashu is typing..."):
        answer = handle_user_query(prompt)
    st.session_state.messages.append({"role":"assistant","content":answer})
    st.rerun()

# ==== CUSTOM FOOTER ====
st.markdown('<div class="custom-footer">Build in Ashutosh Mishra</div>', unsafe_allow_html=True)
