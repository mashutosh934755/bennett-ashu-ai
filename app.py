import streamlit as st
from streamlit_webrtc import webrtc_streamer, AudioProcessorBase, WebRtcMode
import numpy as np
from gtts import gTTS
from pydub import AudioSegment
from pydub.playback import play
import tempfile
import os

# ====== Ashu AI FAQ Knowledgebase ==========
faqMap = [
    (["issue", "borrow", "check-out"], "You may issue or borrow books through automated kiosks installed in the library."),
    (["return", "drop box"], "You may return the books 24×7 at the Drop Box just outside the library."),
    (["overdue"], "Automated overdue mails are sent to you; you can also check it by logging into OPAC at https://libraryopac.bennett.edu.in/."),
    (["journal articles", "articles", "remote access"], "Yes, you have remote access to our digital library 24×7 at https://bennett.refread.com/#/home."),
    (["printers", "scanners", "fax"], "Printing and scanning facilities are available in the LRC from 09:00 AM to 05:30 PM."),
    (["alumni"], "Alumni are always welcome and may access the library for reference."),
    (["laptop", "printers from my laptop"], "For official printouts, email your document to libraryhelpdesk@bennett.edu.in and collect the print from the centre."),
    (["how many books", "checked-out"], "The number of books you can check out depends on your membership category. Please refer to the library’s borrowing policies for details."),
    (["pay my overdue", "fine"], "Overdue fines can be paid through the BU Payment Portal; please update the library staff after payment."),
    (["recommend", "purchase"], "Yes, you may recommend a book for purchase. Fill in the recommendation form provided by the library."),
    (["appeal"], "Please contact the library helpdesk at libraryhelpdesk@bennett.edu.in or visit the helpdesk in person."),
    (["download ebook", "download e-book"], "To download chapters from e-books, visit https://bennett.refread.com/#/home."),
    (["inter library", "loan"], "The library may arrange an interlibrary loan through DELNET. Contact the library staff for more information."),
    (["non bennett", "non-Bennett"], "Non-Bennett users may use the library for reading purposes but cannot check out books."),
    (["find books", "bookshelves"], "Search for a book through the OPAC. Each book has a call number which corresponds to the labels on the shelves."),
    (["snacks", "eatables"], "Eatables are not allowed inside the LRC premises, but you may carry water bottles."),
    (["account still shows", "checked out"], "If your account still shows a book as checked out, please contact the helpdesk or email libraryhelpdesk@bennett.edu.in."),
    (["reserve", "place hold"], "If all copies of a book are issued, you may reserve it using the “Place Hold” feature in the OPAC."),
    (["hello", "hi", "hey", "namaste", "who are you", "your name"], "Hello! I am Ashu, your assistant for Bennett University Library. How can I help you?"),
]

def lookup_faq(user_input):
    q = user_input.lower()
    for keywords, answer in faqMap:
        if any(k in q for k in keywords):
            return answer
    return "Sorry, I do not know the answer to that. Please contact libraryhelpdesk@bennett.edu.in for assistance."

# ====== Streamlit UI ======
st.set_page_config(page_title="Ashu AI – Bennett Library Voice Assistant", page_icon="🤖")
st.markdown("<h1 style='color:#2e86c1;text-align:center;'>Ashu AI Assistant at Bennett University Library</h1>", unsafe_allow_html=True)

# Quick actions/buttons
st.markdown("""
<div style='text-align:center;margin:1em;'>
    <a href='https://bennett.refread.com/#/home' target='_blank' style='margin:5px;padding:8px 16px;background:#2e86c1;color:#fff;border-radius:17px;text-decoration:none;'>Find e-Resources</a>
    <a href='https://libraryopac.bennett.edu.in/' target='_blank' style='margin:5px;padding:8px 16px;background:#2e86c1;color:#fff;border-radius:17px;text-decoration:none;'>Find Books</a>
    <a href='https://library.bennett.edu.in/index.php/working-hours/' target='_blank' style='margin:5px;padding:8px 16px;background:#2e86c1;color:#fff;border-radius:17px;text-decoration:none;'>Working Hours</a>
    <a href='http://10.6.0.121/gdroombooking/' target='_blank' style='margin:5px;padding:8px 16px;background:#2e86c1;color:#fff;border-radius:17px;text-decoration:none;'>Book GD Rooms</a>
</div>
""", unsafe_allow_html=True)

# -- Message history --
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    role = "You" if msg["role"]=="user" else "Ashu"
    st.markdown(f"**{role}:** {msg['content']}")

st.markdown("<hr/>", unsafe_allow_html=True)
st.write("You can either **type your question** below, **or use the mic to ask Ashu AI**.")

# --- TEXT INPUT ---
query = st.text_input("Type your library question...")

# --- VOICE INPUT ---
stt_result = None
with st.expander("🎤 Click to record your voice query:"):
    webrtc_ctx = webrtc_streamer(key="speech-to-text-demo", mode=WebRtcMode.SENDRECV, audio_receiver_size=256)
    if webrtc_ctx.audio_receiver:
        audio_bytes = b''.join([audio.tobytes() for audio in webrtc_ctx.audio_receiver])
        if audio_bytes:
            # NOTE: Real-time streaming speech-to-text is not included in this sample for brevity.
            st.info("Audio captured, but real-time speech recognition from mic requires extra code (Google STT API, etc). For demo, type your question above.")
            # You can use an external speech-to-text service here to convert audio_bytes to text.
            # For demo: pass (no processing)

# When user submits (by text)
if query:
    st.session_state.messages.append({"role": "user", "content": query})
    answer = lookup_faq(query)
    st.session_state.messages.append({"role": "assistant", "content": answer})

    # --- Text-to-speech playback (user can choose) ---
    if st.button("🔊 Suno (Listen to Ashu's reply)"):
        tts = gTTS(answer, lang="en", slow=False)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
            tts.save(fp.name)
            audio = AudioSegment.from_mp3(fp.name)
            st.audio(fp.name)
            os.unlink(fp.name)

    st.rerun()

st.markdown("<div style='text-align:center;color:#999;'>© 2025 - Ashutosh Mishra | All Rights Reserved</div>", unsafe_allow_html=True)
