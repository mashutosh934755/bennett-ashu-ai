# app.py
import streamlit as st
from streamlit_mic_recorder import speech_to_text
from gtts import gTTS
import tempfile, os
import requests
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

# ————— Configuration —————————————————————————————————————————
st.set_page_config(page_title="Ashu AI – Bennett Library", page_icon="🤖")

# Sample FAQ list
FAQ = [
    ("How can I borrow books?", "You may borrow books via automated kiosks inside the library."),
    ("How do I return books?", "You can return books 24×7 at the Drop Box outside the library."),
    ("What if fines overdue?", "Overdue emails are sent automatically. Or check OPAC at https://libraryopac.bennett.edu.in/"),
    ("Can I access journals remotely?", "Yes, at https://bennett.refread.com/#/home — available 24×7."),
    ("How to reserve books?", "Reserve via the 'Place Hold' feature in OPAC."),
    ("Can alumni use library?", "Alumni may access the library for reference purposes."),
    ("How to recommend a book?", "Fill the Recommendation Form linked on the library website."),
    ("How do I appeal a fine?", "Contact libraryhelpdesk@bennett.edu.in or visit HelpDesk."),
    ("Printer available?", "Printing/Scanning is available in LRC from 09:00 AM to 05:30 PM.")
]

questions = [q for q,_ in FAQ]
answers = [a for _,a in FAQ]

@st.cache(allow_output_mutation=True, show_spinner=False)
def load_embed_model():
    return SentenceTransformer("all-MiniLM-L6-v2")

model = load_embed_model()
q_emb = model.encode(questions, convert_to_numpy=True)

def get_semantic_answer(query, threshold=0.55):
    emb = model.encode([query], convert_to_numpy=True)[0]
    sims = cosine_similarity([emb], q_emb)[0]
    idx = int(np.argmax(sims))
    if sims[idx] >= threshold:
        return answers[idx]
    return None

# Optional Gemini fallback
def call_gemini_api(query: str):
    key = st.secrets.get("GEMINI_API_KEY", "")
    if not key:
        return None
    payload = {
        "contents": [
            {"parts":[{"text": ("You are Ashu, AI assistant for Bennett University Library. "
                                "Answer based on FAQ and library data. Question: "+query)}]}
        ]
    }
    try:
        resp = requests.post(
            "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
            headers={"Content-Type":"application/json", "X-goog-api-key": key},
            json=payload,
            timeout=10
        )
        if resp.status_code == 200:
            parts = resp.json().get("candidates", [{}])[0] \
                      .get("content", {}).get("parts", [])
            if parts:
                return parts[0].get("text")
    except:
        pass
    return None

def get_answer(query):
    ans = get_semantic_answer(query)
    if ans is not None:
        return ans
    fallback = call_gemini_api(query)
    return fallback if fallback else (
        "Sorry, I do not know the answer. "
        "Please contact libraryhelpdesk@bennett.edu.in for assistance."
    )

# ————— UI Layout ——————————————————————————————————————————————
st.markdown("<h1 style='text-align:center; color:#2e86c1;'>Ashu AI Assistant<br>Bennett University Library</h1>", unsafe_allow_html=True)
st.markdown("""
<div style='text-align:center; margin-bottom:20px'>
<a href='https://bennett.refread.com/#/home' target='_blank'
   style='margin:5px; padding:8px 14px; background:#2e86c1; color:#fff; border-radius:18px; text-decoration:none;'>
  Find e‑Resources
</a>
<a href='https://libraryopac.bennett.edu.in/' target='_blank'
   style='margin:5px; padding:8px 14px; background:#2e86c1; color:#fff; border-radius:18px; text-decoration:none;'>
  Find Books
</a>
<a href='https://library.bennett.edu.in/index.php/working-hours/' target='_blank'
   style='margin:5px; padding:8px 14px; background:#2e86c1; color:#fff; border-radius:18px; text-decoration:none;'>
  Working Hours
</a>
<a href='http://10.6.0.121/gdroombooking/' target='_blank'
   style='margin:5px; padding:8px 14px; background:#2e86c1; color:#fff; border-radius:18px; text-decoration:none;'>
  Book GD Rooms
</a>
</div><hr/>
""", unsafe_allow_html=True)

# Initiate chat history
if "chat" not in st.session_state:
    st.session_state.chat = []

for msg in st.session_state.chat:
    role = "You" if msg["role"]=="user" else "Ashu"
    st.markdown(f"**{role}:** {msg['content']}")

# Input section
st.write("You can **type** your query or **speak** via mic:")

col1, col2 = st.columns([4,1])
with col1:
    typed_query = st.text_input("💬 Type your question here", key="typed")
with col2:
    voice_query = speech_to_text(
        language='en',
        start_prompt="🎙️ Speak now",
        stop_prompt="🛑 Stop",
        just_once=True,
        use_container_width=True,
        key="voice"
    )

query = ""
if typed_query:
    query = typed_query.strip()
elif "voice_output" in st.session_state:
    query = st.session_state.voice_output.strip()

if query:
    st.session_state.chat.append({"role":"user", "content": query})
    ans = get_answer(query)
    st.session_state.chat.append({"role":"assistant", "content": ans})
    st.rerun()  # ✅ replaced old st.experimental_rerun()

# Playback reply audio
if st.session_state.chat and st.session_state.chat[-1]["role"] == "assistant":
    last_ans = st.session_state.chat[-1]["content"]
    if st.button("🔊 Listen to Ashu", key="tts"):
        tts = gTTS(text=last_ans, lang="en")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as t:
            tts.save(t.name)
            st.audio(t.name, format="audio/mp3")
            os.unlink(t.name)

st.markdown("<p style='text-align:center;color:#888;'>© 2025 Ashutosh Mishra | All Rights Reserved</p>", unsafe_allow_html=True)
