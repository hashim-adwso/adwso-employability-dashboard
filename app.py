"""
PUBLIC Streamlit dashboard – Employability Pathway of ADWSO vocational training graduates.

Reads ONLY data/summary.json (pre-aggregated, small numbers suppressed).
It has no access to KoBo and never sees individual records.
"""
import base64
import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Employability Pathway – ADWSO", page_icon="📊", layout="wide",
                   initial_sidebar_state="collapsed")

ROOT = Path(__file__).parent
SUMMARY = ROOT / "data" / "summary.json"
LOGO = ROOT / "assets" / "adwso_logo.png"

# Chart colours: validated categorical palette. Brand colours are used only for page chrome.
BAR = "#2a78d6"
CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
HIDDEN_GREY = "#c9c8c3"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e6e5e1"
NAVY, TEAL, GREEN, BROWN, WHEAT = "#2e3a87", "#2a8fa8", "#1f8a4c", "#9c5a44", "#e3a72f"

CREDIT_NAME = "Hashim Ali Shah"
CREDIT_ROLE = "Program Associate – Grants and Strategic Partnerships"

st.markdown(f"""
<style>
  [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"] {{display:none;}}
  .stApp {{background:#eef2f7;}}
  header[data-testid="stHeader"] {{background:transparent;}}
  .block-container {{padding-top:3.4rem; padding-bottom:3rem; max-width:1280px;}}
  .ep-banner {{background:linear-gradient(110deg,{NAVY} 0%,#2f6fb3 55%,#3fa9c4 100%); border-radius:16px;
               padding:18px 24px; display:flex; align-items:center; gap:20px; flex-wrap:wrap; color:#fff;
               box-shadow:0 4px 14px rgba(30,50,110,.18);}}
  .ep-logo {{background:#fff; border-radius:14px; padding:6px 8px; display:flex; align-items:center;}}
  .ep-logo img {{height:64px; width:auto; display:block;}}
  .ep-title {{flex:1 1 320px; min-width:240px;}}
  .ep-title h1 {{color:#fff; font-size:1.55rem; font-weight:700; margin:0; padding:0; line-height:1.25;}}
  .ep-title p {{color:#e3ecf8; margin:4px 0 0 0; font-size:.92rem;}}
  .ep-pills {{display:flex; flex-direction:column; gap:8px; align-items:flex-end;}}
  .ep-pill {{background:rgba(255,255,255,.16); border:1px solid rgba(255,255,255,.45); border-radius:999px;
             padding:6px 14px; font-size:.8rem; color:#fff; white-space:nowrap;}}
  .ep-pill b {{font-weight:700;}}
  @media (max-width: 760px) {{ .ep-pills {{align-items:flex-start;}} .ep-pill {{white-space:normal;}} }}
  [data-testid="stVerticalBlockBorderWrapper"], [class*="st-key-card"] {{background:#fff; border-radius:14px !important;
      border:1px solid #e1e6ee !important; box-shadow:0 1px 4px rgba(20,40,80,.06); padding:14px 16px;}}
  .ep-kpis {{display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:14px; margin:6px 0 4px 0;}}
  .ep-kpi {{background:#fff; border-radius:14px; padding:14px 16px 12px 16px; border:1px solid #e1e6ee;
            box-shadow:0 1px 4px rgba(20,40,80,.06);}}
  .ep-kpi .lbl {{font-size:.8rem; color:{INK2}; font-weight:600;}}
  .ep-kpi .val {{font-size:2rem; font-weight:700; color:{INK}; line-height:1.15; margin-top:4px;}}
  .ep-kpi .sub {{font-size:.75rem; color:{INK2}; margin-top:2px;}}
  .ep-section {{color:{NAVY}; font-weight:700; font-size:.82rem; letter-spacing:.06em; text-transform:uppercase;
                border-bottom:2px solid #9cc7e6; padding-bottom:6px; margin:18px 0 10px 0;}}
  .ep-card-title {{color:{NAVY} !important; font-weight:700; font-size:1rem !important; margin:0 !important;}}
  .ep-card-sub {{color:{INK2} !important; font-size:.8rem !important; margin:2px 0 4px 0 !important; line-height:1.35;}}
  .stTabs [data-baseweb="tab-list"] {{gap:4px;}}
  .stTabs [data-baseweb="tab"] {{background:#fff; border-radius:10px 10px 0 0; padding:8px 16px;}}
  .ep-footer {{color:{INK2}; font-size:.78rem; text-align:center; margin-top:28px;}}
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=3600)
def load():
    return json.loads(SUMMARY.read_text(encoding="utf-8"))


@st.cache_data
def logo_b64():
    return base64.b64encode(LOGO.read_bytes()).decode() if LOGO.exists() else ""


if not SUMMARY.exists():
    st.title("Employability Pathway")
    st.info("Results will appear here after the first data refresh.")
    st.stop()

S = load()
META = S["meta"]
MIN_CELL, MIN_GROUP = S["rules"]["min_cell"], S["rules"]["min_group"]
DIMS = {"province": "Province", "gender": "Gender", "age_group": "Age group"}

# ---------------------------------------------------------------- banner
period = S.get("period") or ["", ""]
period_txt = period[0] if period[0] == period[1] else f"{period[0]} to {period[1]}"
st.markdown(f"""
<div class="ep-banner">
  <div class="ep-logo"><img src="data:image/png;base64,{logo_b64()}" alt="ADWSO logo"></div>
  <div class="ep-title">
    <h1>Employability Pathway — VT Graduates Dashboard</h1>
    <p>Post-Vocational Training Assessment 2026 · Afghanistan Development &amp; Welfare Services Organization (ADWSO)</p>
  </div>
  <div class="ep-pills">
    <div class="ep-pill">Prepared by <b>{CREDIT_NAME}</b> · {CREDIT_ROLE}</div>
    <div class="ep-pill">Data: {period_txt} · Updated {S['generated']}</div>
  </div>
</div>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------- filter bar
def reset_filters():
    for k in DIMS:
        st.session_state[f"f_{k}"] = "*"
    st.session_state["compare"] = "all"


for k in DIMS:
    st.session_state.setdefault(f"f_{k}", "*")
st.session_state.setdefault("compare", "all")

with st.container(border=True, key="card_filters"):
    cols = st.columns([1.2, 1, 1, 1.2, 0.8])
    for col, (k, name) in zip(cols[:3], DIMS.items()):
        opts = ["*"] + [o["code"] for o in S["filters"].get(k, [])]
        labels = {"*": "All", **{o["code"]: o["label"] for o in S["filters"].get(k, [])}}
        col.selectbox(name.upper(), opts, format_func=labels.get, key=f"f_{k}")
    fixed = {k for k in DIMS if st.session_state[f"f_{k}"] != "*"}
    compare_opts = ["all"] + [k for k in DIMS if k not in fixed]
    if st.session_state["compare"] not in compare_opts:
        st.session_state["compare"] = "all"
    cols[3].selectbox("COMPARE RESULTS BY", compare_opts,
                      format_func=lambda k: "No comparison" if k == "all" else DIMS[k], key="compare")
    cols[4].markdown("<div style='height:1.7rem'></div>", unsafe_allow_html=True)
    cols[4].button("Reset filters", on_click=reset_filters, use_container_width=True, type="primary")

vkey = "|".join(st.session_state[f"f_{k}"] for k in DIMS)
n_sel = S["view_n"].get(vkey, 0)
V = S["views"].get(vkey)
dim = st.session_state["compare"]
dim_name = "Overall" if dim == "all" else DIMS[dim]

sel_parts = [next(o["label"] for o in S["filters"][k] if o["code"] == st.session_state[f"f_{k}"])
             for k in DIMS if st.session_state[f"f_{k}"] != "*"]
sel_txt = ", ".join(sel_parts) if sel_parts else "all graduates"

if V is None:
    st.warning(f"Only {n_sel} graduate(s) match **{sel_txt}**. To protect privacy, results are shown only when at "
               f"least {MIN_GROUP} graduates match. Please widen the filters.")
    st.stop()


# ---------------------------------------------------------------- helpers
def pct(v, n):
    return None if v is None or not n else 100 * v / n


def fmt(v, n):
    return f"<{MIN_CELL}" if v is None else f"{pct(v, n):.0f}%"


def layout(fig, height):
    fig.update_layout(
        height=height, margin=dict(l=8, r=24, t=8, b=8), plot_bgcolor="white", paper_bgcolor="white",
        font=dict(color=INK, size=13), hoverlabel=dict(bgcolor="white", font_color=INK),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(color=INK2), traceorder="normal"),
        bargap=0.35,
    )
    fig.update_xaxes(gridcolor=GRID, zeroline=False, ticksuffix="%", color=INK2)
    fig.update_yaxes(color=INK, automargin=True)
    return fig


