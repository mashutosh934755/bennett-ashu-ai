import streamlit as st
from streamlit_mic_recorder import speech_to_text
from gtts import gTTS
import tempfile, os
import requests

# ————————— FAQ Mapping ————————
FAQ_MAP = [
    (["hello", "hi", "hey", "namaste"], 
     "Hello! I am Ashu, your virtual assistant at Bennett University Library. How can I help you?"),
    (["issue", "borrow", "check‑out"], 
     "You may issue or borrow books through the automated kiosks installed in the library."),
    (["return", "drop box"], 
     "You may return books 24×7 at the Drop Box just outside the library."),
    (["overdue"], 
     "Automated overdue emails are sent; you can also check your status on OPAC: https://libraryopac.bennett.edu.in/"),
    (["journal articles", "remote access"], 
     "Yes, you can access our digital library 24×7 at https://bennett.refread.com/#/home"),
    (["printers", "scanners", "fax"], 
     "Printing and scanning services are available in the LRC from 09:00 AM to 05:30 PM."),
    (["alumni"], 
     "Alumni are welcome at the LRC for reference use."),
    (["laptop", "email libraryhelpdesk"], 
     "For official printouts from your laptop, email at libraryhelpdesk@bennett.edu.in and collect them from the LRC."),
    (["recommend"], 
     "To recommend a book, fill out the Google Form linked on the library website."),
    (["appeal"], 
     "If you wish to appeal a fine, contact libraryhelpdesk@bennett.edu.in or visit the HelpDesk."),
    (["download ebook", "download e-book"], 
     "To download chapters from e‑books, visit our digital library platform at the RefRead link above."),
    (["inter library", "loan"], 
     "Inter‑library loan through DELNET is possible. Please contact library staff for assistance."),
    (["non-bennett", "intern"], 
     "Non‑Bennett users or interns are welcome to use the library for reading only—they cannot check out books."),
    (["bookshelves", "shelves", "find books internal"], 
     "Search using OPAC. Refer to call numbers—the shelves are labelled accordingly. Tutorial available online."),
    (["snacks", "eatables"], 
     "No food allowed inside the LRC. You may carry water bottles."),
    (["account still shows", "checked out"], 
     "If you returned a book but your account still shows it checked out, contact the helpdesk or email libraryhelpdesk@bennett.edu.in."),
    (["reserve", "place hold"], 
     "If all copies are issued, you may use the ‘Place Hold’ feature in OPAC to reserve the book."),
]

def lookup_faq(query: str) -> str:
    q = query.lower()
    for keywords, answer in FAQ_MAP:
        if any(k in q for k in keywords):
            return answer
    return ("Sorry, I do not know the answer to that. "
            "Please contact libraryhelpdesk@bennett.edu.in for assistance.")

# ————— Optionally Gemini fallback —————
def call_gemini(prompt: str) -> str:
    key = st.secrets.get("GEMINI_API_KEY", "")
    if not key:
        return None
    payload = {
        "contents": [
            {"parts": [{"text": (
                "You are Ashu AI assistant for Bennett University Library. "
                "Use the FAQ and library info to answer concisely. User question: "+prompt)}]}
        ]
    }
    try:
        resp = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
            headers={"Content-Type": "application/json", "X-goog-api-key": key},
            json=payload,
            timeout=10
        )
        data = resp.json()
        return (data.get("candidates", [{}])[0]
                    .get("content", {}).get("parts", [{}])[0]
                    .get("text"))
    except:
        return None

def generate_answer(query: str) -> str:
    answer = lookup_faq(query)
    if answer.startswith("Sorry"):
        gib = call_gemini(query)
        if gib:
            return gib
    return answer

# ————— Streamlit UI —————
st.set_page_config(page_title="Ashu AI – Bennett Library Assistant", page_icon="🤖")
st.markdown("<h1 style='text-align:center; color:#2e86c1;'>Ashu AI – Bennett University Library</h1>", 
            unsafe_allow_html=True)

# Quick‑action buttons
st.markdown("""
<div style='text-align:center; margin:1em;'>
<a href='https://bennett.refread.com/#/home' target='_blank'
   style='margin:4px; padding:8px 16px; background:#2e86c1; color:white;
         border-radius:20px; text-decoration:none;'>Find e‑Resources</a>
<a href='https://libraryopac.bennett.edu.in/' target='_blank'
   style='margin:4px; padding:8px 16px; background:#2e86c1; color:white;
         border-radius:20px; text-decoration:none;'>Find Books</a>
<a href='https://library.bennett.edu.in/index.php/working-hours/' target='_blank'
   style='margin:4px; padding:8px 16px; background:#2e86c1; color:white;
         border-radius:20px; text-decoration:none;'>Working Hours</a>
<a href='http://10.6.0.121/gdroombooking/' target='_blank'
   style='margin:4px; padding:8px 16px; background:#2e86c1; color:white;
         border-radius:20px; text-decoration:none;'>Book GD Rooms</a>
</div>
""", unsafe_allow_html=True)

# == Session Messages ==
if "chat" not in st.session_state:
    st.session_state.chat = []

# == Display chat history
for item in st.session_state.chat:
    who = "You" if item["role"]=="user" else "Ashu"
    st.markdown(f"**{who}:** {item['content']}")

st.markdown("---")

# =================================================
# Section for Text‑input or Voice‑input
# =================================================
st.write("You can **type your query below**, or **click and speak** to ask.")

col1, col2 = st.columns([3,1])
with col1:
    typed = st.text_input("💬 Type your library question", key="typed_query")
with col2:
    spoken = speech_to_text(
        language='en',
        start_prompt="🎙️ Start speaking",
        stop_prompt="🛑 Stop",
        just_once=True,
        use_container_width=True,
        key="voice_query"
    )

# pick final query
query_text = typed.strip() or st.session_state.get("voice_query_output", "").strip()

if query_text:
    # add user message
    st.session_state.chat.append({"role":"user", "content": query_text})

    # generate answer
    ans = generate_answer(query_text)
    st.session_state.chat.append({"role":"assistant", "content": ans})
    st.experimental_rerun()

# After rerun, chat.loop displays the new messages

# ————— TTS: Option to listen reply ————
if st.session_state.chat and st.session_state.chat[-1]["role"]=="assistant":
    ans = st.session_state.chat[-1]["content"]
    if st.button("🔊 Suno (Listen to Ashu's reply)"):
        tts = gTTS(ans, lang="en", slow=False)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
            tts.save(f.name)
            st.audio(f.name, format="audio/mp3")
            try: os.unlink(f.name)
            except: pass

st.markdown("<div style='text-align:center;color:#666;'>© 2025 – Ashutosh Mishra | All Rights Reserved</div>",
            unsafe_allow_html=True)
