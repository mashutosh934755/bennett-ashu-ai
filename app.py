import streamlit as st
import requests
import os
import logging

# Logging setup
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Gemini API config
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"] if "GEMINI_API_KEY" in st.secrets else os.getenv("GEMINI_API_KEY")
GEMINI_API_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent"

# Koha Demo API config
KOHA_API_URL = "https://demo-admin.bibkat.no/api/v1/biblios"
KOHA_USERNAME = "demo"
KOHA_PASSWORD = "demo"
KOHA_HEADERS = {"Accept": "application/json"}

# CSS styles
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

def create_payload(prompt):
    system_instruction = (
        "You are Ashu, an AI assistant for Bennett University Library. "
        # ... [unchanged: same as your code]
        f"User question: {prompt}"
    )
    return {
        "contents": [
            {"parts": [{"text": system_instruction}]}
        ]
    }

def call_gemini_api(payload):
    if not GEMINI_API_KEY:
        logging.error("Gemini API Key is missing.")
        return "Gemini API Key is missing. Please set it as a secret in Streamlit Cloud."
    try:
        response = requests.post(
            f"{GEMINI_API_ENDPOINT}?key={GEMINI_API_KEY}",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=15
        )
        if response.status_code == 200:
            try:
                candidates = response.json().get("candidates", [{}])
                answer = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "No answer found.")
                logging.info("Gemini API success: %s", answer[:100])
            except Exception as e:
                logging.error(f"Error parsing response: {e}")
                answer = "An error occurred while processing your request."
        else:
            answer = f"Connection error: {response.status_code} - {response.text}"
            logging.error(answer)
    except requests.RequestException as e:
        answer = "A network error occurred. Please try again later."
        logging.error(f"Network/API error: {e}")
    return answer

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

# --- Koha Book Search Function ---
def search_koha_books(title):
    url = f"{KOHA_API_URL}?title={title}"
    try:
        response = requests.get(url, auth=(KOHA_USERNAME, KOHA_PASSWORD), headers=KOHA_HEADERS, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API Error: {response.status_code}")
            return []
    except Exception as e:
        st.error(f"Request failed: {e}")
        return []

if "messages" not in st.session_state:
    st.session_state.messages = []

def main():
    inject_custom_css()

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

    # --- NEW SECTION: Koha Book Search ---
    st.markdown("### 📚 Book Search (Koha Demo)")
    st.markdown("Search for books in the <b>Koha Demo Library</b> by title (English):", unsafe_allow_html=True)
    search_term = st.text_input("Enter book title, e.g. Python, History, Data Science, etc.")

    if search_term:
        with st.spinner("Searching Koha Demo Library..."):
            books = search_koha_books(search_term)
        if books and isinstance(books, list):
            st.success(f"Found {len(books)} result(s) for '{search_term}':")
            for book in books:
                st.markdown(
                    f"""
                    <div style="padding:10px; margin:10px 0; border:1px solid #2e86c1; border-radius:16px; background:#f7fafc;">
                    <b>Title:</b> {book.get('title', 'N/A')}<br>
                    <b>Author:</b> {book.get('author', 'N/A')}<br>
                    <b>Year:</b> {book.get('publication_year', 'N/A')}<br>
                    <b>ISBN:</b> {book.get('isbn', 'N/A')}
                    </div>
                    """, unsafe_allow_html=True
                )
        else:
            st.info("No books found for your search. Try another keyword.")

    # --- Chatbot Section ---
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    st.markdown('<div class="static-chat-input">', unsafe_allow_html=True)
    prompt = st.chat_input("Ask me about BU Library (e.g., 'What are the library hours?')")

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.spinner("Ashu is typing..."):
            payload = create_payload(prompt)
            answer = call_gemini_api(payload)
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

if __name__ == "__main__":
    main()