def option_rows(meta, block):
    rows = [{"label": o["label"], "count": block["counts"].get(o["code"]),
             "pct": pct(block["counts"].get(o["code"]), block["n"])} for o in meta["options"]]
    if meta["multi"]:
        rows = [r for r in rows if r["count"] != 0]
        rows.sort(key=lambda r: -1 if r["count"] is None else r["count"], reverse=True)
    return rows


def chart_overall(meta, ind):
    block = ind["all"]
    rows = option_rows(meta, block)
    labels = [r["label"] for r in rows][::-1]
    vals = [r["pct"] or 0 for r in rows][::-1]
    text = [fmt(r["count"], block["n"]) for r in rows][::-1]
    fig = go.Figure(go.Bar(x=vals, y=labels, orientation="h", marker=dict(color=BAR, cornerradius=4),
                           text=text, textposition="outside", cliponaxis=False, textfont=dict(color=INK2),
                           hovertemplate="%{y}<br>%{text}<extra></extra>"))
    fig.update_xaxes(range=[0, max(vals + [10]) * 1.2])
    st.plotly_chart(layout(fig, 50 + 34 * len(rows)), use_container_width=True, config={"displayModeBar": False})
    with st.expander("Show as table"):
        st.dataframe(pd.DataFrame({"Answer": [r["label"] for r in rows],
                                   "Graduates": [f"<{MIN_CELL}" if r["count"] is None else r["count"] for r in rows],
                                   "Share": [fmt(r["count"], block["n"]) for r in rows]}),
                     hide_index=True, use_container_width=True)


