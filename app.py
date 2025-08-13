import streamlit as st
import requests
import re
import feedparser  # pip install feedparser
import urllib.parse
import csv
from io import StringIO

# ==== GET KEYS FROM SECRETS (never paste in code) ====
GEMINI_API_KEY        = st.secrets.get("GEMINI_API_KEY", "")
CORE_API_KEY          = st.secrets.get("CORE_API_KEY", "")
GOOGLE_BOOKS_API_KEY  = st.secrets.get("GOOGLE_BOOKS_API_KEY", "")

# Koha (internal)
KOHA_BASE_URL         = st.secrets.get("KOHA_BASE_URL", "")     # e.g. http://10.6.0.105:8080/api/v1
KOHA_CLIENT_ID        = st.secrets.get("KOHA_CLIENT_ID", "")
KOHA_CLIENT_SECRET    = st.secrets.get("KOHA_CLIENT_SECRET", "")
KOHA_OPAC_BASE        = st.secrets.get("KOHA_OPAC_BASE", "https://libraryopac.bennett.edu.in")

# Koha REPORT IDs (IMPORTANT)
KOHA_REPORT_AI_ID     = st.secrets.get("KOHA_REPORT_AI_ID", "")  # <-- put your saved report id here (e.g. "123")

# ==== CSS ====
st.markdown("""
<style>
    :root { --header-color: #2e86c1; }
    .main .block-container { max-width: 900px; padding: 2rem 1rem; }
    .profile-container { text-align: center; margin-bottom: 1rem; }
    .quick-actions-row { display: flex; justify-content: center; gap: 10px; margin: 1rem 0 2rem 0; width: 100%; }
    .quick-action-btn { background-color: #2e86c1; color: white !important; padding: 10px 15px; border-radius: 20px; border: none; box-shadow: 0 2px 5px rgba(0,0,0,0.1); transition: all 0.3s; font-size: 14px; text-decoration: none; text-align: center; cursor: pointer; white-space: nowrap; flex: 1; max-width: 200px; }
    .quick-action-btn:hover { transform: translateY(-2px); box-shadow: 0 4px 8px rgba(0,0,0,0.15); }
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

# ==== BUTTONS ====
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

# ==== External APIs ====
def google_books_search(query, limit=5):
    if not GOOGLE_BOOKS_API_KEY:
        return []
    url = f"https://www.googleapis.com/books/v1/volumes?q={urllib.parse.quote(query)}&maxResults={limit}&key={GOOGLE_BOOKS_API_KEY}"
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
                "title": title, "authors": authors, "url": link,
                "publisher": publisher, "year": year
            })
        return result
    except Exception:
        return []

def core_article_search(query, limit=5):
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

def arxiv_article_search(query, limit=5):
    url = f"http://export.arxiv.org/api/query?search_query=all:{urllib.parse.quote(query)}&start=0&max_results={limit}"
    try:
        feed = feedparser.parse(url)
        result = []
        for entry in feed.entries:
            title = entry.title
            pdf_links = [l.href for l in entry.links if l.type == "application/pdf"]
            link = pdf_links[0] if pdf_links else entry.link
            year = entry.published[:4]
            result.append({"title": title, "url": link, "year": year})
        return result
    except Exception:
        return []

def doaj_article_search(query, limit=5):
    url = f"https://doaj.org/api/search/articles/title:{urllib.parse.quote(query)}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            articles = data.get("results", [])[:limit]
            result = []
            for art in articles:
                bibjson = art.get("bibjson", {})
                title = bibjson.get("title", "No Title")
                link = bibjson.get("link", [{}])[0].get("url", "#")
                journal = bibjson.get("journal", {}).get("title", "")
                year = bibjson.get("year", "")
                result.append({"title": title, "url": link, "journal": journal, "year": year})
            return result
        return []
    except Exception:
        return []

def datacite_article_search(query, limit=5):
    url = f"https://api.datacite.org/dois?query={urllib.parse.quote(query)}&page[size]={limit}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            items = resp.json().get("data", [])
            result = []
            for item in items:
                attrs = item.get("attributes", {})
                title = (attrs.get("titles", [{}])[0].get("title", "No Title")) if attrs.get("titles") else "No Title"
                url2 = attrs.get("url", "#")
                publisher = attrs.get("publisher", "")
                year = attrs.get("publicationYear", "")
                result.append({"title": title, "url": url2, "journal": publisher, "year": year})
            return result
        return []
    except Exception:
        return []

# ==== Koha OAuth token ====
def koha_get_token():
    if not (KOHA_BASE_URL and KOHA_CLIENT_ID and KOHA_CLIENT_SECRET):
        return None
    try:
        r = requests.post(
            f"{KOHA_BASE_URL}/oauth/token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "client_credentials",
                "client_id": KOHA_CLIENT_ID,
                "client_secret": KOHA_CLIENT_SECRET
            },
            timeout=15
        )
        if r.status_code == 200:
            return r.json().get("access_token")
    except Exception:
        pass
    return None

# ==== Koha Reports API: Run “AI Books” report and return JSON rows ====
def koha_ai_books():
    """
    Calls Koha Reports REST API to get all 'Artificial Intelligence' books from your saved report.
    Shows table + CSV download in chat.
    """
    if not (KOHA_BASE_URL and KOHA_REPORT_AI_ID):
        return {"ok": False, "msg": "Koha base URL or KOHA_REPORT_AI_ID missing in secrets.", "rows": []}

    token = koha_get_token()
    if not token:
        return {"ok": False, "msg": "Koha OAuth token failed. Check CLIENT_ID/SECRET in secrets.", "rows": []}

    headers_json = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    try:
        url = f"{KOHA_BASE_URL}/reports/{KOHA_REPORT_AI_ID}/run"
        r = requests.get(url, headers=headers_json, timeout=120)
        if r.status_code != 200:
            return {"ok": False, "msg": f"Reports API error: {r.status_code} - {r.text[:300]}", "rows": []}
        rows = r.json()
        if not isinstance(rows, list):
            return {"ok": False, "msg": "Unexpected report format.", "rows": []}
        return {"ok": True, "msg": f"Found {len(rows)} AI books.", "rows": rows}
    except Exception as e:
        return {"ok": False, "msg": "Network error while hitting Reports API.", "rows": []}

# ==== Gemini prompt ====
def create_payload(prompt):
    system_instruction = (
        "You are Ashu, an AI assistant for Bennett University Library. "
        "Provide accurate and concise answers based on the following FAQ and library information. "
        "Key information: "
        "- Library website: https://library.bennett.edu.in/. "
        "- Library timings: Weekdays 8:00 AM to 12:00 AM (midnight), Weekends & Holidays 9:00 AM to 5:00 PM (may vary during vacations, check https://library.bennett.edu.in/index.php/working-hours/). "
        "- Physical book search: Use https://libraryopac.bennett.edu.in/ to search for physical books. "
        "- e-Resources: Access digital books and journal articles at https://bennett.refread.com/#/home. "
        "- Group Discussion Rooms: Book at http://10.6.0.121/gdroombooking/. "
        "If the question is unrelated, politely redirect to library-related topics. "
        f"User question: {prompt}"
    )
    return {"contents": [{"parts": [{"text": system_instruction}]}]}

def call_gemini_api_v2(payload):
    if not GEMINI_API_KEY:
        return "Gemini API Key is missing. Please set it in Streamlit secrets."
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    try:
        response = requests.post(
            url, json=payload,
            headers={"Content-Type": "application/json", "X-goog-api-key": GEMINI_API_KEY},
            timeout=15
        )
        if response.status_code == 200:
            candidates = response.json().get("candidates", [{}])
            return candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "No answer found.")
        return f"Connection error: {response.status_code} - {response.text}"
    except Exception:
        return "A network error occurred. Please try again later."

def get_topic_from_prompt(prompt):
    pattern = r"(?:on|par|about|ke bare mein|पर|के बारे में|का|की)\s+([a-zA-Z0-9\-अ-ह ]+)"
    match = re.search(pattern, prompt, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    words = prompt.strip().split()
    if len(words) > 1:
        return words[-2] if words[-1].lower() in ["articles", "पर", "on"] else words[-1]
    return prompt.strip()

# ==== Main chat intent handler ====
def handle_user_query(prompt):
    pl = prompt.lower().strip()

    # SPECIAL: All AI books from Koha (full list via Report)
    if ("artificial intelligence" in pl) and ("find books" in pl or "books" in pl or "kitni" in pl or "list" in pl):
        result = koha_ai_books()
        if not result["ok"]:
            return f"⚠️ {result['msg']}\n\nTry OPAC search: {KOHA_OPAC_BASE}/cgi-bin/koha/opac-search.pl?idx=ti&q=artificial%20intelligence"

        rows = result["rows"]
        n = len(rows)
        answer = f"### 📚 Artificial Intelligence — Books in BU Koha\nFound **{n}** records.\n\n"
        # Make a small markdown list preview (first 15)
        for r in rows[:15]:
            title = r.get("title") or "No title"
            author = r.get("author") or ""
            bid = r.get("biblio_id") or r.get("biblionumber") or ""
            link = f"{KOHA_OPAC_BASE}/cgi-bin/koha/opac-detail.pl?biblionumber={bid}" if bid else f"{KOHA_OPAC_BASE}/cgi-bin/koha/opac-search.pl?idx=ti&q=artificial%20intelligence"
            author_txt = f" — {author}" if author else ""
            answer += f"- [{title}]({link}){author_txt}\n"

        # Build CSV in-memory + provide download button
        csv_buf = StringIO()
        if rows:
            fieldnames = ["biblio_id", "title", "subtitle", "author", "isbn", "publisher", "publication_year", "item_type"]
            writer = csv.DictWriter(csv_buf, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for r in rows:
                writer.writerow(r)

        st.markdown(answer)
        if rows:
            st.download_button(
                label="⬇️ Download full AI books list (CSV)",
                data=csv_buf.getvalue(),
                file_name="artificial_intelligence_books.csv",
                mime="text/csv",
                use_container_width=True
            )
        return ""

    # Generic “find books on …” (Google + links)
    if "find books on" in pl or "find book on" in pl:
        topic = pl.replace("find books on", "").replace("find book on", "").strip() or "library"
        answer = f"### 📚 Books on **{topic.title()}**\n"
        gb = google_books_search(topic, limit=5)
        if gb:
            answer += "#### Google Books\n"
            for book in gb:
                authors = f" by {book['authors']}" if book['authors'] else ""
                pub = f", {book['publisher']}" if book['publisher'] else ""
                year = f" ({book['year']})" if book['year'] else ""
                answer += f"- [{book['title']}]({book['url']}){authors}{pub}{year}\n"
        else:
            answer += "- No relevant books found from Google Books.\n"
        answer += f"\n**More:** [BU OPAC]({KOHA_OPAC_BASE}) · [Refread e-Resources](https://bennett.refread.com/#/home)\n"
        return answer

    # Articles / research papers intent
    article_keywords = ["article","articles","research paper","journal","preprint","open access","dataset","साहित्य","आर्टिकल","पत्रिका","जर्नल","शोध","पेपर"]
    if any(kw in pl for kw in article_keywords):
        topic = get_topic_from_prompt(prompt)
        if not topic or len(topic) < 2:
            return "Please specify a topic for article search. उदाहरण: 'articles on AI' या 'हिंदी साहित्य पर articles'."
        topic = topic.strip()
        answer = f"### 🟦 Bennett University e-Resources (Refread)\n"
        answer += f"Find e-books and journal articles on **'{topic.title()}'** 24/7 here: [Refread](https://bennett.refread.com/#/home)\n\n"

        # Optional: show a few Koha titles too (OPAC click-through)
        answer += f"#### Bennett OPAC (titles)\n- Search: {KOHA_OPAC_BASE}/cgi-bin/koha/opac-search.pl?idx=ti&q={urllib.parse.quote(topic)}\n\n"

        google_books = google_books_search(topic, limit=3)
        answer += "#### Google Books\n"
        if google_books:
            for book in google_books:
                authors = f" by {book['authors']}" if book['authors'] else ""
                pub = f", {book['publisher']}" if book['publisher'] else ""
                year = f" ({book['year']})" if book['year'] else ""
                answer += f"- [{book['title']}]({book['url']}){authors}{pub}{year}\n"
        else:
            answer += "- No relevant books found from Google Books.\n"

        core_results = core_article_search(topic, limit=3)
        answer += "\n#### 🌐 CORE (Open Access)\n"
        if core_results:
            for art in core_results:
                title = art.get("title","No Title")
                url = art.get("downloadUrl", art.get("urls", [{}])[0].get("url", "#"))
                year = art.get("createdDate","")[:4]
                answer += f"- [{title}]({url}) {'('+year+')' if year else ''}\n"
        else:
            answer += "- No recent OA articles found on CORE.\n"

        arxiv_results = arxiv_article_search(topic, limit=3)
        answer += "\n#### 📄 arXiv (Preprints)\n"
        if arxiv_results:
            for art in arxiv_results:
                answer += f"- [{art['title']}]({art['url']}) ({art['year']})\n"
        else:
            answer += "- No preprints found on arXiv.\n"

        doaj_results = doaj_article_search(topic, limit=3)
        answer += "\n#### 📚 DOAJ (Open Access Journals)\n"
        if doaj_results:
            for art in doaj_results:
                answer += f"- [{art['title']}]({art['url']}) ({art['year']}) - {art['journal']}\n"
        else:
            answer += "- No OA journal articles found on DOAJ.\n"

        datacite_results = datacite_article_search(topic, limit=3)
        answer += "\n#### 🏷️ DataCite\n"
        if datacite_results:
            for art in datacite_results:
                answer += f"- [{art['title']}]({art['url']}) ({art['year']}) - {art['journal']}\n"
        else:
            answer += "- No entries found on DataCite.\n"

        return answer

    # General (FAQ etc) - Gemini
    payload = create_payload(prompt)
    return call_gemini_api_v2(payload)

# ==== UI ====
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
    if answer:
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
