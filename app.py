import streamlit as st
import requests
from streamlit_speech_recognition import speech_to_text
import os

# ----------------- CONFIG -----------------
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"] if "GEMINI_API_KEY" in st.secrets else os.getenv("GEMINI_API_KEY")
GEMINI_API_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent"

# -------------- CSS STYLE --------------
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
    @media (max-width: 700px) { .main .block-container { padding: 0.5rem 0.2rem; } .static-chat-input { max-width: 98vw; } }
</style>
"""
def inject_custom_css():
    st.markdown(CSS_STYLES, unsafe_allow_html=True)

# ------------- QUICK ACTIONS --------------
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

# ------------- PAYLOAD FOR GEMINI --------------
def create_payload(prompt, lang):
    sys_inst = {
        "en": (
            "You are Ashu, an AI assistant for Bennett University Library. "
            "Answer concisely. FAQs: "
            "- Library timings: Weekdays 8AM-12AM, Weekends/Holidays 9AM-5PM. "
            "- Find books: https://libraryopac.bennett.edu.in/ . "
            "- E-Resources: https://bennett.refread.com/#/home . "
            "- Book GD Room: http://10.6.0.121/gdroombooking/ ."
            " If unrelated, politely redirect to library topics."
            f" User question: {prompt}"
        ),
        "hi": (
            "आप Ashu, Bennett University Library के AI सहायक हैं। जवाब संक्षिप्त और सही दें। मुख्य जानकारी:"
            "- लाइब्रेरी समय: सप्ताह के दिन 8AM-12AM, शनिवार-रविवार/छुट्टी 9AM-5PM। "
            "- पुस्तक खोजें: https://libraryopac.bennett.edu.in/ । "
            "- ई-रिसोर्सेज़: https://bennett.refread.com/#/home । "
            "- GD रूम बुक करें: http://10.6.0.121/gdroombooking/ । "
            " अगर सवाल लाइब्रेरी से न जुड़ा हो तो विनम्रता से redirect करें।"
            f" यूज़र सवाल: {prompt}"
        )
    }
    return {
        "contents": [
            {"parts": [{"text": sys_inst[lang]}]}
        ]
    }

# ------------- GEMINI API CALL --------------
def call_gemini_api(payload):
    if not GEMINI_API_KEY:
        return "❗ Gemini API Key is missing. Please set it in Streamlit Secrets."
    try:
        response = requests.post(
            f"{GEMINI_API_ENDPOINT}?key={GEMINI_API_KEY}",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=20
        )
        if response.status_code == 200:
            try:
                candidates = response.json().get("candidates", [{}])
                answer = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "No answer found.")
            except Exception:
                answer = "❗ Sorry, response format changed."
        else:
            answer = f"❗ Connection error: {response.status_code}"
    except Exception as e:
        answer = f"❗ Network error: {str(e)}"
    return answer

# ------------- TEXT TO SPEECH BUTTON (JS) --------------
def speak_button(text, lang_code):
    safe_text = text.replace("'", "").replace('"', "").replace('\n', ' ')
    js_lang = 'hi-IN' if lang_code == 'hi' else 'en-US'
    st.markdown(
        f"""
        <button onclick="var u=new SpeechSynthesisUtterance('{safe_text}');u.lang='{js_lang}';speechSynthesis.speak(u)">🔊 सुनें / Listen</button>
        """,
        unsafe_allow_html=True
    )

# ---------------- MAIN APP -----------------
def main():
    inject_custom_css()

    # Language Toggle
    st.markdown('<div style="text-align:right">🌐', unsafe_allow_html=True)
    lang = st.radio(
        "Choose Language / भाषा चुनें", 
        options=[('English', 'en'), ('हिंदी', 'hi')],
        format_func=lambda x: x[0],
        horizontal=True,
        label_visibility="collapsed"
    )
    lang_code = lang[1]

    # Header/Profile
    st.markdown("""
    <div class="profile-container">
        <img src="https://library.bennett.edu.in/wp-content/uploads/2024/05/WhatsApp-Image-2024-05-01-at-12.41.02-PM-e1714549052999-150x150.jpeg" 
             width="150" alt="Ashu AI Assistant"
             style="border-radius: 50%; border: 3px solid #2e86c1; margin-bottom: 1rem;">
        <h1 style="color: #2e86c1; margin-bottom: 0.5rem; font-size: 2em;">Ashu AI Assistant at Bennett University Library</h1>
    </div>
    """, unsafe_allow_html=True)

    show_quick_actions()

    # Welcome
    st.markdown(f"""
    <div style="text-align: center; margin: 2rem 0;">
        <p style="font-size: 1.1em;">
            {"Hello! I am Ashu, your AI assistant at Bennett University Library. How can I help you today?" if lang_code == "en" else "नमस्ते! मैं Ashu हूं, आपकी लाइब्रेरी AI सहायक। क्या मदद कर सकता हूं?"}
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Session for chat
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # --- Speech-to-Text Section (Hindi/English) ---
    st.write("🎤 बोलकर पूछें / Speak your question:")
    user_voice = speech_to_text(language='hi-IN' if lang_code == 'hi' else 'en-US', use_container_width=True)
    st.session_state['input_text'] = user_voice if user_voice else ""

    # --- Chat Box ---
    st.markdown('<div class="static-chat-input">', unsafe_allow_html=True)
    prompt = st.chat_input(
        "Ask me about BU Library (e.g., 'What are the library hours?')" if lang_code == "en"
        else "लाइब्रेरी के बारे में पूछें (जैसे: 'लाइब्रेरी कब खुलती है?')",
        value=st.session_state.get('input_text', '')
    )

    # Clear Chat Button
    if st.button("🗑️ Clear Chat / चैट साफ करें", use_container_width=True):
        st.session_state.messages = []
        st.experimental_rerun()

    # Show messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant":
                speak_button(message["content"], lang_code)

    # On user input
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.spinner("Ashu is typing..." if lang_code == "en" else "Ashu जवाब दे रहा है..."):
            payload = create_payload(prompt, lang_code)
            answer = call_gemini_api(payload)
        st.session_state.messages.append({"role": "assistant", "content": answer})
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # Footer
    st.markdown("""
    <div class="footer">
        <div style="margin: 0.5rem 0;">
            © 2025 - Ashutosh Mishra | All Rights Reserved
        </div>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
