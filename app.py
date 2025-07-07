import streamlit as st
import requests
import os

# Secure Gemini API Key Handling (from Streamlit secrets or environment variable)
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"] if "GEMINI_API_KEY" in st.secrets else os.getenv("GEMINI_API_KEY")
GEMINI_API_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent"

# Set page configuration
st.set_page_config(
    page_title="Ashu AI @ BU Library",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS styling
def inject_custom_css():
    custom_css = """
    <style>
        :root {
            --header-color: #2e86c1;
        }
        .main .block-container {
            max-width: 900px;
            padding: 2rem 1rem;
        }
        .profile-container {
            text-align: center;
            margin-bottom: 1rem;
        }
        .quick-actions-row {
            display: flex;
            justify-content: center;
            gap: 10px;
            margin: 1rem 0 2rem 0;
            width: 100%;
        }
        .quick-action-btn {
            background-color: #2e86c1;
            color: white !important;
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
        .chat-container {
            margin: 2rem 0;
        }
        .static-chat-input {
            position: fixed;
            bottom: 80px;
            left: 50%;
            transform: translateX(-50%);
            width: 100%;
            max-width: 800px;
            z-index: 100;
        }
        .stChatInput input {
            border-radius: 25px !important;
            padding: 12px 20px !important;
        }
        .stChatInput button {
            border-radius: 50% !important;
            background-color: var(--header-color) !important;
        }
        .footer {
            position: fixed;
            bottom: 0;
            left: 0;
            right: 0;
            text-align: center;
            color: #666;
            padding: 1rem;
            background-color: white;
            z-index: 99;
        }
    </style>
    """
    st.markdown(custom_css, unsafe_allow_html=True)

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

def main():
    inject_custom_css()

    # Header Section - Centered
    with st.container():
        st.markdown("""
        <div class="profile-container">
            <img src="https://library.bennett.edu.in/wp-content/uploads/2024/05/WhatsApp-Image-2024-05-01-at-12.41.02-PM-e1714549052999-150x150.jpeg" 
                 width="150" 
                 style="border-radius: 50%; border: 3px solid #2e86c1; margin-bottom: 1rem;">
            <h1 style="color: #2e86c1; margin-bottom: 0.5rem; font-size: 2em;">Ashu AI Assistant at Bennett University Library</h1>
        </div>
        """, unsafe_allow_html=True)

    # Quick Actions - Horizontal and Centered using columns
    quick_actions = [
        ("Find e-Resources", "https://bennett.refread.com/#/home"),
        ("Find Books", "https://libraryopac.bennett.edu.in/"),
        ("Working Hours", "https://library.bennett.edu.in/index.php/working-hours/"),
        ("Book GD Rooms", "http://10.6.0.121/gdroombooking/")
    ]

    cols = st.columns(4)
    for i, (text, url) in enumerate(quick_actions):
        with cols[i]:
            st.markdown(
                f'<a href="{url}" target="_blank" class="quick-action-btn">{text}</a>', 
                unsafe_allow_html=True
            )

    # Welcome message below buttons
    with st.container():
        st.markdown("""
        <div style="text-align: center; margin: 2rem 0;">
            <p style="font-size: 1.1em;">Hello! I am Ashu, your AI assistant at Bennett University Library. How can I help you today?</p>
        </div>
        """, unsafe_allow_html=True)

    # Chat Container (for previous messages)
    with st.container():
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

    # Static Chat Input at bottom
    st.markdown('<div class="static-chat-input">', unsafe_allow_html=True)
    if prompt := st.chat_input("Ask me anything about BU Library..."):
        st.session_state.messages.append({"role": "user", "content": prompt})

        # Gemini API Call
        try:
            if not GEMINI_API_KEY:
                answer = "Gemini API Key is missing. Please set it as a secret in Streamlit Cloud."
            else:
                payload = {
                    "contents": [
                        {
                            "parts": [
                                {
                                    "text": (
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
                                }
                            ]
                        }
                    ]
                }
                response = requests.post(
                    f"{GEMINI_API_ENDPOINT}?key={GEMINI_API_KEY}",
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                if response.status_code == 200:
                    answer = response.json().get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "Sorry, I couldn't find an answer.")
                else:
                    answer = f"Connection error: {response.status_code}"
        except Exception as e:
            answer = f"An error occurred: {str(e)}"

        st.session_state.messages.append({"role": "assistant", "content": answer})
        st.rerun()  # Refresh to show new messages
    st.markdown('</div>', unsafe_allow_html=True)

    # Fixed Footer at bottom
    st.markdown("""
    <div class="footer">
        <div style="margin: 0.5rem 0;">
            © 2025 - Ashutosh Mishra | All Rights Reserved
        </div>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
