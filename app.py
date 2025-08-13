import streamlit as st
import requests
import re
import feedparser  # pip install feedparser
import urllib.parse  # NEW

# ==== GET KEYS FROM SECRETS (never paste in code) ====
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
CORE_API_KEY = st.secrets.get("CORE_API_KEY", "")
GOOGLE_BOOKS_API_KEY = st.secrets.get("GOOGLE_BOOKS_API_KEY", "")

# Koha (NEW - all from secrets)
KOHA_BASE_URL = st.secrets.get("KOHA_BASE_URL", "")  # e.g. http://10.6.0.105:8080/api/v1
KOHA_CLIENT_ID = st.secrets.get("KOHA_CLIENT_ID", "")
KOHA_CLIENT_SECRET = st.secrets.get("KOHA_CLIENT_SECRET", "")
KOHA_OPAC_BASE = st.secrets.get("KOHA_OPAC_BASE", "https://libraryopac.bennett.edu.in")

# ==== CSS ====
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

# ==== API FUNCTIONS ====
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
                "title": title,
                "authors": authors,
                "url": link,
                "publisher": publisher,
                "year": year
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
        else:
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
        else:
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
        else:
            return []
    except Exception:
        return []

# ==== KOHA HELPERS (NEW) ====
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

def _koha_try(url, headers):
    try:
        resp = requests.get(url, headers=headers, timeout=20)
        if resp.status_code >= 400:
            # return status and small body for debugging/telemetry if needed
            return None, resp.status_code, resp.text[:400]
        data = resp.json()
        if isinstance(data, list):
            return data, resp.status_code, None
        return [], resp.status_code, None
    except Exception as e:
        return None, 0, str(e)

def koha_search_biblios(query, limit=5):
    """
    Tries multiple query styles (because your Koha previously rejected q=/search= and pagination).
    Always returns an OPAC link so the user can click-through.
    """
    opac_link = f"{KOHA_OPAC_BASE}/cgi-bin/koha/opac-search.pl?idx=ti&q={urllib.parse.quote(query)}"

    if not KOHA_BASE_URL:
        return {"records": [], "opac_url": opac_link}

    token = koha_get_token()
    if not token:
        return {"records": [], "opac_url": opac_link}

    hdr = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    q_plain = urllib.parse.quote(query)
    q_quoted = urllib.parse.quote(f"\"{query}\"")

    candidates = [
        f"{KOHA_BASE_URL}/biblios?q=title,contains,{q_plain}",
        f"{KOHA_BASE_URL}/biblios?q=any,contains,{q_plain}",
        f"{KOHA_BASE_URL}/biblios?q=title,contains,{q_quoted}",
        f"{KOHA_BASE_URL}/biblios?search={q_plain}",
        # last resort (no params): will return default batch; we’ll still map first few
        f"{KOHA_BASE_URL}/biblios",
    ]

    for url in candidates:
        data, status, err = _koha_try(url, hdr)
        if isinstance(data, list) and data:
            out = []
            for item in data[:max(1, int(limit))]:
                title = item.get("title") or "No title"
                author = item.get("author") or ""
                bid = item.get("biblio_id") or item.get("biblionumber") or ""
                detail = f"{KOHA_OPAC_BASE}/cgi-bin/koha/opac-detail.pl?biblionumber={bid}" if bid else opac_link
                out.append({"title": title, "authors": author, "url": detail})
            return {"records": out, "opac_url": opac_link}

    return {"records": [], "opac_url": opac_link}

