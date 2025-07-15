import streamlit as st
import requests
import re
import feedparser

# ========== YOUR VM KOHA SERVER INFO ==========
KOHA_API_BASE = "http://192.168.31.128:8081/api/v1"
KOHA_USER = "ashutosh"
KOHA_PASS = "#Ashu12!@"

GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
CORE_API_KEY = st.secrets.get("CORE_API_KEY", "")
GOOGLE_BOOKS_API_KEY = st.secrets.get("GOOGLE_BOOKS_API_KEY", "")

# ========== CSS (same as above) ==========
st.markdown("""
<style>
    :root { --header-color: #2e86c1; }
    .main .block-container { max-width: 900px; padding: 2rem 1rem; }
    .profile-container { text-align: center; margin-bottom: 1rem; }
    .quick-actions-row { display: flex; justify-content: center; gap: 10px; margin: 1rem 0 2rem 0; width: 100%; }
    .quick-action-btn { background-color: #2e86c1; color: white !important; padding: 10px 15px; border-radius: 20px; border: none; box-shadow: 0 2px 5px rgba(0,0,0,0.1); transition: all 0.3s; font-size: 14px; text-decoration: none; text-align: center; cursor: pointer; white-space: nowrap; flex: 1; max-width: 200px; }
    .quick-action-btn:hover { transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.15); }
    .chat-container { margin: 2rem 0; }
    .static-chat-input { position: fixed; bottom: 80px; left: 50%; transform: translateX(-50%); width: 100%; max-width: 800px; z-index: 100; }
    .stChatInput input { border-radius: 25px !important; padding: 12px 20px !important; }
    .stChatInput button { border-radius: 50% !important; background-color: var(--header-color) !important; }
    .footer { position: fixed; bottom: 0; left: 0; right: 0; text-align: center; color: #666; padding: 1rem; background-color: white; z-index: 99; }
    @media (max-width: 700px) {
        .main .block-container { padding: 0.5rem 0.2rem; }
        .static-chat-input { max-width: 98vw; }
    }
</style>
""", unsafe_allow_html=True)

def create_quick_action_button(text, url):
    return f'<a href="{url}" target="_blank" class="quick-action-btn">{text}</a>'

def show_quick_actions():
    quick_actions = [
        ("Find e-Resources", "https://bennett.refread.com/#/home"),
        ("Find Books", "https://libraryopac.bennett.edu.in/"),
        ("Working Hours", "https://library.bennett.edu.in/index.php/working-hours/"),
        ("Book GD Rooms", "http://10.6.0.121/gdroombooking/")
    ]
    st.markdown(
        '<div class="quick-actions-row">' +
        "".join([create_quick_action_button(t, u) for t, u in quick_actions]) +
        '</div>',
        unsafe_allow_html=True
    )

