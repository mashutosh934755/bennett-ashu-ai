import streamlit as st, requests, urllib.parse

def test_koha_api():
    base = st.secrets.get("KOHA_BASE_URL", "").rstrip("/")
    cid  = st.secrets.get("KOHA_CLIENT_ID", "")
    csec = st.secrets.get("KOHA_CLIENT_SECRET", "")
    rid  = st.secrets.get("KOHA_REPORT_AI_ID", "")

    if not all([base, cid, csec, rid]):
        st.error("Secrets missing: KOHA_BASE_URL / CLIENT_ID / CLIENT_SECRET / KOHA_REPORT_AI_ID")
        return

    def _token():
        urls = [f"{base}/oauth/token"]
        if base.endswith("/api/v1"):
            urls.append(base[:-7] + "/oauth/token")
        for url in urls:
            try:
                r = requests.post(
                    url,
                    headers={"Content-Type":"application/x-www-form-urlencoded","Accept":"application/json"},
                    data={"grant_type":"client_credentials","client_id":cid,"client_secret":csec},
                    timeout=12
                )
                if r.status_code == 200 and "access_token" in r.json():
                    return r.json()["access_token"]
            except requests.exceptions.RequestException:
                pass
        return None

    with st.spinner("Contacting Koha…"):
        tok = _token()
        if not tok:
            st.error("❌ Token failed (check network/base URL/credentials/scopes).")
            return
        st.success("✅ Token OK")
        try:
            r = requests.get(
                f"{base}/reports/{rid}/run",
                headers={"Authorization": f"Bearer {tok}","Accept":"application/json"},
                timeout=20
            )
            if r.status_code == 200:
                rows = r.json()
                st.success(f"✅ Reports API OK — {len(rows)} rows")
                if isinstance(rows, list) and rows:
                    st.json(rows[:3])  # preview first 3
            else:
                st.error(f"❌ Reports API error {r.status_code}: {r.text[:200]}")
        except requests.exceptions.RequestException as e:
            st.error(f"❌ Network error: {e}")

# Place a button near the top/header:
if st.button("🔎 Test Koha API", use_container_width=True):
    test_koha_api()

