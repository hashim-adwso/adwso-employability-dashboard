"""
PUBLIC page – Employability Pathway (retired dashboard).

The Employability Pathway dashboard has moved to ADWSO's sign-in protected organisational app.
This page only shows an announcement with a link; it loads no data.
"""
import base64
from pathlib import Path

import streamlit as st

NEW_URL = "https://adwso-org.streamlit.app"
LOGO = Path(__file__).parent / "assets" / "adwso_logo.png"
NAVY = "#2e3a87"

st.set_page_config(page_title="Employability Pathway – ADWSO", page_icon="📊", layout="centered",
                   initial_sidebar_state="collapsed")

logo = base64.b64encode(LOGO.read_bytes()).decode() if LOGO.exists() else ""

st.markdown(f"""
<style>
  [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"] {{display:none;}}
  .stApp {{background:#eef2f7;}}
  header[data-testid="stHeader"] {{background:transparent;}}
  .block-container {{padding-top:4rem; max-width:760px;}}
  .ep-card {{background:#fff; border-radius:16px; border:1px solid #e1e6ee; box-shadow:0 4px 14px rgba(30,50,110,.10);
             overflow:hidden;}}
  .ep-top {{background:linear-gradient(110deg,{NAVY} 0%,#2f6fb3 55%,#3fa9c4 100%); padding:22px 26px; display:flex;
            align-items:center; gap:18px; flex-wrap:wrap;}}
  .ep-top img {{height:64px; background:#fff; border-radius:12px; padding:6px 8px;}}
  .ep-top h1 {{color:#fff; font-size:1.45rem; margin:0; padding:0; line-height:1.3;}}
  .ep-body {{padding:24px 26px 8px 26px; color:#0b0b0b; font-size:1rem; line-height:1.6;}}
  .ep-body h2 {{color:{NAVY}; font-size:1.2rem; margin:0 0 10px 0; padding:0;}}
  .ep-foot {{color:#52514e; font-size:.8rem; text-align:center; margin-top:18px;}}
</style>
<div class="ep-card">
  <div class="ep-top">
    {'<img src="data:image/png;base64,' + logo + '" alt="ADWSO logo">' if logo else ''}
    <h1>Employability Pathway — VT Graduates Dashboard</h1>
  </div>
  <div class="ep-body">
    <h2>This dashboard has moved</h2>
    <p>ADWSO has launched a detailed <b>organisational dashboard</b>. The Employability Pathway results, together with
    individual records and reports, are now available there to authorised ADWSO staff.</p>
    <p>Please sign in, or sign up to request access, at
    <a href="{NEW_URL}" target="_blank">adwso-org.streamlit.app</a>.</p>
  </div>
</div>
""", unsafe_allow_html=True)

st.link_button("Go to the ADWSO organisational dashboard", NEW_URL, type="primary", width="stretch")

st.markdown("<div class='ep-foot'>Afghanistan Development &amp; Welfare Services Organization (ADWSO)</div>",
            unsafe_allow_html=True)
