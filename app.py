import streamlit as st
import requests
from requests.auth import HTTPBasicAuth

# Koha API settings (replace if needed)
KOHA_API_URL = "http://192.168.31.128:8081/api/v1/patrons/"
KOHA_API_USER = "ashutosh"
KOHA_API_PASS = "#Ashu12!@"

st.title("Koha Patrons List (Demo)")

# Button to trigger fetch
if st.button("Show All Patrons"):
    try:
        response = requests.get(
            KOHA_API_URL,
            auth=HTTPBasicAuth(KOHA_API_USER, KOHA_API_PASS),
            headers={"Accept": "application/json"},
            timeout=10
        )
        if response.status_code == 200:
            patrons = response.json()
            if patrons and isinstance(patrons, list):
                st.success(f"Total patrons found: {len(patrons)}")
                for p in patrons:
                    st.write(f"{p.get('firstname', '')} {p.get('surname', '')} - {p.get('cardnumber', '')}")
            else:
                st.warning("No patron data found in API response.")
        else:
            st.error(f"Error: Status {response.status_code} - {response.text}")
    except Exception as e:
        st.error(f"Request failed: {e}")