def create_payload(prompt):
    system_instruction = (
        "You are Ashu, an AI assistant for Bennett University Library. "
        "Provide accurate and concise answers based on the following FAQ and library information. "
        "Key information: "
        "- Library website: https://library.bennett.edu.in/. "
        "- Library timings: Weekdays 8:00 AM to 12:00 AM (midnight), Weekends & Holidays 9:00 AM to 5:00 PM (may vary during vacations, check https://library.bennett.edu.in/index.php/working-hours/). "
        "- Physical book search: Use https://libraryopac.bennett.edu.in/ to search for physical books. For specific searches (e.g., by title or topic like 'Python'), guide users to enter terms in the catalog's title field. Automatic searches are not possible. "
        "- e-Resources: Access digital books and journal articles at https://bennett.refread.com/#/home, available 24/7 remotely. "
        "- Group Discussion Rooms: Book at http://10.6.0.121/gdroombooking/. "
        "FAQ: "
        "- Borrowing books: Use automated kiosks in the library (see library tutorial for details). "
        "- Return books: Use the 24/7 Drop Box outside the library (see library tutorial). "
        "- Overdue checks: Automated overdue emails are sent, or check via OPAC at https://libraryopac.bennett.edu.in/. "
        "- Journal articles: Accessible 24/7 remotely at https://bennett.refread.com/#/home. "
        "- Printing/Scanning: Available at the LRC from 9:00 AM to 5:30 PM. For laptop printing, email libraryhelpdesk@bennett.edu.in for official printouts or visit M-Block Library for other services. "
        "- Alumni access: Alumni can access the LRC for reference. "
        "- Book checkout limits: Refer to the library tutorial for details. "
        "- Overdue fines: Pay via BU Payment Portal and update library staff. "
        "- Book recommendations: Submit at https://docs.google.com/forms/d/e/1FAIpQLSeC0-LPlWvUbYBcN834Ct9kYdC9Oebutv5VWRcTujkzFgRjZw/viewform. "
        "- Appeal fines: Contact libraryhelpdesk@bennett.edu.in or visit the HelpDesk. "
        "- Download e-Books: Download chapters at https://bennett.refread.com/#/home. "
        "- Inter Library Loan: Available via DELNET, contact library for details. "
        "- Non-BU interns: Can use the library for reading only. "
        "- Finding books on shelves: Search via OPAC; books have Call Numbers, and shelves are marked (see tutorial). "
        "- Snacks in LRC: Not allowed, but water bottles are permitted. "
        "- Drop Box issues: Confirm return via auto-generated email; if none, contact libraryhelpdesk@bennett.edu.in. "
        "- Reserve a book: Use the 'Place Hold' feature in OPAC at https://libraryopac.bennett.edu.in/. "
        "If the question is unrelated, politely redirect to library-related topics. "
        f"User question: {prompt}"
    )
    return {
        "contents": [
            {"parts": [{"text": system_instruction}]}
        ]
    }

def call_gemini_api_v2(payload):
    if not GEMINI_API_KEY:
        return "Gemini API Key is missing. Please set it in Streamlit secrets."
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    try:
        response = requests.post(
            url,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "X-goog-api-key": GEMINI_API_KEY
            },
            timeout=15
        )
        if response.status_code == 200:
            candidates = response.json().get("candidates", [{}])
            answer = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "No answer found.")
            return answer
        else:
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

