import streamlit as st
import requests
import os
import logging
import re
import feedparser
import time
from io import BytesIO
from PyPDF2 import PdfReader

# Optional: For text-to-speech
# import pyttsx3

# ---------------------- Configuration ----------------------
st.set_page_config(
    page_title="Ashu AI @ BU Library",
    page_icon="https://play-lh.googleusercontent.com/kCXMe_CDJaLcEb_Ax8hoSo9kfqOmeB7VoB4zNI5dCSAD8QSeNZE1Eow4NBXx-NjTDQ",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Logging
timestamp = time.strftime("%Y%m%d-%H%M%S")
logging.basicConfig(
    filename=f'app_{timestamp}.log',
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# API Keys
gemini_key = st.secrets.get("GEMINI_API_KEY", os.getenv("GEMINI_API_KEY"))
core_key = st.secrets.get("CORE_API_KEY", os.getenv("CORE_API_KEY"))

# Endpoints
GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
CORE_ENDPOINT = "https://api.core.ac.uk/v3/search/works"
GOOGLE_BOOKS_API = "https://www.googleapis.com/books/v1/volumes"

# ---------------------- Utility Functions ----------------------
def stream_gemini(prompt):
    """Stream response from Gemini API token by token."""
    headers = {"Content-Type": "application/json", "X-goog-api-key": gemini_key}
    payload = {"prompt": prompt, "stream": True}
    response = requests.post(GEMINI_ENDPOINT, json=payload, headers=headers, stream=True)
    for line in response.iter_lines(decode_unicode=True):
        if line:
            data = line.replace('data: ', '')
            try:
                part = requests.utils.json.loads(data)
                text = part.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', '')
                yield text
            except:
                continue


def summarize_pdf(uploaded_file):
    reader = PdfReader(uploaded_file)
    full_text = "".join(page.extract_text() or '' for page in reader.pages)
    # Truncate if too large
    prompt = f"Summarize the following document concisely:\n{full_text[:2000]}"
    # For simplicity, call Gemini in non-stream
    resp = requests.post(
        GEMINI_ENDPOINT,
        json={"prompt": prompt},
        headers={"Content-Type": "application/json", "X-goog-api-key": gemini_key},
        timeout=30
    )
    try:
        return resp.json()['candidates'][0]['content']['parts'][0]['text']
    except:
        return "Summarization failed."


def search_google_books(title):
    params = {"q": title, "maxResults": 3}
    r = requests.get(GOOGLE_BOOKS_API, params=params)
    if r.status_code != 200:
        return []
    data = r.json().get('items', [])
    results = []
    for item in data:
        info = item['volumeInfo']
        results.append({
            'title': info.get('title'),
            'authors': info.get('authors', []),
            'thumbnail': info.get('imageLinks', {}).get('thumbnail'),
            'infoLink': info.get('infoLink')
        })
    return results

# ---------------------- Main UI ----------------------

def inject_css():
    st.markdown("""
    <style>
        :root { --header-color: #2e86c1; }
        .chat-container { max-width: 800px; margin: auto; }
        .typing { color: #888; font-style: italic; }
    </style>
    """, unsafe_allow_html=True)

inject_css()

st.title("Ashu AI Assistant @ BU Library 🚀")

# Sidebar for file upload and features
with st.sidebar:
    st.header("Features")
    upload = st.file_uploader("Upload PDF to Summarize", type=["pdf"])
    if upload:
        with st.spinner("Summarizing PDF..."):
            summary = summarize_pdf(upload)
        st.subheader("PDF Summary")
        st.write(summary)

    st.markdown("---")
    st.subheader("Book Recommendations 📚")
    book_query = st.text_input("Enter a book title or topic:")
    if st.button("Recommend Books") and book_query:
        recs = search_google_books(book_query)
        for r in recs:
            st.image(r['thumbnail'], width=100)
            st.write(f"**{r['title']}** by {', '.join(r['authors'])}")
            st.write(r['infoLink'])

# Chat interface
if 'messages' not in st.session_state:
    st.session_state['messages'] = []

user_input = st.chat_input("")

if user_input:
    st.session_state['messages'].append({"role": "user", "content": user_input})

# Render messages
chat_placeholder = st.empty()
with chat_placeholder.container():
    for msg in st.session_state['messages']:
        st.chat_message(msg['role']).markdown(msg['content'])

# Streaming response
if user_input:
    assistant_msg = st.chat_message("assistant")
    with assistant_msg:
        stream = stream_gemini(user_input)
        for chunk in stream:
            st.write(chunk, end="")
        # Optional: Text-to-speech
        # engine = pyttsx3.init()
        # engine.say(chunk)
        # engine.runAndWait()
    st.session_state['messages'].append({"role": "assistant", "content": ''})

st.markdown("---")
st.write("© 2025 Ashutosh Mishra | Bennett University Library")
