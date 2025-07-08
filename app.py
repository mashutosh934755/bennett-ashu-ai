import streamlit as st
import requests
import os
import logging

# --- Logging Setup: Logs will be saved to app.log file for easy debugging ---
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# --- API Configuration ---
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"] if "GEMINI_API_KEY" in st.secrets else os.getenv("GEMINI_API_KEY")
GEMINI_API_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent"

# --- CSS Styles: Stored as a variable for better readability & maintainability ---
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
    """Inject custom CSS for app styling and responsive design."""
    st.markdown(CSS_STYLES, unsafe_allow_html=True)

def create_quick_action_button(text, url):
    """Create HTML for a styled quick action button."""
    return f'<a href="{url}" target="_blank" class="quick-action-btn">{text}</a>'

def create_payload(prompt):
    """
    Create a payload for the Gemini API request.

    Args:
        prompt (str): The user input prompt.

    Returns:
        dict: The payload object.
    """
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

def call_gemini_api(payload):
    """
    Send the payload to Gemini API and handle the response.

    Args:
        payload (dict): Payload for Gemini API.

    Returns:
        str: Gemini API answer or error message.
    """
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
    """Display the row of quick action buttons."""
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

# --- Session state for chat history ---
if "messages" not in st.session_state:
    st.session_state.messages = []

def main():
    inject_custom_css()

    # --- Header Section ---
    st.markdown("""
    <div class="profile-container">
        <img src="https://library.bennett.edu.in/wp-content/uploads/2024/05/WhatsApp-Image-2024-05-01-at-12.41.02-PM-e1714549052999-150x150.jpeg" 
             width="150" 
             style="border-radius: 50%; border: 3px solid #2e86c1; margin-bottom: 1rem;">
        <h1 style="color: #2e86c1; margin-bottom: 0.5rem; font-size: 2em;">Ashu AI Assistant at Bennett University Library</h1>
    </div>
    """, unsafe_allow_html=True)

    show_quick_actions()

    # --- Welcome Message ---
    st.markdown("""
    <div style="text-align: center; margin: 2rem 0;">
        <p style="font-size: 1.1em;">Hello! I am Ashu, your AI assistant at Bennett University Library. How can I help you today?</p>
    </div>
    """, unsafe_allow_html=True)

    # --- Chat History Display ---
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # --- Chat Input at Bottom ---
    st.markdown('<div class="static-chat-input">', unsafe_allow_html=True)
    prompt = st.chat_input("Ask me about BU Library (e.g., 'What are the library hours?')")

    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})

        # --- Show a loading indicator while processing (for user experience) ---
        with st.spinner("Ashu is typing..."):
            payload = create_payload(prompt)
            answer = call_gemini_api(payload)

        st.session_state.messages.append({"role": "assistant", "content": answer})
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # --- Fixed Footer ---
    st.markdown("""
    <div class="footer">
        <div style="margin: 0.5rem 0;">
            © 2025 - Ashutosh Mishra | All Rights Reserved
        </div>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
