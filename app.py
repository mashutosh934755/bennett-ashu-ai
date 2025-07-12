import streamlit as st
import requests
import os
import re
import logging

# --- Logging Setup ---
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# --- API Keys from Streamlit secrets or env ---
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
CORE_API_KEY = st.secrets.get("CORE_API_KEY", os.getenv("CORE_API_KEY"))

GEMINI_API_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
CORE_API_ENDPOINT = "https://api.core.ac.uk/v3/search/works"

# --- CSS Styles ---
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
        "Your answers should be concise, friendly, and professional like ChatGPT, supporting Hindi-English mix queries. "
        "Provide accurate answers based on the following FAQ and library info. "
        "Key info: Library site: https://library.bennett.edu.in/ ; Timings: Weekdays 8AM-12AM, Weekends/Holidays 9AM-5PM. "
        "Physical books: https://libraryopac.bennett.edu.in/ ; E-resources: https://bennett.refread.com/#/home ; GD Room Booking: http://10.6.0.121/gdroombooking/ "
        "Borrow/Return: Automated kiosk & 24/7 drop box. Overdue, fine, alumni access etc. as per tutorial/FAQ. "
        "If the question is not library related, politely redirect. "
        f"User question: {prompt}"
    )
    return {
        "contents": [
            {"parts": [{"text": system_instruction}]}
        ]
    }

def call_gemini_api_v2(payload):
    if not GEMINI_API_KEY:
        logging.error("Gemini API Key is missing.")
        return "Sorry, system issue. Please try again later."
    try:
        response = requests.post(
            GEMINI_API_ENDPOINT,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "X-goog-api-key": GEMINI_API_KEY
            },
            timeout=15
        )
        if response.status_code == 200:
            try:
                candidates = response.json().get("candidates", [{}])
                answer = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "No answer found.")
            except Exception as e:
                logging.error(f"Error parsing response: {e}")
                answer = "Sorry, kuch problem aayi. Please try again."
        else:
            answer = "Sorry, backend connection issue."
    except requests.RequestException as e:
        answer = "Sorry, service unavailable. Please try again shortly."
    return answer

def core_article_search(query, limit=20):
    if not CORE_API_KEY:
        return []
    url = f"{CORE_API_ENDPOINT}"
    headers = {"Authorization": f"Bearer {CORE_API_KEY}"}
    params = {"q": query, "limit": limit}
    try:
        r = requests.get(url, headers=headers, params=params, timeout=15)
        if r.status_code == 200:
            return r.json()["results"]
        else:
            return []
    except Exception as e:
        return []

# --- SMART TOPIC DETECTION ---
def is_core_query(prompt):
    # Accept natural mix language and phrases
    keywords = [
        "find research paper", "find research papers", "research articles", "open access article",
        "find papers on", "journal article", "download article", "open access paper",
        "article on", "papers on", "journal on",
        "article", "articles", "research paper", "journal", "journals", "papers", "paper"
    ]
    prompt_lower = prompt.lower()

    # 1. "ML par articles" OR "chatgpt par article chahiye"
    m = re.search(r"([\w\s\-\+]+?)\s*(par|on|about|ke bare mein)", prompt_lower)
    if m:
        topic = m.group(1).strip()
        if any(kw in prompt_lower for kw in keywords):
            return (True, topic)
    # 2. "articles on ML"
    m = re.search(r"(on|par|about|ke bare mein)\s*([\w\s\-\+]+)", prompt_lower)
    if m:
        topic = m.group(2).strip()
        if any(kw in prompt_lower for kw in keywords):
            return (True, topic)
    # 3. "ML ke bare mein journal chahiye"
    m = re.search(r"([\w\s\-\+]+?)\s*ke bare mein\s*(journal|article|research paper|papers)?", prompt_lower)
    if m:
        topic = m.group(1).strip()
        if any(kw in prompt_lower for kw in keywords):
            return (True, topic)
    # 4. "AI article", "chatgpt journal"
    m = re.search(r"([\w\s\-\+]+)\s*(article|articles|journal|journals|research paper|papers)$", prompt_lower)
    if m:
        topic = m.group(1).strip()
        if any(kw in prompt_lower for kw in keywords):
            return (True, topic)
    # 5. "AI", "ML", etc. (one word, but looks like a research query)
    if any(kw in prompt_lower for kw in keywords):
        tokens = prompt_lower.split()
        if len(tokens) == 1:
            return (True, prompt_lower)
    return (False, None)

