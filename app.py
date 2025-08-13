import streamlit as st
import requests
from bs4 import BeautifulSoup
import urllib.parse
import pandas as pd
from io import StringIO

# ==============================================================================
# ==== 1. CONFIGURATION & SETUP ================================================
# ==============================================================================

# --- Get API Key from Secrets (Optional, for general questions) ---
# You can add your Gemini API key to Streamlit secrets for more advanced general chat.
# For now, the chatbot will primarily focus on the scraper.
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")

# --- Page Configuration ---
st.set_page_config(
    page_title="Ashu AI Assistant",
    page_icon="🤖",
    layout="centered"
)

# --- Custom CSS for Styling ---
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
        max-width: 800px;
        padding: 2rem 1rem;
    }
    .profile-container {
        text-align: center;
        margin-bottom: 2rem;
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
    .stDataFrame {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
    }
    .footer {
        text-align: center;
        color: #888;
        margin-top: 3rem;
        font-size: 0.9em;
    }
</style>
""", unsafe_allow_html=True)


# ==============================================================================
# ==== 2. KOHA OPAC WEB SCRAPER ================================================
# ==============================================================================

def scrape_koha_opac(query: str):
    """
    Scrapes the Bennett University Koha OPAC for a given query, handling
    SSL errors and pagination.

    Args:
        query: The search term (e.g., "Artificial Intelligence").

    Returns:
        A list of dictionaries, where each dictionary represents a book.
        Returns an empty list if no results are found or an error occurs.
    """
    base_url = "https://libraryopac.bennett.edu.in"
    search_path = f"/cgi-bin/koha/opac-search.pl?idx=ti&q={urllib.parse.quote(query)}"
    current_url = base_url + search_path

    all_books = []
    
    with requests.Session() as session:
        session.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        # Key fix: Ignore SSL certificate verification errors
        session.verify = False
        # Suppress the warning that this causes
        requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

        page_count = 0
        while current_url and page_count < 10: # Safety limit: scrape a max of 10 pages
            try:
                response = session.get(current_url, timeout=20)
                response.raise_for_status()
                soup = BeautifulSoup(response.content, "html.parser")
                results_table = soup.find("table", class_="biblios")
                if not results_table:
                    break

                for row in results_table.find_all("tr", class_=["bibliocol", "bibliocol1"]):
                    title_tag = row.find("a", class_="title")
                    author_tag = row.find("span", class_="author")
                    
                    if title_tag:
                        title = title_tag.get_text(strip=True)
                        detail_link = base_url + title_tag['href']
                        author = author_tag.get_text(strip=True).replace('by', '').strip() if author_tag else "N/A"
                        
                        all_books.append({
                            "Title": title,
                            "Author": author,
                            "Link": detail_link
                        })

                next_page_tag = soup.find("a", class_="next")
                if next_page_tag and next_page_tag.has_attr('href'):
                    current_url = base_url + next_page_tag['href']
                    page_count += 1
                else:
                    current_url = None

            except requests.exceptions.RequestException as e:
                st.error(f"A network error occurred while scraping: {e}")
                current_url = None
    
    return all_books


# ==============================================================================
# ==== 3. CHATBOT LOGIC ========================================================
# ==============================================================================

def handle_user_query(prompt: str):
    """
    Handles the user's prompt and routes it to the correct function.
    This is the main "brain" of the chatbot.
    """
    pl = prompt.lower().strip()
    book_keywords = ["find books on", "search for books on", "books on", "show me books on", "get books on"]

    # Check if the prompt is a request to find books
    if any(pl.startswith(kw) for kw in book_keywords):
        # Extract the topic from the prompt by removing the keyword part
        for kw in book_keywords:
            if pl.startswith(kw):
                topic = pl[len(kw):].strip()
                break
        
        if not topic:
            st.warning("Please specify a topic to search for. For example: *Find books on Artificial Intelligence*.")
            return

        with st.spinner(f"Searching the library catalog for books on '{topic}'... This may take a moment."):
            scraped_books = scrape_koha_opac(topic)

        if not scraped_books:
            st.info(f"Sorry, I couldn't find any books matching '{topic}' in the library catalog. Please try a different search term.")
            return

        # --- Display results in the chatbot ---
        st.success(f"Found {len(scraped_books)} books on '{topic}':")
        df = pd.DataFrame(scraped_books)

        # To make the link clickable in the dataframe, we format it as HTML
        df['Link'] = df['Link'].apply(lambda x: f'<a href="{x}" target="_blank">View Details</a>')
        st.markdown(df.to_html(escape=False, index=False), unsafe_allow_html=True)

        # --- Provide a CSV download button ---
        csv = pd.DataFrame(scraped_books).to_csv(index=False).encode('utf-8')
        st.download_button(
            label="⬇️ Download Full List as CSV",
            data=csv,
            file_name=f"{topic.replace(' ', '_')}_books.csv",
            mime="text/csv",
            use_container_width=True
        )
        return
    
    # --- Fallback for general questions ---
    else:
        # For any other query, provide a helpful default response.
        # You can integrate Gemini API here for more advanced chat if needed.
        st.info("I am Ashu, your library assistant. I can help you find books in the Bennett University library catalog. Try asking me: **'Find books on Python'** or **'Books on Machine Learning'**.")
        return


# ==============================================================================
# ==== 4. STREAMLIT UI =========================================================
# ==============================================================================

# --- Header ---
st.markdown("""
<div class="profile-container">
    <img src="https://library.bennett.edu.in/wp-content/uploads/2024/05/WhatsApp-Image-2024-05-01-at-12.41.02-PM-e1714549052999-150x150.jpeg"
         width="120"
         style="border-radius: 50%; border: 3px solid var(--header-color);">
    <h1 style="color: var(--header-color); margin-bottom: 0.5rem;">Ashu AI Assistant</h1>
    <p>Your guide to the Bennett University Library catalog.</p>
</div>
""", unsafe_allow_html=True)

# --- Initialize Chat History ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! How can I help you find books in the library today?"}
    ]

# --- Display Chat History ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"], unsafe_allow_html=True)

# --- Chat Input Field ---
if prompt := st.chat_input("Ask me to find books, e.g., 'books on physics'"):
    # Add user message to history and display it
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate and display assistant response
    with st.chat_message("assistant"):
        # The handle_user_query function will use st elements directly
        # so we don't need to capture and display its return value here.
        handle_user_query(prompt)

    # We need to rerun to see the download button and dataframe properly
    # This is a common pattern when using complex interactive elements in Streamlit.
    st.rerun()

# --- Footer ---
st.markdown("""
<div class="footer">
    <p>© 2025 - Ashutosh Mishra | All Rights Reserved</p>
</div>
""", unsafe_allow_html=True)