# ========== KOHA API FUNCTIONS ==========
def koha_get_patrons():
    url = KOHA_API_BASE + "/patrons/"
    try:
        resp = requests.get(url, auth=(KOHA_USER, KOHA_PASS), headers={"Accept":"application/json"}, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        else:
            return []
    except Exception:
        return []

def koha_get_biblios():
    url = KOHA_API_BASE + "/biblios/"
    try:
        resp = requests.get(url, auth=(KOHA_USER, KOHA_PASS), headers={"Accept":"application/json"}, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        else:
            return []
    except Exception:
        return []

def koha_patron_checkouts(cardnumber):
    url = f"{KOHA_API_BASE}/checkouts?cardnumber={cardnumber}"
    try:
        resp = requests.get(url, auth=(KOHA_USER, KOHA_PASS), headers={"Accept":"application/json"}, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        else:
            return []
    except Exception:
        return []

# ========== OTHER APIs as before (Google Books, CORE, etc.) ==========
def google_books_search(query, limit=5):
    if not GOOGLE_BOOKS_API_KEY:
        return []
    url = f"https://www.googleapis.com/books/v1/volumes?q={query}&maxResults={limit}&key={GOOGLE_BOOKS_API_KEY}"
    try:
        resp = requests.get(url, timeout=10)
        items = resp.json().get("items", [])
        result = []
        for item in items:
            volume = item.get("volumeInfo", {})
            title = volume.get("title", "No Title")
            authors = ", ".join(volume.get("authors", []))
            link = volume.get("infoLink", "#")
            publisher = volume.get("publisher", "")
            year = volume.get("publishedDate", "")[:4]
            result.append({
                "title": title,
                "authors": authors,
                "url": link,
                "publisher": publisher,
                "year": year
            })
        return result
    except Exception as e:
        return []

# (core_article_search, arxiv_article_search, doaj_article_search, datacite_article_search -- as in your code)

# ========== MAIN QUERY HANDLER ==========
def handle_user_query(prompt):
    pl = prompt.lower()

    # 1. Koha: List all patrons
    if "show all patrons" in pl or "list all patrons" in pl:
        patrons = koha_get_patrons()
        if not patrons:
            return "No patrons found or API not reachable."
        msg = "### 🧑‍💼 All Library Patrons (Koha API)\n"
        for p in patrons:
            msg += f"- {p['firstname']} {p['surname']} ({p['cardnumber']})\n"
        return msg

    # 2. Koha: List all books
    if "show all books" in pl or "list all books" in pl:
        books = koha_get_biblios()
        if not books:
            return "No books found or API not reachable."
        msg = "### 📚 Books in Library Catalog (Koha API)\n"
        for b in books:
            msg += f"- {b.get('title','(no title)')} ({b.get('publisher','')})\n"
        return msg

    # 3. Koha: Patron checkouts
    if "checkouts for" in pl:
        match = re.search(r"checkouts for (\w+)", pl)
        if match:
            card = match.group(1)
            checkouts = koha_patron_checkouts(card)
            if not checkouts:
                return f"No checkouts found for {card}."
            msg = f"### Books checked out for card `{card}`\n"
            for co in checkouts:
                msg += f"- {co.get('title','(no title)')} (Due: {co.get('date_due','')})\n"
            return msg
        return "Please specify the cardnumber, e.g. 'checkouts for 15121112'"

    # 4. Google Books quick search
    if "find books on" in pl or "find book on" in pl:
        topic = pl.replace("find books on","").replace("find book on","").strip()
        books = google_books_search(topic, limit=5)
        msg = f"### 📚 Books on **{topic.title()}** (Google Books)\n"
        if books:
            for book in books:
                authors = f" by {book['authors']}" if book['authors'] else ""
                pub = f", {book['publisher']}" if book['publisher'] else ""
                year = f" ({book['year']})" if book['year'] else ""
                msg += f"- [{book['title']}]({book['url']}){authors}{pub}{year}\n"
        else:
            msg += "No relevant books found from Google Books.\n"
        msg += f"\n**For more, search [BU OPAC](https://libraryopac.bennett.edu.in/) or [Refread](https://bennett.refread.com/#/home).**"
        return msg

    # 5. General: Gemini/OpenAI etc (as in your code)
    # fallback to Gemini
    payload = create_payload(prompt)
    return call_gemini_api_v2(payload)

# ========== STREAMLIT PAGE ==========
if "messages" not in st.session_state:
    st.session_state.messages = []

st.markdown("""
<div class="profile-container">
    <img src="https://library.bennett.edu.in/wp-content/uploads/2024/05/WhatsApp-Image-2024-05-01-at-12.41.02-PM-e1714549052999-150x150.jpeg"
         width="150"
         style="border-radius: 50%; border: 3px solid #2e86c1; margin-bottom: 1rem;">
    <h1 style="color: #2e86c1; margin-bottom: 0.5rem; font-size: 2em;">Ashu AI Assistant at Bennett University Library</h1>
</div>
""", unsafe_allow_html=True)

show_quick_actions()

st.markdown("""
<div style="text-align: center; margin: 2rem 0;">
    <p style="font-size: 1.1em;">Hello! I am Ashu, your AI assistant at Bennett University Library. How can I help you today?</p>
</div>
""", unsafe_allow_html=True)

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

st.markdown('<div class="static-chat-input">', unsafe_allow_html=True)
prompt = st.chat_input("Type your query about books, research papers, journals, library services...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.spinner("Ashu is typing..."):
        answer = handle_user_query(prompt)
    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

st.markdown("""
<div class="footer">
    <div style="margin: 0.5rem 0;">
        © 2025 - Ashutosh Mishra | All Rights Reserved
    </div>
</div>
""", unsafe_allow_html=True)

# ============================
# NOTE: Google Books/CORE API keys set in .streamlit/secrets.toml
# Koha API VM must be ON, network must be reachable (which you already did!)
# ============================

