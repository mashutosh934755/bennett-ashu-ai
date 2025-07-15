import streamlit as st
import requests
import os
import logging
import re
import feedparser  # pip install feedparser

st.set_page_config(
    page_title="Ashu AI @ BU Library",
    page_icon="https://play-lh.googleusercontent.com/kCXMe_CDJaLcEb_Ax8hoSo9kfqOmeB7VoB4zNI5dCSAD8QSeNZE1Eow4NBXx-NjTDQ",
    layout="centered",
    initial_sidebar_state="collapsed"
)

logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
CORE_API_KEY = st.secrets.get("CORE_API_KEY", os.getenv("CORE_API_KEY"))
GOOGLE_BOOKS_API_KEY = st.secrets.get("GOOGLE_BOOKS_API_KEY", os.getenv("GOOGLE_BOOKS_API_KEY"))

GEMINI_API_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
CORE_API_ENDPOINT = "https://api.core.ac.uk/v3/search/works"

CSS_STYLES = """
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
"""
def inject_custom_css():
    st.markdown(CSS_STYLES, unsafe_allow_html=True)

def create_quick_action_button(text, url):
    return f'<a href="{url}" target="_blank" class="quick-action-btn">{text}</a>'

# -------------- Google Books API --------------
def google_books_search(query, limit=5):
    API_KEY = GOOGLE_BOOKS_API_KEY
    if not API_KEY:
        return []
    url = f"https://www.googleapis.com/books/v1/volumes?q={query}&maxResults={limit}&key={API_KEY}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
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
        else:
            return []
    except Exception:
        return []

# ... [Other article search functions remain unchanged] ...

# -------------- Main Handler --------------
def handle_user_query(prompt):
    # Book search (priority check)
    if "find books on" in prompt.lower() or "find book on" in prompt.lower():
        topic = (
            prompt.lower()
            .replace("find books on", "")
            .replace("find book on", "")
            .strip()
        )
        opac_link = f"https://libraryopac.bennett.edu.in/"
        answer = (
            f"### 🏷️ To find books on **{topic.title()}**:\n"
            f"- Visit the Bennett University Library OPAC: [Search here]({opac_link}) "
            "and enter your topic or book title in the search field. For digital books, explore e-resources at [Refread](https://bennett.refread.com/#/home).\n\n"
        )
        # --- Google Books Integration ---
        google_books = google_books_search(topic, limit=5)
        answer += "### 📚 Books from Google Books\n"
        if google_books:
            for book in google_books:
                authors = f" by {book['authors']}" if book['authors'] else ""
                pub = f", {book['publisher']}" if book['publisher'] else ""
                year = f" ({book['year']})" if book['year'] else ""
                answer += f"- [{book['title']}]({book['url']}){authors}{pub}{year}\n"
        else:
            answer += "No relevant books found from Google Books.\n"
        return answer

    # ARTICLE SEARCH (Hindi/English: topic detection)
    article_keywords = [
        "article", "articles", "research paper", "journal", "preprint", "open access", "dataset", "साहित्य", "आर्टिकल", "पत्रिका", "जर्नल", "शोध", "पेपर"
    ]
    # ... [Rest of your original function remains unchanged] ...
    # Paste the article search code, Gemini fallback, etc. from your existing code.

# ... [Rest of your original code remains unchanged] ...

if __name__ == "__main__":
    main()
