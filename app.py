import streamlit as st
import requests
import os
import logging
import re
import feedparser  # pip install feedparser
import json
from streamlit.components.v1 import html

# --- Streamlit Page Config ---
st.set_page_config(
    page_title="Ashu AI @ BU Library",
    page_icon="https://play-lh.googleusercontent.com/kCXMe_CDJaLcEb_Ax8hoSo9kfqOmeB7VoB4zNI5dCSAD8QSeNZE1Eow4NBXx-NjTDQ",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- Logging ---
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# --- API Keys & Endpoints ---
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
CORE_API_KEY    = st.secrets.get("CORE_API_KEY",    os.getenv("CORE_API_KEY"))

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
CORE_ENDPOINT   = "https://api.core.ac.uk/v3/search/works"

# --- Custom CSS ---
CSS_STYLES = """
<style>
    :root { --header-color: #2e86c1; }
    .main .block-container { max-width: 900px; padding: 2rem 1rem; }
    .profile-container { text-align: center; margin-bottom: 1rem; }
    .quick-actions-row { display: flex; justify-content: center; gap: 10px; margin: 1rem 0 2rem 0; width: 100%; }
    .quick-action-btn { background-color: var(--header-color); color: white !important; padding: 10px 15px; border-radius: 20px; border: none; box-shadow: 0 2px 5px rgba(0,0,0,0.1); transition: all 0.3s; font-size: 14px; text-decoration: none; text-align: center; cursor: pointer; white-space: nowrap; flex: 1; max-width: 200px; }
    .quick-action-btn:hover { transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.15); }
    .footer { position: fixed; bottom: 0; left: 0; right: 0; text-align: center; color: #666; padding: 1rem; background-color: white; z-index: 99; }
</style>
"""

def inject_custom_css():
    st.markdown(CSS_STYLES, unsafe_allow_html=True)

def create_quick_action_button(text, url):
    return f'<a href="{url}" target="_blank" class="quick-action-btn">{text}</a>'

# --- Article Search Functions ---
def core_article_search(query, limit=5):
    if not CORE_API_KEY:
        return []
    try:
        r = requests.get(
            CORE_ENDPOINT,
            headers={"Authorization": f"Bearer {CORE_API_KEY}"},
            params={"q": query, "limit": limit},
            timeout=15
        )
        return r.json().get("results", [])
    except:
        return []

# (arxiv, doaj, datacite functions unchanged...)

def arxiv_article_search(query, limit=5):
    try:
        feed = feedparser.parse(
            f"http://export.arxiv.org/api/query?search_query=all:{query}&start=0&max_results={limit}"
        )
        out = []
        for e in feed.entries:
            pdfs = [l.href for l in e.links if l.type=="application/pdf"]
            out.append({
                "title": e.title,
                "url": pdfs[0] if pdfs else e.link,
                "year": e.published[:4]
            })
        return out
    except:
        return []

def doaj_article_search(query, limit=5):
    try:
        resp = requests.get(f"https://doaj.org/api/search/articles/title:{query}", timeout=10)
        arts = resp.json().get("results", [])[:limit]
        out = []
        for art in arts:
            b = art.get("bibjson", {})
            out.append({
                "title": b.get("title","No Title"),
                "url":   b.get("link",[{}])[0].get("url","#"),
                "journal": b.get("journal",{}).get("title",""),
                "year": b.get("year","")
            })
        return out
    except:
        return []


def datacite_article_search(query, limit=5):
    try:
        resp = requests.get(f"https://api.datacite.org/dois?query={query}&page[size]={limit}", timeout=10)
        items = resp.json().get("data", [])
        out = []
        for it in items:
            a = it.get("attributes",{})
            titles = a.get("titles",[])
            out.append({
                "title": titles[0].get("title","No Title") if titles else "No Title",
                "url":   a.get("url","#"),
                "journal": a.get("publisher",""),
                "year": a.get("publicationYear","")
            })
        return out
    except:
        return []

# --- Gemini Integration ---
def create_payload(prompt):
    system = (
        "You are Ashu, an AI assistant for Bennett University Library. "
        "Use the library FAQ and resources to answer."
        f" User question: {prompt}"
    )
    return {"contents":[{"parts":[{"text": system}]}]}

def call_gemini(payload):
    if not GEMINI_API_KEY:
        return "Missing GEMINI_API_KEY."
    try:
        r = requests.post(
            GEMINI_ENDPOINT,
            json=payload,
            headers={"Content-Type":"application/json","X-goog-api-key":GEMINI_API_KEY},
            timeout=15
        )
        j = r.json()
        return j["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        logging.error(e)
        return "Error calling Gemini API."

# --- Topic Extraction ---
def get_topic(prompt):
    m = re.search(r"(?:on|par|about|के बारे में)\s+(.+)$", prompt, re.IGNORECASE)
    return m.group(1).strip() if m else prompt

# --- Main Query Handler ---
def handle_query(q):
    ql = q.lower()
    if "find book" in ql or "find books" in ql:
        topic = ql.split("on")[-1].strip()
        return f"To find books on **{topic.title()}**, visit [OPAC](https://libraryopac.bennett.edu.in/) or e-resources at [Refread](https://bennett.refread.com/#/home)."
    kws = ["article","research","journal","पेपर","आर्टिकल"]
    if any(k in ql for k in kws):
        topic = get_topic(q)
        out = f"### e-Resources (Refread)\n- Search **{topic.title()}** at https://bennett.refread.com/#/home\n\n"
        cr = core_article_search(topic)
        out += "### CORE\n" + ("\n".join(f"- [{a['title']}]({a.get('downloadUrl',a['urls'][0]['url'])}) ({a.get('createdDate','')[:4]})" for a in cr) or "No results") + "\n\n"
        ar = arxiv_article_search(topic)
        out += "### arXiv\n" + ("\n".join(f"- [{a['title']}]({a['url']}) ({a['year']})" for a in ar) or "No results") + "\n\n"
        dj = doaj_article_search(topic)
        out += "### DOAJ\n" + ("\n".join(f"- [{a['title']}]({a['url']}) ({a['year']})" for a in dj) or "No results") + "\n\n"
        dc = datacite_article_search(topic)
        out += "### DataCite\n" + ("\n".join(f"- [{a['title']}]({a['url']}) ({a['year']})" for a in dc) or "No results")
        return out
    return call_gemini(create_payload(q))

# --- Quick Actions ---
def show_quick_actions():
    qa = [
        ("Find e-Resources", "https://bennett.refread.com/#/home"),
        ("Find Books", "https://libraryopac.bennett.edu.in/"),
        ("Working Hours", "https://library.bennett.edu.in/index.php/working-hours/"),
        ("Book GD Rooms", "http://10.6.0.121/gdroombooking/")
    ]
    st.markdown(
        '<div class="quick-actions-row">' +
        "".join(create_quick_action_button(t,u) for t,u in qa) +
        '</div>', unsafe_allow_html=True
    )

# --- Voice-Activated Catalog Component ---
books = [
    {"title":"सूरज का सातवाँ घोड़ा","author":"धर्मवीर भारती","genre":"Novel"},
    {"title":"गोदान","author":"मुंशी प्रेमचंद","genre":"Classic"},
    {"title":"मुंशीजी की कहानियाँ","author":"मुंशी प्रेमचंद","genre":"Short Stories"},
    {"title":"गिट्टी छोड़ो पुल बनाओ","author":"रवीन्द्रनाथ टैगोर","genre":"Poetry"},
    {"title":"सत्यार्थ प्रकाश","author":"मदनमोहन मालवीय","genre":"History"}
]
books_json = json.dumps(books, ensure_ascii=False)

voice_catalog_html = (
    """
<style>
.controls { display:flex; justify-content:center; gap:0.5rem; margin-bottom:1rem; }
.controls input, .controls button { padding:0.5rem; font-size:1rem; }
.controls button { cursor:pointer; }
#bookGrid { display:grid; grid-template-columns:repeat(auto-fill,minmax(180px,1fr)); gap:1rem; }
.book-card { background:#fff; border-radius:4px; padding:0.5rem; box-shadow:0 1px 3px rgba(0,0,0,0.1); }
.book-card h3 { font-size:1.1rem; margin-bottom:0.3rem; }
</style>
<header>
  <h2 style="text-align:center;">वॉइस-एक्टिवेटेड कैटलॉग</h2>
  <div class="controls">
    <input type="text" id="searchInput" placeholder="टाइप करके खोजें...">
    <button id="voiceBtn">🎤 बोलकर खोजें</button>
  </div>
</header>
<main id="bookGrid"></main>
<script>
const books = """ + books_json + """;
function renderBooks(list) {
    const grid = document.getElementById('bookGrid');
    grid.innerHTML = '';
    if (!list.length) { grid.innerHTML = '<p>कोई किताब नहीं मिली।</p>'; return; }
    list.forEach(b => {
        const c = document.createElement('div'); c.className = 'book-card';
        c.innerHTML = `<h3>${b.title}</h3><p><strong>लेखक:</strong> ${b.author}</p><p><strong>शैली:</strong> ${b.genre}</p>`;
        grid.appendChild(c);
    });
}
function applyFilters(q) {
    const txt = q.trim().toLowerCase();
    return books.filter(b => 
        b.title.toLowerCase().includes(txt) ||
        b.author.toLowerCase().includes(txt) ||
        b.genre.toLowerCase().includes(txt)
    );
}
function speak(t) {
    if (!('speechSynthesis' in window)) return;
    const u = new SpeechSynthesisUtterance(t);
    u.lang = 'hi-IN'; speechSynthesis.speak(u);
}
document.getElementById('voiceBtn').onclick = function() {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { alert('ब्राउज़र समर्थित नहीं, Chrome आज़माएँ'); return; }
    const r = new SR(); r.lang = 'hi-IN'; r.interimResults = false; r.maxAlternatives = 1; r.start();
    r.onresult = function(e) {
        const txt = e.results[0][0].transcript;
        document.getElementById('searchInput').value = txt;
        const res = applyFilters(txt);
        renderBooks(res);
        speak(`मिला ${res.length} परिणाम`);
    };
};
document.getElementById('searchInput').oninput = function(e) { renderBooks(applyFilters(e.target.value)); };
renderBooks(books);
</script>
    """
)

# --- Streamlit App ---
def main():
    inject_custom_css()

    st.markdown("""
    <div class="profile-container">
      <img src="https://library.bennett.edu.in/wp-content/uploads/2024/05/WhatsApp-Image-2024-05-01-at-12.41.02-PM-e1714549052999-150x150.jpeg"
           width="120" style="border-radius:50%;border:3px solid var(--header-color);">
      <h1 style="color:var(--header-color);">Ashu AI Assistant @ BU Library</h1>
    </div>
    """, unsafe_allow_html=True)

    show_quick_actions()
    html(voice_catalog_html, height=600)

    st.markdown("## 🤖 AI Chat Assistant")
    if "msgs" not in st.session_state:
        st.session_state.msgs = []
    for m in st.session_state.msgs:
        with st.chat_message(m["role"]):
            st.markdown(m["content"])
    user_input = st.chat_input("Ask about books, articles, services…")
    if user_input:
        st.session_state.msgs.append({"role":"user","content":user_input})
        with st.spinner("Ashu is typing…"):
            reply = handle_query(user_input)
        st.session_state.msgs.append({"role":"assistant","content":reply})
        st.experimental_rerun()

    st.markdown("""
    <div class="footer">© 2025 Ashutosh Mishra | Bennett University Library</div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
