import streamlit as st
import requests
from requests.auth import HTTPBasicAuth

url = "http://192.168.31.128:8081/api/v1/patrons/"
st.write(f"Testing Koha API: {url}")

try:
    resp = requests.get(
        url, 
        auth=HTTPBasicAuth('ashutosh', '#Ashu12!@'), 
        headers={"Accept": "application/json"}
    )
    st.write("Status code:", resp.status_code)
    st.write("Raw response:", resp.text)
    if resp.status_code == 200:
        data = resp.json()
        st.success("API JSON parsed successfully!")
        st.write(data)
        if data:
            for p in data:
                st.write(f"{p['firstname']} {p['surname']} - {p['cardnumber']}")
        else:
            st.warning("JSON is empty.")
    else:
        st.error(f"API error: {resp.status_code}")
except Exception as e:
    st.error(f"Exception: {e}")