def clean_topic(topic):
    # Clean up common trailing/leading words and connect ML/AI/DL to full forms
    expansions = {
        "ml": "machine learning",
        "ai": "artificial intelligence",
        "dl": "deep learning",
        "llm": "large language model",
        "nlp": "natural language processing"
    }
    topic = topic.strip(" .?").lower()
    topic = re.sub(r"\b(do|dijiye|chahiye|de do|ka|ke|ki|par|on|about|ke upar|ke bare mein|articles|article|journal|journals|research paper|papers|latest|naye|waale|wala|show|list|open access|open-access|pdf|fulltext|results)\b", "", topic)
    topic = re.sub(r"\s+", " ", topic)
    topic = topic.strip()
    # Expand short forms to full
    if topic in expansions:
        topic = expansions[topic]
    return topic

def handle_user_query(prompt):
    # Core article queries
    core_q, topic = is_core_query(prompt)
    if core_q and topic:
        topic_clean = clean_topic(topic)
        # Don't respond for empty topic
        if not topic_clean or topic_clean in ["article", "journal", "research paper", "papers"]:
            return "Please specify a subject/topic (e.g., 'AI par articles', 'machine learning ke bare mein journal', 'cloud computing paper')."
        # Friendly professional suggestion + CORE results
        answer = (
            f"Sure! You can also explore latest journal articles and e-books on '**{topic_clean.title()}**' anytime at Bennett University e-Resources platform: [Refread](https://bennett.refread.com/#/home).\n\n"
            f"Here are some recent open access research articles on **{topic_clean.title()}**:\n\n"
        )
        # CORE API results (10, sorted by most recent)
        results = core_article_search(topic_clean, limit=20)
        results = sorted(results, key=lambda x: x.get("createdDate", ""), reverse=True)[:10]
        if not results:
            answer += (
                "Sorry, I couldn't find relevant open access research papers right now. "
                "Try a broader or alternate keyword (e.g., 'artificial intelligence' instead of 'AI')."
            )
        else:
            for art in results:
                title = art.get("title", "No Title")
                url = art.get("downloadUrl", art.get("urls", [{}])[0].get("url", "#"))
                year = art.get("createdDate", "")[:4]
                author = ", ".join(a.get("name", "") for a in art.get("authors", [])[:3])
                # Show title (link), author and year for smart ChatGPT-like look
                answer += f"- [{title}]({url})"
                if year or author:
                    answer += " <span style='color:#999;font-size:12px'>"
                    if author: answer += f"{author}"
                    if author and year: answer += ", "
                    if year: answer += f"{year}"
                    answer += "</span>"
                answer += "\n"
        return answer
    # Book queries
    elif "find books on" in prompt.lower() or "find book on" in prompt.lower():
        topic = (
            prompt.lower()
            .replace("find books on", "")
            .replace("find book on", "")
            .strip()
        )
        opac_link = f"https://libraryopac.bennett.edu.in/"
        return (
            f"To find books on **{topic.title()}**, visit the Bennett University Library OPAC: [Search here]({opac_link}) "
            "and enter your topic or book title in the search field. For digital books, explore e-resources at [Refread](https://bennett.refread.com/#/home)."
        )
    else:
        payload = create_payload(prompt)
        return call_gemini_api_v2(payload)

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

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            # Allow HTML for better article display
            st.markdown(message["content"], unsafe_allow_html=True)

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

if __name__ == "__main__":
    main()