def group_label(g):
    return f"{g['label']} (n={g['n']})"


def table_breakdown(meta, groups):
    data = {"Answer": [o["label"] for o in meta["options"]]}
    for g in groups:
        data[group_label(g)] = [fmt(g["counts"].get(o["code"]), g["n"]) if g["n"] >= MIN_GROUP else "–"
                                for o in meta["options"]]
    df = pd.DataFrame(data)
    if meta["multi"]:
        df = df[~(df.iloc[:, 1:].isin(["0%", "–"])).all(axis=1)]
    st.dataframe(df, hide_index=True, use_container_width=True)


def chart_breakdown(meta, ind, d):
    groups = ind["by"].get(d, [])
    if not groups:
        st.info("No responses to compare yet.")
        return
    if meta["multi"] or len(meta["options"]) > len(CATEGORICAL):
        table_breakdown(meta, groups)
        return
    fig = go.Figure()
    ylab = [group_label(g) for g in groups][::-1]
    for i, o in enumerate(meta["options"]):
        vals = [pct(g["counts"].get(o["code"]), g["n"]) or 0 for g in groups][::-1]
        txt = [fmt(g["counts"].get(o["code"]), g["n"]) for g in groups][::-1]
        fig.add_trace(go.Bar(x=vals, y=ylab, orientation="h", name=o["label"],
                             marker=dict(color=CATEGORICAL[i], line=dict(color="white", width=2)),
                             text=[t if v >= 8 else "" for t, v in zip(txt, vals)], textposition="inside",
                             insidetextanchor="middle", customdata=txt,
                             hovertemplate="%{y}<br>" + o["label"] + ": %{customdata}<extra></extra>"))
    hidden = [100 * (g["n"] - sum(v for v in g["counts"].values() if v is not None)) / g["n"] if g["n"] else 0
              for g in groups][::-1]
    if any(h > 0.01 for h in hidden):
        fig.add_trace(go.Bar(x=hidden, y=ylab, orientation="h", name="Not shown (small numbers)",
                             marker=dict(color=HIDDEN_GREY, line=dict(color="white", width=2)),
                             hovertemplate="%{y}<br>Not shown to protect privacy<extra></extra>"))
    fig.update_layout(barmode="stack")
    fig.update_xaxes(range=[0, 100])
    st.plotly_chart(layout(fig, 110 + 46 * len(groups)), use_container_width=True, config={"displayModeBar": False})
    with st.expander("Show as table"):
        table_breakdown(meta, groups)


CARD_N = [0]


def card(key, d=None):
    meta, ind = META.get(key), V.get(key)
    if not meta or ind is None:
        return
    d = d or dim
    CARD_N[0] += 1
    with st.container(border=True, key=f"card_{key}_{CARD_N[0]}"):
        st.markdown(f"<div class='ep-card-title'>{meta['title']}</div>", unsafe_allow_html=True)
        if ind.get("too_few"):
            st.markdown(f"<div class='ep-card-sub'>{meta['base']}</div>", unsafe_allow_html=True)
            st.info(f"Fewer than {MIN_GROUP} graduates answered this for the current selection.")
            return
        sub = f"{meta['base']} · n = {ind['all']['n']}"
        if meta["multi"]:
            sub += " · more than one answer allowed, so totals can exceed 100%"
        if d != "all":
            sub += f" · each bar = 100% of that {DIMS.get(d, d).lower()}"
        st.markdown(f"<div class='ep-card-sub'>{sub}</div>", unsafe_allow_html=True)
        if d == "all":
            chart_overall(meta, ind)
        else:
            chart_breakdown(meta, ind, d)


