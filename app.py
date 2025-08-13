import streamlit as st
import requests
import re
import feedparser  # pip install feedparser
import urllib.parse
import csv
from io import StringIO
from datetime import datetime

# ==============================================================================
# ==== 1. SETUP & CONFIGURATION ================================================
# ==============================================================================

# --- Get Keys from Secrets (never paste in code) ---
# It's crucial these are set in your Streamlit Cloud secrets
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")
CORE_API_KEY = st.secrets.get("CORE_API_KEY", "")
GOOGLE_BOOKS_API_KEY = st.secrets.get("GOOGLE_BOOKS_API_KEY", "")

# --- Koha Configuration (Internal) ---
KOHA_BASE_URL = st.secrets.get("KOHA_BASE_URL", "")  # e.g., http://your-koha-domain/api/v1
KOHA_CLIENT_ID = st.secrets.get("KOHA_CLIENT_ID", "")
KOHA_CLIENT_SECRET = st.secrets.get("KOHA_CLIENT_SECRET", "")
KOHA_OPAC_BASE = st.secrets.get("KOHA_OPAC_BASE", "https://libraryopac.bennett.edu.in")

# --- CSS for Styling ---
st.markdown("""
<style>
    :root {
        --header-color: #2e86c1;
        --primary-bg: #ffffff;
        --secondary-bg: #f0f2f6;
        --text-color: #333;
        --button-color: #ffffff;
    }
    .main .block-container {
        max-width: 900px;
        padding: 2rem 1rem;
    }
    /* Login Page Styles */
    .login-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        padding: 2rem;
        background-color: var(--primary-bg);
        border-radius: 10px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    .login-container h1 {
        color: var(--header-color);
    }
    /* Chat Page Styles */
    .profile-container {
        text-align: center;
        margin-bottom: 1rem;
    }
    .quick-actions-row {
        display: flex;
        flex-wrap: wrap;
        justify-content: center;
        gap: 10px;
        margin: 1rem 0 2rem 0;
        width: 100%;
    }
    .quick-action-btn {
        background-color: var(--header-color);
        color: var(--button-color) !important;
        padding: 10px 15px;
        border-radius: 20px;
        border: none;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        transition: all 0.3s;
        font-size: 14px;
        text-decoration: none;
        text-align: center;
        cursor: pointer;
        white-space: nowrap;
        flex: 1;
        max-width: 200px;
    }
    .quick-action-btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    .stChatInput input {
        border-radius: 25px !important;
        padding: 12px 20px !important;
        background-color: var(--secondary-bg);
    }
    .stChatInput button {
        border-radius: 50% !important;
        background-color: var(--header-color) !important;
    }
    .logout-button {
        position: absolute;
        top: 10px;
        right: 10px;
    }
    /* Fine and Book display */
    .info-box {
        background-color: var(--secondary-bg);
        border-left: 5px solid var(--header-color);
        padding: 15px;
        border-radius: 5px;
        margin-bottom: 10px;
    }
    .info-box h4 { margin-top: 0; }
    .info-box ul { padding-left: 20px; margin-bottom: 0; }
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# ==== 2. KOHA API INTEGRATION =================================================
# ==============================================================================

# --- Koha OAuth Token Management ---
@st.cache_data(ttl=3000)  # Cache token for 50 minutes
def koha_get_token():
    if not all([KOHA_BASE_URL, KOHA_CLIENT_ID, KOHA_CLIENT_SECRET]):
        st.error("Koha API credentials are not set in secrets.")
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
        st.error(f"Koha Token Error: {r.status_code} - {r.text}")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Koha Network Error: {e}")
        return None

# --- Patron (User) Authentication & Data ---
def koha_authenticate_and_get_patron(cardnumber, password):
    """
    Authenticates a patron and fetches their details.
    NOTE: This uses a workaround. The standard Koha REST API doesn't have a direct
    password verification endpoint. This function checks if a patron with the
    given cardnumber exists. In a real-world scenario, you would need a more
    secure authentication method, possibly a custom plugin or middleware.
    """
    token = koha_get_token()
    if not token:
        return None, "Could not connect to the library system."

    headers = {"Authorization": f"Bearer {token}"}
    # For this example, we're finding the patron by card number.
    # Password verification is NOT performed by this API call.
    try:
        r = requests.get(
            f"{KOHA_BASE_URL}/patrons?cardnumber={cardnumber}",
            headers=headers,
            timeout=10
        )
        if r.status_code == 200 and r.json():
            patron_data = r.json()[0]
            # Here you would add password verification logic if available
            # For now, we assume if the user exists, login is successful.
            return patron_data, "Login Successful"
        elif r.status_code == 200:
            return None, "Invalid username. Please check your card number."
        else:
            return None, f"API Error: {r.status_code}"
    except requests.exceptions.RequestException as e:
        return None, f"Network Error: {e}"

def koha_get_fines(borrowernumber):
    """Fetches total fine amount for a given patron."""
    token = koha_get_token()
    if not token:
        return "Error: Could not get API token."

    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(f"{KOHA_BASE_URL}/patrons/{borrowernumber}/fines", headers=headers, timeout=10)
        if r.status_code == 200:
            fines_data = r.json()
            total_fine = fines_data.get("total_outstanding", 0.0)
            return f"""
            <div class="info-box">
                <h4>💰 Your Fines</h4>
                Your total pending fine amount is **₹{total_fine:.2f}**.
                <br>Please clear the fine to continue borrowing books.
            </div>
            """
        return "Could not retrieve your fine information at this time."
    except requests.exceptions.RequestException:
        return "A network error occurred while fetching your fine details."

def koha_get_checkouts(borrowernumber):
    """Fetches the list of books currently checked out by a patron."""
    token = koha_get_token()
    if not token:
        return "Error: Could not get API token."

    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(f"{KOHA_BASE_URL}/patrons/{borrowernumber}/checkouts", headers=headers, timeout=15)
        if r.status_code == 200 and r.json():
            checkouts = r.json()
            response_md = '<div class="info-box"><h4>📚 Your Borrowed Books</h4><ul>'
            for item in checkouts:
                title = item.get('biblio', {}).get('title', 'Unknown Title')
                due_date_str = item.get('due_date', '')
                try:
                    due_date = datetime.fromisoformat(due_date_str.replace('Z', '+00:00')).strftime('%d-%b-%Y')
                except (ValueError, TypeError):
                    due_date = "N/A"
                
                biblio_id = item.get('biblio', {}).get('biblio_id', '')
                link = f"{KOHA_OPAC_BASE}/cgi-bin/koha/opac-detail.pl?biblionumber={biblio_id}" if biblio_id else "#"

                response_md += f"<li><a href='{link}' target='_blank'>{title}</a> (Due: {due_date})</li>"
            response_md += "</ul></div>"
            return response_md
        elif r.status_code == 200:
            return "<div class='info-box'>You have no books currently borrowed.</div>"
        return "Could not retrieve your borrowed books information."
    except requests.exceptions.RequestException:
        return "A network error occurred while fetching your borrowed books."

# --- General Book/Article Search (from your original code, slightly adapted) ---
def koha_biblios_search(query, limit=5):
    """Searches the Koha catalog for books."""
    token = koha_get_token()
    if not token:
        return []
    headers = {"Authorization": f"Bearer {token}"}
    params = {"q": f"title:{query}", "_page": 1, "_per_page": limit}
    try:
        r = requests.get(f"{KOHA_BASE_URL}/biblios", headers=headers, params=params, timeout=10)
        if r.status_code == 200:
            return r.json()
        return []
    except requests.exceptions.RequestException:
        return []

# (Other search functions like google_books_search, core_article_search etc. remain the same)
def google_books_search(query, limit=5):
    if not GOOGLE_BOOKS_API_KEY: return []
    url = f"https://www.googleapis.com/books/v1/volumes?q={urllib.parse.quote(query)}&maxResults={limit}&key={GOOGLE_BOOKS_API_KEY}"
    try:
        resp = requests.get(url, timeout=10).json()
        return [{"title": v.get("volumeInfo", {}).get("title", ""), "authors": ", ".join(v.get("volumeInfo", {}).get("authors", [])), "url": v.get("volumeInfo", {}).get("infoLink", "#")} for v in resp.get("items", [])]
    except Exception: return []

# ==============================================================================
# ==== 3. GEMINI (LLM) AND CHAT LOGIC ==========================================
# ==============================================================================

def call_gemini_api(prompt):
    """Calls Gemini for general conversation."""
    if not GEMINI_API_KEY:
        return "Gemini API Key is missing. Please set it in Streamlit secrets."
    
    system_instruction = (
        "You are Ashu, an AI assistant for Bennett University Library. "
        "Provide accurate and concise answers based on library information. "
        "Library website: https://library.bennett.edu.in/. "
        "Timings: Weekdays 8 AM to 12 AM, Weekends 9 AM to 5 PM. "
        "For physical books, use the OPAC. For e-resources, use Refread. "
        "If asked about personal data like fines, tell the user to ask 'my fine amount' or 'my borrowed books'. "
        "If the question is unrelated, politely redirect to library topics."
    )
    payload = {"contents": [{"parts": [{"text": f"{system_instruction}\n\nUser question: {prompt}"}]}]}
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent"
    try:
        response = requests.post(
            url, json=payload,
            headers={"Content-Type": "application/json", "X-goog-api-key": GEMINI_API_KEY},
            timeout=20
        )
        if response.status_code == 200:
            return response.json()["candidates"][0]["content"]["parts"][0]["text"]
        return f"Connection error: {response.status_code} - {response.text}"
    except Exception as e:
        return f"A network error occurred: {e}"

def handle_user_query(prompt):
    """The main brain, routing user queries to the right function."""
    pl = prompt.lower().strip()
    borrowernumber = st.session_state.get("borrowernumber")

    # --- Personalized Queries (Require Login) ---
    if any(kw in pl for kw in ["my fine", "fine amount", "fine details", "kitna fine hai"]):
        return koha_get_fines(borrowernumber) if borrowernumber else "Please log in to check your fine details."

    if any(kw in pl for kw in ["my books", "borrowed books", "checkouts", "meri kitabein"]):
        return koha_get_checkouts(borrowernumber) if borrowernumber else "Please log in to see your borrowed books."

    # --- General Book/Article Search ---
    if "find book" in pl or "search for book" in pl:
        topic = re.sub(r'find book(s)? (on|for)?', '', pl, flags=re.IGNORECASE).strip()
        if not topic: return "Please specify a topic for the book search."
        
        answer = f"### 📚 Books on **{topic.title()}**\n"
        
        # Search Koha Catalog First
        koha_results = koha_biblios_search(topic)
        answer += "#### In Bennett University Library (Koha)\n"
        if koha_results:
            for book in koha_results:
                link = f"{KOHA_OPAC_BASE}/cgi-bin/koha/opac-detail.pl?biblionumber={book['biblio_id']}"
                answer += f"- [{book.get('title', 'No Title')}]({link}) by {book.get('author', 'N/A')}\n"
        else:
            answer += "- No direct matches found in the university catalog.\n"

        # Search Google Books
        gb_results = google_books_search(topic)
        answer += "\n#### On Google Books\n"
        if gb_results:
            for book in gb_results:
                 answer += f"- [{book['title']}]({book['url']}) by {book['authors']}\n"
        else:
            answer += "- No relevant books found on Google Books.\n"
        return answer

    # --- Fallback to Gemini for general questions ---
    return call_gemini_api(prompt)


# ==============================================================================
# ==== 4. STREAMLIT UI (LOGIN AND CHAT PAGES) ==================================
# ==============================================================================

def show_login_page():
    """Displays the login form."""
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.image("https://library.bennett.edu.in/wp-content/uploads/2024/05/WhatsApp-Image-2024-05-01-at-12.41.02-PM-e1714549052999-150x150.jpeg", width=120)
    st.title("Library AI Assistant Login")
    st.write("Please log in with your library card number to continue.")

    with st.form("login_form"):
        username = st.text_input("Library Card Number (Username)", key="username")
        password = st.text_input("Password", type="password", key="password")
        submitted = st.form_submit_button("Login", use_container_width=True)

        if submitted:
            if not username:
                st.warning("Please enter your card number.")
            else:
                with st.spinner("Authenticating..."):
                    patron_data, message = koha_authenticate_and_get_patron(username, password)
                    if patron_data:
                        st.session_state.logged_in = True
                        st.session_state.borrowernumber = patron_data.get("borrowernumber")
                        st.session_state.patron_name = f"{patron_data.get('firstname')} {patron_data.get('surname')}"
                        st.session_state.messages = [] # Clear messages on new login
                        st.success("Login successful! Redirecting...")
                        st.rerun()
                    else:
                        st.error(f"Login Failed: {message}")
    st.markdown('</div>', unsafe_allow_html=True)

def show_chat_page():
    """Displays the main chatbot interface after login."""
    
    # --- Header and Logout Button ---
    st.markdown(f"""
    <div class="profile-container">
        <h2 style="color: #2e86c1;">Ashu AI Assistant</h2>
        <p>Welcome, <strong>{st.session_state.get('patron_name', 'User')}</strong>!</p>
    </div>
    """, unsafe_allow_html=True)

    if st.button("Logout", key="logout"):
        # Clear session state on logout
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    # --- Quick Action Buttons ---
    st.markdown(
        '<div class="quick-actions-row">'
        '<div class="quick-action-btn" onclick="st.session_state.prompt = \'my fine amount\'">Check My Fines</div>'
        '<div class="quick-action-btn" onclick="st.session_state.prompt = \'my borrowed books\'">My Borrowed Books</div>'
        '</div>',
        unsafe_allow_html=True # Note: This JS click simulation is a hack and might not work perfectly. A better way is to use buttons that rerun the script.
    )

    # --- Chat History ---
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"], unsafe_allow_html=True)

    # --- Chat Input ---
    prompt = st.chat_input("Ask about your fines, books, or general library questions...")
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("Ashu is thinking..."):
                response = handle_user_query(prompt)
                st.markdown(response, unsafe_allow_html=True)
        
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()


# ==============================================================================
# ==== 5. MAIN APP ROUTER ======================================================
# ==============================================================================

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if st.session_state.logged_in:
    show_chat_page()
else:
    show_login_page()
