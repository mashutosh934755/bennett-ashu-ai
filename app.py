st.markdown("""
<style>
  /* ====== BRAND ====== */
  :root{ --brand-a:#960820; --brand-b:#0D335E; }

  /* App को modal-width के हिसाब से कॉम्पैक्ट करें */
  .main .block-container{
      max-width: 460px;          /* 900 → 460 (mobile-panel width) */
      padding: 1rem .75rem;      /* tighter padding */
  }

  /* Avatar + Heading */
  .profile-container{ text-align:center; margin: .25rem 0 .5rem 0; }
  .profile-container img{
      width:110px; height:auto; border-radius:50%;
      border: 3px solid var(--brand-b); margin-bottom:.5rem;
  }
  .profile-container h1{
      color: var(--brand-b) !important;
      font-size: 1.35rem !important;
      line-height:1.25; margin:0 .25rem;
  }

  /* Quick action buttons → wrap & smaller pills */
  .quick-actions-row{
      display:flex; flex-wrap:wrap; justify-content:center;
      gap:8px; margin:.5rem 0 1rem 0; width:100%;
  }
  .quick-action-btn{
      background: var(--brand-b); color:#fff !important;
      padding:8px 12px; border-radius:18px; border:0;
      box-shadow:0 2px 5px rgba(0,0,0,.08);
      transition: all .2s; font-size:13px; text-decoration:none; text-align:center;
      cursor:pointer; white-space:nowrap; flex:1 1 46%; max-width:46%;
  }
  @media (max-width:400px){ .quick-action-btn{ flex:1 1 100%; max-width:100%; } }
  .quick-action-btn:hover{ transform:translateY(-1px); box-shadow:0 4px 8px rgba(0,0,0,.12); }

  /* Chat input को fixed न रखें (iframe में footer issues रोकने के लिए) */
  .static-chat-input{ position:unset !important; }

  /* Input/Buttons theme */
  .stChatInput button{ border-radius:50% !important; background: var(--brand-b) !important; }
  .stChatInput input{ border-radius:24px !important; padding:10px 16px !important; }

  /* ====== Streamlit chrome HIDE (footer, toolbar, fullscreen) ====== */
  #MainMenu, header, footer {visibility: hidden !important;}
  [data-testid="stToolbar"]{ display:none !important; }
  [data-testid="stDecoration"]{ display:none !important; }
  .viewerBadge_container__1QSob, .viewerBadge_link__1S137,
  .stAppDeployButton, a[href*="fullscreen"]{ display:none !important; }

  /* Misc tidy */
  html, body, .stApp { overflow-x:hidden; }
</style>
""", unsafe_allow_html=True)
