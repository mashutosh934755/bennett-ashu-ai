import streamlit as st
import requests
from requests.auth import HTTPBasicAuth

# ---- Koha API credentials & URL ----
KOHA_API_BASE = "http://192.168.31.128:8081/api/v1"
KOHA_USER = "ashutosh"
KOHA_PASS = "#Ashu12!@"

# ========== KOHA API FUNCTIONS ==========

def koha_get_all_patrons():
    url = f"{KOHA_API_BASE}/patrons/"
    try:
        resp = requests.get(
            url,
            auth=HTTPBasicAuth(KOHA_USER, KOHA_PASS),
            headers={"Accept": "application/json"}
        )
        if resp.status_code == 200:
            return resp.json()
        else:
            return []
    except Exception:
        return []

def koha_get_all_books():
    url = f"{KOHA_API_BASE}/biblios/"
    try:
        resp = requests.get(
            url,
            auth=HTTPBasicAuth(KOHA_USER, KOHA_PASS),
            headers={"Accept": "application/json"}
        )
        if resp.status_code == 200:
            return resp.json()
        else:
            return []
    except Exception:
        return []

# ========== STREAMLIT UI ==========

st.set_page_config(page_title="Ashu AI Assistant - Bennett University Library", page_icon="📚", layout="centered")

st.markdown("""
    <div style='text-align:center;'>
        <img src="https://library.bennett.edu.in/wp-content/uploads/2024/05/WhatsApp-Image-2024-05-01-at-12.41.02-PM-e1714549052999-150x150.jpeg"
            width="100" style="border-radius:50%;border:2px solid #2e86c1">
        <h1 style="color:#2e86c1;">Ashu AI Assistant at Bennett University Library</h1>
    </div>
    """, unsafe_allow_html=True)

with st.expander("ℹ️ Quick Library Links"):
    st.markdown("""
    - [Find e-Resources](https://bennett.refread.com/#/home)
    - [Find Books (OPAC)](https://libraryopac.bennett.edu.in/)
    - [Library Working Hours](https://library.bennett.edu.in/index.php/working-hours/)
    - [Book Group Discussion Room](http://10.6.0.121/gdroombooking/)
    """)

st.markdown("---")

st.markdown("#### What would you like to do?")
option = st.selectbox(
    "Choose one:",
    ["Ask Library Chatbot", "Show All Patrons", "Show All Books (Biblios)"]
)

# --------- Ask Chatbot -----------
if option == "Ask Library Chatbot":
    st.markdown("Type your library-related question (English/Hindi):")
    prompt = st.text_input("Your question:", key="chat_input")

    if st.button("Ask"):
        # Aap yahan Gemini/OpenAI ya custom logic laga sakte hain
        if not prompt.strip():
            st.warning("Please enter a question.")
        else:
            st.info("Yahan abhi demo response hai. Isko Gemini/OpenAI ya aur API se connect kar sakte hain.")
            st.success(f"**Q:** {prompt}\n\n**A:** Bennett University Library chatbot active! Aapka sawal: *{prompt}*")

# --------- Show All Patrons ---------
elif option == "Show All Patrons":
    st.markdown("##### 👤 All Koha Patrons (via API):")
    patrons = koha_get_all_patrons()
    if patrons:
        for p in patrons:
            st.write(f"{p['firstname']} {p['surname']} - {p['cardnumber']}")
    else:
        st.warning("No patrons found or API not reachable.")

# --------- Show All Books (Biblios) ---------
elif option == "Show All Books (Biblios)":
    st.markdown("##### 📚 All Koha Books (Biblios via API):")
    books = koha_get_all_books()
    if books:
        for b in books:
            title = b.get("title", "No Title")
            pub = b.get("publisher", "")
            year = b.get("publication_year", "") or b.get("copyright_date", "")
            st.write(f"**{title}** | {pub} | {year}")
    else:
        st.warning("No books found or API not reachable.")

st.markdown("""
    <div style='text-align:center;margin-top:40px;color:#888'>
    © 2025 - Ashutosh Mishra | Bennett University Library
    </div>
    """, unsafe_allow_html=True)