# ==== UPDATED: include Koha blocks ====
def handle_user_query(prompt):
    # Book search
    if "find books on" in prompt.lower() or "find book on" in prompt.lower():
        topic = (
            prompt.lower()
            .replace("find books on", "")
            .replace("find book on", "")
            .strip()
        )
        topic = topic if topic else "library"
        answer = f"### 📚 Books on **{topic.title()}**\n"

        # 1) Koha (real-time Bennett OPAC)
        koha = koha_search_biblios(topic, limit=5)
        answer += "#### Bennett OPAC (Koha)\n"
        if koha["records"]:
            for book in koha["records"]:
                authors = f" by {book['authors']}" if book.get("authors") else ""
                answer += f"- [{book['title']}]({book['url']}){authors}\n"
        else:
            answer += f"- *(API search not available on this server build)* — Try OPAC: [{topic}]({koha['opac_url']})\n"

        # 2) Google Books
        gb = google_books_search(topic, limit=5)
        answer += "\n#### Google Books\n"
        if gb:
            for book in gb:
                authors = f" by {book['authors']}" if book['authors'] else ""
                pub = f", {book['publisher']}" if book['publisher'] else ""
                year = f" ({book['year']})" if book['year'] else ""
                answer += f"- [{book['title']}]({book['url']}){authors}{pub}{year}\n"
        else:
            answer += "- No relevant books found from Google Books.\n"

        answer += f"\n**More:** [BU OPAC](https://libraryopac.bennett.edu.in/) · [Refread e-Resources](https://bennett.refread.com/#/home)\n"
        return answer

    # Article/research paper/journal
    article_keywords = [
        "article", "articles", "research paper", "journal", "preprint", "open access", "dataset", "साहित्य", "आर्टिकल", "पत्रिका", "जर्नल", "शोध", "पेपर"
    ]
    if any(kw in prompt.lower() for kw in article_keywords):
        topic = get_topic_from_prompt(prompt)
        if not topic or len(topic) < 2:
            return "Please specify a topic for article search. उदाहरण: 'articles on AI' या 'हिंदी साहित्य पर articles'।"
        topic = topic.strip()

        answer = f"### 🟦 Bennett University e-Resources (Refread)\n"
        answer += f"Find e-books and journal articles on **'{topic.title()}'** 24/7 here: [Refread](https://bennett.refread.com/#/home)\n\n"

        # Koha (optional titles)
        koha = koha_search_biblios(topic, limit=5)
        answer += "#### Bennett OPAC (Koha)\n"
        if koha["records"]:
            for book in koha["records"]:
                authors = f" by {book['authors']}" if book.get("authors") else ""
                answer += f"- [{book['title']}]({book['url']}){authors}\n"
        else:
            answer += f"- *(API search not available on this server build)* — Try OPAC: [{topic}]({koha['opac_url']})\n"

        # GOOGLE BOOKS
        google_books = google_books_search(topic, limit=3)
        answer += "\n#### Google Books\n"
        if google_books:
            for book in google_books:
                authors = f" by {book['authors']}" if book['authors'] else ""
                pub = f", {book['publisher']}" if book['publisher'] else ""
                year = f" ({book['year']})" if book['year'] else ""
                answer += f"- [{book['title']}]({book['url']}){authors}{pub}{year}\n"
        else:
            answer += "– No relevant books found from Google Books.\n"

        # CORE
        core_results = core_article_search(topic, limit=3)
        answer += "#### 🌐 Open Access (CORE)\n"
        if core_results:
            for art in core_results:
                title = art.get("title", "No Title")
                url = art.get("downloadUrl", art.get("urls", [{}])[0].get("url", "#"))
                year = art.get("createdDate", "")[:4]
                answer += f"- [{title}]({url}) {'('+year+')' if year else ''}\n"
        else:
            answer += "– No recent OA articles found on CORE.\n"

        # arXiv
        arxiv_results = arxiv_article_search(topic, limit=3)
        answer += "#### 📄 arXiv (Preprints)\n"
        if arxiv_results:
            for art in arxiv_results:
                answer += f"- [{art['title']}]({art['url']}) ({art['year']})\n"
        else:
            answer += "– No preprints found on arXiv.\n"

        # DOAJ
        doaj_results = doaj_article_search(topic, limit=3)
        answer += "#### 📚 DOAJ (Open Access Journals)\n"
        if doaj_results:
            for art in doaj_results:
                answer += f"- [{art['title']}]({art['url']}) ({art['year']}) - {art['journal']}\n"
        else:
            answer += "– No OA journal articles found on DOAJ.\n"

        # DataCite
        datacite_results = datacite_article_search(topic, limit=3)
        answer += "#### 🏷️ DataCite\n"
        if datacite_results:
            for art in datacite_results:
                answer += f"- [{art['title']}]({art['url']}) ({art['year']}) - {art['journal']}\n"
        else:
            answer += "– No entries found on DataCite.\n"

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
