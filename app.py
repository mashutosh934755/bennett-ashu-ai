# app.py

import os
import logging
import json
import streamlit as st
import openai  # pip install openai
from streamlit.components.v1 import html

# --- Configuration ---
st.set_page_config(
    page_title="Ashu AI @ BU Library",
    page_icon="https://play-lh.googleusercontent.com/kCXMe_CDJaLcEb_Ax8hoSo9kfqOmeB7VoB4zNI5dCSAD8QSeNZE1Eow4NBXx-NjTDQ",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- Logging ---
logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# --- Secrets ---
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
if not OPENAI_API_KEY:
    st.error("Missing OpenAI API key. Set OPENAI_API_KEY in Streamlit secrets.")
openai.api_key = OPENAI_API_KEY

# --- Custom CSS ---
st.markdown("""
<style>
:root { --header-color: #2e86c1; }
.main .block-container { max-width: 900px; padding: 2rem 1rem; }
.profile-container { text-align: center; margin-bottom: 1rem; }
.footer { text-align: center; color: #666; padding: 1rem; }
</style>
""", unsafe_allow_html=True)

# --- Quick Actions ---
quick_actions = [
    ("Find e-Resources", "https://bennett.refread.com/#/home"),
    ("Find Books", "https://libraryopac.bennett.edu.in/"),
    ("Working Hours", "https://library.bennett.edu.in/index.php/working-hours/"),
    ("Book GD Rooms", "http://10.6.0.121/gdroombooking/")
]
st.markdown(
    '<div style="display:flex;justify-content:center;gap:10px;margin:1rem 0;">' +
    ''.join(f'<a href="{url}" target="_blank" style="background:var(--header-color);color:#fff;padding:10px 15px;border-radius:20px;text-decoration:none;">{label}</a>' for label,url in quick_actions) +
    '</div>', unsafe_allow_html=True
)

# --- Real-Time Voice-Enabled AI Chat Interface ---
api_key_js = OPENAI_API_KEY  # passed into JS
chat_html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Ashu AI Voice Chat</title>
  <script src="https://cdn.jsdelivr.net/npm/openai@4.5.0/browser/index.min.js"></script>
  <style>
    body {{ font-family: sans-serif; margin:0; padding:0; }}
    #chat {{ height: 450px; overflow-y: auto; padding:1rem; background:#f4f4f4; }}
    .msg {{ margin:0.5rem 0; }}
    .user {{ text-align:right; color:#2e86c1; }}
    .assistant {{ text-align:left; color:#333; }}
    #controls {{ display:flex; gap:10px; padding:1rem; }}
    #textIn {{ flex:1; padding:10px; font-size:1rem; }}
    #sendBtn, #voiceBtn {{ padding:10px 15px; font-size:1rem; cursor:pointer; }}
  </style>
</head>
<body>
  <div id="chat"></div>
  <div id="controls">
    <button id="voiceBtn">🎙️</button>
    <input id="textIn" placeholder="Type or speak..." />
    <button id="sendBtn">Send</button>
  </div>
  <script>
    const openaiClient = new OpenAI({ apiKey: '{api_key_js}' });
    const chatEl = document.getElementById('chat');
    const textIn = document.getElementById('textIn');
    const sendBtn = document.getElementById('sendBtn');
    const voiceBtn = document.getElementById('voiceBtn');

    let recog;
    if ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window) {
      const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
      recog = new SR(); recog.lang = 'hi-IN'; recog.interimResults = false;
      voiceBtn.onclick = () => { recog.start(); };
      recog.onresult = (e) => { textIn.value = e.results[0][0].transcript; };
    } else { voiceBtn.disabled = true; }

    function appendMsg(text, cls) {
      const d = document.createElement('div'); d.className = 'msg ' + cls; d.textContent = text;
      chatEl.appendChild(d); chatEl.scrollTop = chatEl.scrollHeight;
      if (cls === 'assistant') speak(text);
    }

    function speak(text) {
      if (!('speechSynthesis' in window)) return;
      const utt = new SpeechSynthesisUtterance(text); utt.lang = 'hi-IN'; speechSynthesis.speak(utt);
    }

    async function sendMessage() {
      const userText = textIn.value.trim(); if (!userText) return;
      appendMsg(userText, 'user'); textIn.value = '';

      const chatHistory = [], msgs = chatEl.querySelectorAll('.msg');
      msgs.forEach(m => chatHistory.push({ role: m.classList.contains('user') ? 'user' : 'assistant', content: m.textContent }));

      const stream = await openaiClient.chat.completions.create(
        { model: 'gpt-4o-mini', stream: true, messages: chatHistory }
      );

      let assistantText = '';
      for await (const chunk of stream) {
        const delta = chunk.choices[0].delta.content;
        if (delta) assistantText += delta;
        const lastMsg = chatEl.lastElementChild;
        if (lastMsg && lastMsg.classList.contains('assistant')) {
          lastMsg.textContent = assistantText;
        } else {
          appendMsg(assistantText, 'assistant');
        }
      }
    }

    sendBtn.onclick = sendMessage;
    textIn.addEventListener('keypress', e => { if (e.key === 'Enter') sendMessage(); });
  </script>
</body>
</html>
"""

# Render the chat interface
ehtml = html(chat_html, height=550)

# --- Footer ---
st.markdown("""
<div class="footer">© 2025 Ashutosh Mishra | Bennett University Library</div>
""", unsafe_allow_html=True)