def section(title):
    st.markdown(f"<div class='ep-section'>{title}</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------- KPI cards
pw = V["pathway"]["all"]
n, c = pw["n"], pw["counts"]


def share(*codes):
    vals = [c.get(k) for k in codes]
    return ("—", "hidden (small numbers)") if any(v is None for v in vals) else \
        (f"{100 * sum(vals) / n:.0f}%", f"{sum(vals)} of {n} graduates")


earn_c = V["is_earning"]["all"]["counts"].get("1") if not V["is_earning"].get("too_few") else None
earn = ("—", "hidden (small numbers)") if earn_c is None else (f"{100 * earn_c / n:.0f}%", f"{earn_c} of {n} graduates")
kpis = [
    ("Graduates assessed", f"{n:,}", f"Showing {sel_txt}", NAVY),
    ("Working in their trade", *share("own_business", "employed"), TEAL),
    ("Earning from their trade", *earn, GREEN),
    ("Still in apprenticeship", *share("apprentice"), WHEAT),
    ("Not working", *share("not_working"), BROWN),
]
st.markdown("<div class='ep-kpis'>" + "".join(
    f"<div class='ep-kpi' style='border-bottom:4px solid {col}'><div class='lbl'>{lbl}</div>"
    f"<div class='val'>{val}</div><div class='sub'>{sub}</div></div>" for lbl, val, sub, col in kpis) + "</div>",
    unsafe_allow_html=True)
st.caption("Working in their trade = own business or paid work in the trained vocation (Paths A and B). "
           "Earning from their trade also counts graduates who work mainly in another field but still earn from the trade.")

# ---------------------------------------------------------------- tabs
tabs = st.tabs(["Pathways", "Income", "Barriers", "Toolkit & support", "Outlook", "About the data"])

with tabs[0]:
    section("The five employability pathways")
    card("pathway")
    if dim == "all":
        with st.expander("Pathway by vocation (vocations with at least 5 graduates)"):
            chart_breakdown(META["pathway"], V["pathway"], "vocation")
    section("Work and business details")
    l, r = st.columns(2)
    with l:
        card("workplace")
        card("repeat_customers")
        card("appr_place")
    with r:
        card("find_customers")
        card("appr_allowance")
        card("past_work")

with tabs[1]:
    section("Income from the trained vocation")
    card("is_earning")
    l, r = st.columns(2)
    with l:
        card("earning_freq")
        card("monthly_income")
        card("trade_income")
    with r:
        card("time_to_income")
        card("income_change")
        card("income_use")

with tabs[2]:
    section("Barriers to working in the trade")
    card("reason_not_in_trade")
    card("market_challenges")
    card("toolkit_reason")

with tabs[3]:
    section("Toolkit and follow-up support")
    l, r = st.columns(2)
    with l:
        card("toolkit_use")
        card("post_support")
    with r:
        card("toolkit_how")
        card("post_support_type")
    card("support_needed")

with tabs[4]:
    section("Plans and perceived benefit")
    card("plans_3_6m")
    l, r = st.columns(2)
    with l:
        card("continue_trade")
    with r:
        card("vt_benefit")
    card("monitor_assessment")

with tabs[5]:
    section("About this assessment")
    with st.container(border=True, key="card_about"):
        st.markdown(f"""
**What it is.** ADWSO staff interviewed vocational training graduates in person or by phone using a KoBoToolbox
questionnaire in English and Dari. Graduates under 18 took part only with the consent of a parent or guardian,
as well as their own agreement.

**The five pathways.** A. Own business (self-employed, business group or partnership) · B. Paid employment
(including paid work with the Master Trainer) · C. Apprenticeship (still learning, without regular pay) ·
D. Working in another field · E. Not working.

**Graduates included:** {S['n_used']:,} who gave consent. Submissions marked "Not approved" during ADWSO's
quality review are excluded.

**Privacy.** This dashboard shows totals only. It never contains names, phone numbers, locations below province
level, photos or individual answers. Any figure based on fewer than {MIN_CELL} graduates is shown as
"<{MIN_CELL}". For any group of fewer than {MIN_GROUP} graduates – for example a province with only a few
interviews – only the number of graduates is shown, not their answers. A filter selection is shown only when at
least {MIN_GROUP} graduates match.
""")
    card("method", "all")

st.markdown(f"<div class='ep-footer'>ADWSO · Employability Pathway Dashboard · Prepared by {CREDIT_NAME}, "
            f"{CREDIT_ROLE}</div>", unsafe_allow_html=True)
