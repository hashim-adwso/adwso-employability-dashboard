"""
PUBLIC Streamlit dashboard – Employability Pathway of ADWSO vocational training graduates.

Data source (in this order):
1. LIVE: if the Streamlit secret KOBO_TOKEN is set, the app downloads the submissions from KoBo,
   aggregates them IN MEMORY with aggregate.build_summary() (same privacy rules) and keeps only the
   totals. Refreshed automatically every 30 minutes, or by the "Refresh data" button.
2. SNAPSHOT: otherwise (or if KoBo cannot be reached) it reads data/summary.json, which the GitHub
   Action refreshes on a schedule.
Individual records are never shown, stored or sent to the browser.
"""
import base64
import datetime as dt
import json
import sys
import time
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
import aggregate  # noqa: E402

st.set_page_config(page_title="Employability Pathway – ADWSO", page_icon="📊", layout="wide",
                   initial_sidebar_state="collapsed")

SUMMARY = ROOT / "data" / "summary.json"
LOGO = ROOT / "assets" / "adwso_logo.png"
LIVE_TTL = 30 * 60        # automatic refresh interval (seconds)
REFRESH_COOLDOWN = 60     # minimum seconds between two manual refreshes (protects KoBo)
KABUL = dt.timezone(dt.timedelta(hours=4, minutes=30))

# Chart colours: validated categorical palette. Brand colours are used only for page chrome.
BAR = "#2a78d6"
CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
HIDDEN_GREY = "#c9c8c3"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e6e5e1"
NAVY, TEAL, GREEN, BROWN, WHEAT = "#2e3a87", "#2a8fa8", "#1f8a4c", "#9c5a44", "#e3a72f"

# Fixed colours so a pathway / earning status looks the same in every chart.
PATH_COLORS = {"own_business": "#2a78d6", "employed": "#1baf7a", "apprentice": "#eda100",
               "other_field": "#4a3aa7", "not_working": "#e34948"}
EARN_COLORS = {"regular": "#1f8a4c", "occasional": "#8fd1ac", "none": "#e34948"}
OPTION_COLORS = {"pathway": PATH_COLORS, "earning_status": EARN_COLORS}

PATHS = [  # code, letter, short name, plain-language meaning
    ("own_business", "A", "Own business", "Runs their own work in the trade – alone, in a group or in a partnership."),
    ("employed", "B", "Paid job", "Works for someone else in the trade for pay, including paid work with the Master Trainer."),
    ("apprentice", "C", "Apprenticeship", "Still learning on the job with a master, usually without regular pay."),
    ("other_field", "D", "Another field", "Main work is in a different field from the one they were trained in."),
    ("not_working", "E", "Not working", "Has no work at the moment."),
]

CREDIT_NAME = "Hashim Ali Shah"
CREDIT_ROLE = "Program Associate – Grants and Strategic Partnerships"

# Plain-language explanation shown under each chart title.
EXPLAIN = {
    "pathway": "Every graduate is placed in one of five pathways according to their main activity today.",
    "earning_status": "How often each graduate earns money from the skill they were trained in. Everyone in Paths A "
                      "and B earns from the trade; Path D graduates are counted if they still earn from it on the side.",
    "earning_freq": "Among graduates who earn from their trade: is the income steady (every week or month) or only now and then?",
    "trade_income": "Graduates whose main work is in another field: do they still earn something from the trained vocation?",
    "monthly_income": "Approximate monthly income from the trade, among graduates who earn from it.",
    "time_to_income": "How long after finishing the training graduates first earned money from the trade.",
    "income_change": "Whether the graduate's personal or family income has changed since the training.",
    "income_use": "What graduates mostly spend their trade income on.",
    "workplace": "Where graduates with their own business or a paid job mostly work.",
    "find_customers": "How graduates who run their own business get customers.",
    "repeat_customers": "Whether customers come back – a sign that the business can last.",
    "appr_place": "Where apprentices are learning.",
    "appr_allowance": "Whether apprentices receive any money while they learn.",
    "past_work": "Graduates not working today: have they worked or earned at any time since the training?",
    "reason_not_in_trade": "Why graduates in another field or without work are not working in their trained vocation.",
    "market_challenges": "The main difficulties in finding customers, work or markets.",
    "toolkit_reason": "Why some graduates use their toolkit only sometimes, rarely or not at all.",
    "toolkit_use": "How often graduates use the toolkit they received at the end of the training.",
    "toolkit_how": "What graduates use the toolkit for.",
    "post_support": "Whether graduates received any help after the training ended.",
    "post_support_type": "The kind of help received after the training.",
    "support_needed": "What graduates say would help them most now.",
    "plans_3_6m": "The graduate's main plan for the next 3 to 6 months.",
    "continue_trade": "Whether the graduate expects to keep working in the trained vocation next year.",
    "vt_benefit": "The graduate's own view of how much the training has helped their livelihood.",
    "monitor_assessment": "The interviewer's own judgement of the graduate's employability (not read to the graduate).",
    "method": "Whether the interview was done in person or by phone.",
}

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
  .ep-status {{font-size:.85rem; color:{INK2}; line-height:1.5;}}
  .ep-status b {{color:{INK};}}
  .ep-dot {{display:inline-block; width:9px; height:9px; border-radius:50%; margin-right:6px; vertical-align:middle;}}
  .ep-kpis {{display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); gap:14px; margin:6px 0 4px 0;}}
  .ep-kpi {{background:#fff; border-radius:14px; padding:14px 16px 12px 16px; border:1px solid #e1e6ee;
            box-shadow:0 1px 4px rgba(20,40,80,.06);}}
  .ep-kpi .lbl {{font-size:.82rem; color:{INK}; font-weight:700;}}
  .ep-kpi .val {{font-size:2rem; font-weight:700; color:{INK}; line-height:1.15; margin-top:4px;}}
  .ep-kpi .sub {{font-size:.75rem; color:{INK2}; margin-top:2px;}}
  .ep-kpi .what {{font-size:.76rem; color:{INK2}; margin-top:8px; padding-top:8px; border-top:1px dashed #dde3ec; line-height:1.35;}}
  .ep-paths {{display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:12px; margin:4px 0;}}
  .ep-path {{background:#fff; border:1px solid #e1e6ee; border-radius:14px; padding:12px 14px; border-left:6px solid;}}
  .ep-path .h {{font-size:.8rem; font-weight:700; color:{INK2}; text-transform:uppercase; letter-spacing:.04em;}}
  .ep-path .v {{font-size:1.7rem; font-weight:700; color:{INK}; line-height:1.2;}}
  .ep-path .v small {{font-size:.8rem; color:{INK2}; font-weight:500;}}
  .ep-path .d {{font-size:.78rem; color:{INK2}; line-height:1.35; margin-top:4px;}}
  .ep-strip {{display:flex; height:30px; border-radius:8px; overflow:hidden; margin:6px 0 4px 0;}}
  .ep-strip div {{display:flex; align-items:center; justify-content:center; color:#fff; font-size:.78rem; font-weight:700;}}
  .ep-find li {{margin-bottom:6px; color:{INK}; font-size:.92rem;}}
  .ep-section {{color:{NAVY}; font-weight:700; font-size:.82rem; letter-spacing:.06em; text-transform:uppercase;
                border-bottom:2px solid #9cc7e6; padding-bottom:6px; margin:18px 0 10px 0;}}
  .ep-card-title {{color:{NAVY} !important; font-weight:700; font-size:1rem !important; margin:0 !important;}}
  .ep-card-what {{color:{INK} !important; font-size:.85rem !important; margin:3px 0 2px 0 !important; line-height:1.4;}}
  .ep-card-sub {{color:{INK2} !important; font-size:.76rem !important; margin:2px 0 4px 0 !important; line-height:1.35;}}
  .stTabs [data-baseweb="tab-list"] {{gap:4px; flex-wrap:wrap;}}
  .stTabs [data-baseweb="tab"] {{background:#fff; border-radius:10px 10px 0 0; padding:8px 16px;}}
  .ep-footer {{color:{INK2}; font-size:.78rem; text-align:center; margin-top:28px;}}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------- data
def kobo_token():
    try:
        return st.secrets.get("KOBO_TOKEN") or None
    except Exception:  # no secrets file (e.g. local run)
        return None


@st.cache_data(ttl=LIVE_TTL, show_spinner="Fetching the latest interviews from KoBo…")
def live_summary(_token):
    asset, raw = aggregate.fetch(_token)
    summary = aggregate.build_summary(asset, raw)
    del raw  # individual records are dropped; only the totals are cached
    return summary


@st.cache_data
def file_summary(mtime):
    # mtime is part of the cache key, so a new snapshot file is picked up immediately
    return json.loads(SUMMARY.read_text(encoding="utf-8"))


@st.cache_resource
def refresh_state():
    return {"last": 0.0}


@st.cache_data
def logo_b64():
    return base64.b64encode(LOGO.read_bytes()).decode() if LOGO.exists() else ""


def do_refresh():
    state = refresh_state()
    wait = REFRESH_COOLDOWN - (time.time() - state["last"])
    if wait > 0:
        st.session_state["refresh_msg"] = f"The data was refreshed less than a minute ago. Please try again in {wait:.0f} seconds."
        return
    state["last"] = time.time()
    live_summary.clear()
    st.session_state["refresh_msg"] = "Data refreshed from KoBo."


TOKEN = kobo_token()
S, SOURCE, LIVE_ERROR = None, "snapshot", None
if TOKEN:
    try:
        S, SOURCE = live_summary(TOKEN), "live"
    except Exception as e:  # KoBo unreachable or too few records – fall back to the snapshot
        LIVE_ERROR = type(e).__name__
if S is None:
    if not SUMMARY.exists():
        st.title("Employability Pathway")
        st.info("Results will appear here after the first data refresh.")
        st.stop()
    S = file_summary(SUMMARY.stat().st_mtime)

META = S["meta"]
MIN_CELL, MIN_GROUP = S["rules"]["min_cell"], S["rules"]["min_group"]
DIMS = {"province": "Province", "gender": "Gender", "age_group": "Age group"}


def kabul_time(summary):
    iso = summary.get("generated_iso")
    try:
        t = dt.datetime.fromisoformat(iso) if iso else \
            dt.datetime.strptime(summary["generated"], "%Y-%m-%d %H:%M UTC").replace(tzinfo=dt.timezone.utc)
        return t.astimezone(KABUL).strftime("%d %b %Y, %H:%M") + " Kabul time"
    except Exception:
        return summary.get("generated", "")


def nice_day(s):
    try:
        return dt.date.fromisoformat(s).strftime("%d %b %Y")
    except Exception:
        return s


period = S.get("period") or ["", ""]
period_txt = nice_day(period[0]) if period[0] == period[1] else f"{nice_day(period[0])} – {nice_day(period[1])}"
UPDATED = kabul_time(S)

# ---------------------------------------------------------------- banner
st.markdown(f"""
<div class="ep-banner">
  <div class="ep-logo"><img src="data:image/png;base64,{logo_b64()}" alt="ADWSO logo"></div>
  <div class="ep-title">
    <h1>Employability Pathway — VT Graduates Dashboard</h1>
    <p>Where are our vocational training graduates now, and are they earning from their trade?<br>
    Post-Vocational Training Assessment 2026 · Afghanistan Development &amp; Welfare Services Organization (ADWSO)</p>
  </div>
  <div class="ep-pills">
    <div class="ep-pill">Prepared by <b>{CREDIT_NAME}</b> · {CREDIT_ROLE}</div>
    <div class="ep-pill">Interviews: {period_txt}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------- data status + refresh
with st.container(border=True, key="card_status"):
    l, r = st.columns([5, 1.1], vertical_alignment="center")
    n_kobo = S.get("n_kobo")
    n_out = (n_kobo - S["n_used"]) if n_kobo is not None else None
    counts_txt = (f"<b>{n_kobo:,}</b> interviews in KoBo · <b>{S['n_used']:,}</b> included"
                  + (f" · {n_out} excluded (no consent or marked “Not approved”)" if n_out else "")
                  ) if n_kobo is not None else f"<b>{S['n_used']:,}</b> interviews included"
    if SOURCE == "live":
        dot, how = GREEN, f"Live from KoBo · updates automatically every {LIVE_TTL // 60} minutes"
    else:
        dot, how = WHEAT, "Daily snapshot" + (" · live connection to KoBo is not available right now" if LIVE_ERROR else "")
    l.markdown(f"<div class='ep-status'><span class='ep-dot' style='background:{dot}'></span>"
               f"Data last fetched: <b>{UPDATED}</b> · {how}<br>{counts_txt}</div>", unsafe_allow_html=True)
    r.button("↻ Refresh data", on_click=do_refresh, width="stretch", disabled=not TOKEN,
             help="Fetch the latest interviews from KoBo now." if TOKEN else
             "Live refresh is not set up yet (KOBO_TOKEN secret missing in Streamlit).")
    msg = st.session_state.pop("refresh_msg", None)
    if msg:
        st.toast(msg)


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
        if st.session_state[f"f_{k}"] not in opts:  # a filter value can disappear after a refresh
            st.session_state[f"f_{k}"] = "*"
        col.selectbox(name.upper(), opts, format_func=labels.get, key=f"f_{k}")
    fixed = {k for k in DIMS if st.session_state[f"f_{k}"] != "*"}
    compare_opts = ["all"] + [k for k in DIMS if k not in fixed]
    if st.session_state["compare"] not in compare_opts:
        st.session_state["compare"] = "all"
    cols[3].selectbox("COMPARE RESULTS BY", compare_opts,
                      format_func=lambda k: "No comparison" if k == "all" else DIMS[k], key="compare",
                      help="Split every chart by province, gender or age group.")
    cols[4].markdown("<div style='height:1.7rem'></div>", unsafe_allow_html=True)
    cols[4].button("Reset filters", on_click=reset_filters, width="stretch", type="primary")

with st.expander("How to read this dashboard"):
    st.markdown(f"""
- **Percentages** are shares of the graduates described under each chart title (for example *all graduates*, or
  *graduates who earn from their trade*). The number of graduates behind each chart is shown as **n**.
- **The five pathways** – every graduate is placed in one:
  **A. Own business** · **B. Paid job** in the trade · **C. Apprenticeship** (still learning) ·
  **D. Another field** (main work is not the trained vocation) · **E. Not working**.
- **Earning from their trade** counts everyone who earns money from the skill they were trained in, regularly or
  occasionally. All graduates in Paths A and B earn from the trade, so this figure is close to the share in Paths A + B;
  it is higher only when some Path D graduates also earn from the trade on the side.
- **Earning regularly** means every week or every month – a sign of a stable livelihood.
- **Questions with several answers** (marked *more than one answer allowed*) can add up to more than 100%.
- **Privacy:** “<{MIN_CELL}” means fewer than {MIN_CELL} graduates; grey “Not shown” bars hide small numbers. A group of
  fewer than {MIN_GROUP} graduates shows only its size, never its answers.
- **Compare results by** splits each chart by province, gender or age group; each bar is then 100% of that group.
""")

vkey = "|".join(st.session_state[f"f_{k}"] for k in DIMS)
n_sel = S["view_n"].get(vkey, 0)
V = S["views"].get(vkey)
dim = st.session_state["compare"]

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
    rows = [{"code": o["code"], "label": o["label"], "count": block["counts"].get(o["code"]),
             "pct": pct(block["counts"].get(o["code"]), block["n"])} for o in meta["options"]]
    if meta["multi"]:
        rows = [r for r in rows if r["count"] != 0]
        rows.sort(key=lambda r: -1 if r["count"] is None else r["count"], reverse=True)
    return rows


def chart_overall(key, meta, ind):
    block = ind["all"]
    rows = option_rows(meta, block)
    colors = OPTION_COLORS.get(key, {})
    labels = [r["label"] for r in rows][::-1]
    vals = [r["pct"] or 0 for r in rows][::-1]
    text = [fmt(r["count"], block["n"]) for r in rows][::-1]
    bar_colors = [colors.get(r["code"], BAR) for r in rows][::-1]
    fig = go.Figure(go.Bar(x=vals, y=labels, orientation="h", marker=dict(color=bar_colors, cornerradius=4),
                           text=text, textposition="outside", cliponaxis=False, textfont=dict(color=INK2),
                           hovertemplate="%{y}<br>%{text}<extra></extra>"))
    fig.update_xaxes(range=[0, max(vals + [10]) * 1.2])
    st.plotly_chart(layout(fig, 50 + 34 * len(rows)), width="stretch", config={"displayModeBar": False},
                    key=f"chart_{CARD_N[0]}_{key}")
    with st.expander("Show as table"):
        st.dataframe(pd.DataFrame({"Answer": [r["label"] for r in rows],
                                   "Graduates": [f"<{MIN_CELL}" if r["count"] is None else str(r["count"]) for r in rows],
                                   "Share": [fmt(r["count"], block["n"]) for r in rows]}),
                     hide_index=True, width="stretch")


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
    st.dataframe(df, hide_index=True, width="stretch")


def chart_breakdown(key, meta, ind, d):
    groups = ind["by"].get(d, [])
    if not groups:
        st.info("No responses to compare yet.")
        return
    if meta["multi"] or len(meta["options"]) > len(CATEGORICAL):
        table_breakdown(meta, groups)
        return
    colors = OPTION_COLORS.get(key, {})
    fig = go.Figure()
    ylab = [group_label(g) for g in groups][::-1]
    for i, o in enumerate(meta["options"]):
        vals = [pct(g["counts"].get(o["code"]), g["n"]) or 0 for g in groups][::-1]
        txt = [fmt(g["counts"].get(o["code"]), g["n"]) for g in groups][::-1]
        fig.add_trace(go.Bar(x=vals, y=ylab, orientation="h", name=o["label"],
                             marker=dict(color=colors.get(o["code"], CATEGORICAL[i]), line=dict(color="white", width=2)),
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
    st.plotly_chart(layout(fig, 110 + 46 * len(groups)), width="stretch", config={"displayModeBar": False},
                    key=f"chart_{CARD_N[0]}_{key}_{d}")
    with st.expander("Show as table"):
        table_breakdown(meta, groups)


CARD_N = [0]


def card(key, d=None, title=None, explain=None):
    meta, ind = META.get(key), V.get(key)
    if not meta or ind is None:
        return
    d = d or dim
    CARD_N[0] += 1
    with st.container(border=True, key=f"card_{key}_{CARD_N[0]}"):
        st.markdown(f"<div class='ep-card-title'>{title or meta['title']}</div>", unsafe_allow_html=True)
        what = explain or EXPLAIN.get(key)
        if what:
            st.markdown(f"<div class='ep-card-what'>{what}</div>", unsafe_allow_html=True)
        if ind.get("too_few"):
            st.markdown(f"<div class='ep-card-sub'>Base: {meta['base']}</div>", unsafe_allow_html=True)
            st.info(f"Fewer than {MIN_GROUP} graduates answered this for the current selection.")
            return
        sub = f"Base: {meta['base']} · n = {ind['all']['n']}"
        if meta["multi"]:
            sub += " · more than one answer allowed, so totals can exceed 100%"
        if d != "all":
            sub += f" · each bar = 100% of that {(DIMS.get(d) or d).lower()}"
        st.markdown(f"<div class='ep-card-sub'>{sub}</div>", unsafe_allow_html=True)
        if d == "all":
            chart_overall(key, meta, ind)
        else:
            chart_breakdown(key, meta, ind, d)


def section(title):
    st.markdown(f"<div class='ep-section'>{title}</div>", unsafe_allow_html=True)


def counts_of(key):
    ind = V.get(key)
    if not ind or ind.get("too_few"):
        return None, None
    return ind["all"]["counts"], ind["all"]["n"]


def share_of(key, *codes):
    """(percent text, 'x of n' text) or ('—', reason) when hidden or too few."""
    c, n = counts_of(key)
    if c is None:
        return "—", f"fewer than {MIN_GROUP} answered"
    vals = [c.get(k) for k in codes]
    if any(v is None for v in vals):
        return "—", "hidden (small numbers)"
    return f"{100 * sum(vals) / n:.0f}%", f"{sum(vals)} of {n} graduates"


TEN_PHRASES = {"own_business": ("runs their own business", "run their own business"),
               "employed": ("has a paid job", "have a paid job"),
               "apprentice": ("is an apprentice", "are apprentices"),
               "other_field": ("works in another field", "work in another field"),
               "not_working": ("is not working", "are not working")}


def out_of_ten(parts):
    """parts: [(code, share of 10)] -> phrases whose whole numbers add up to exactly 10 (largest remainder)."""
    base = {c: int(t) for c, t in parts}
    left = 10 - sum(base.values())
    for c, t in sorted(parts, key=lambda x: x[1] - int(x[1]), reverse=True)[:max(left, 0)]:
        base[c] += 1
    order = sorted((v, c) for c, v in base.items() if v > 0)[::-1]
    return [f"<b>{v}</b> {TEN_PHRASES[c][0 if v == 1 else 1]}" for v, c in order]


def chart_rate(key, codes, d, label):
    """One bar per group: share answering any of `codes` (e.g. earning from the trade), sorted high to low."""
    ind = V.get(key)
    groups = ind["by"].get(d, []) if ind and not ind.get("too_few") else []
    if not groups:
        st.info("No responses to compare yet.")
        return
    rows = []
    for g in groups:
        vals = [g["counts"].get(c) for c in codes]
        if g["n"] < MIN_GROUP or any(v is None for v in vals):
            rows.append((g, None))
        else:
            rows.append((g, 100 * sum(vals) / g["n"]))
    rows.sort(key=lambda x: -1 if x[1] is None else x[1])
    ylab = [group_label(g) for g, _ in rows]
    fig = go.Figure(go.Bar(
        x=[v if v is not None else 100 for _, v in rows], y=ylab, orientation="h",
        marker=dict(color=[TEAL if v is not None else "#e9e8e4" for _, v in rows], cornerradius=4),
        text=[f"{v:.0f}%" if v is not None else
              ("Too few graduates to show" if g["n"] < MIN_GROUP else "Not shown (small numbers)") for g, v in rows],
        textposition=["outside" if v is not None else "inside" for _, v in rows], insidetextanchor="middle",
        textfont=dict(color=INK2), cliponaxis=False,
        hovertemplate="%{y}<br>" + label + ": %{text}<extra></extra>"))
    fig.update_xaxes(range=[0, 110])
    st.plotly_chart(layout(fig, 60 + 34 * len(rows)), width="stretch", config={"displayModeBar": False},
                    key=f"rate_{key}_{d}_{CARD_N[0]}")


def top_option(key):
    """Most common answer that is shown (not hidden): (label, percent) or None."""
    c, n = counts_of(key)
    if c is None:
        return None
    best = max(((v, code) for code, v in c.items() if v), default=None)
    if not best:
        return None
    label = next(o["label"] for o in META[key]["options"] if o["code"] == best[1])
    return label, 100 * best[0] / n


# ================================================================ TABS
tabs = st.tabs(["At a glance", "Pathways & work", "Income", "Barriers", "Toolkit & support", "Outlook",
                "About the data"])

# ---------------------------------------------------------------- at a glance
with tabs[0]:
    pw_c, n = counts_of("pathway")
    section(f"Key figures · {sel_txt} · {n:,} graduates")
    kpis = [
        ("Graduates assessed", f"{n:,}", f"Showing {sel_txt}",
         "Interviews with consent that are included in this dashboard.", NAVY),
        ("Earning from their trade", *share_of("earning_status", "regular", "occasional"),
         "Earn money – regularly or now and then – from the skill they were trained in.", TEAL),
        ("Earning regularly", *share_of("earning_status", "regular"),
         "Earn from the trade every week or every month: a steady livelihood.", GREEN),
        ("Say the training helped", *share_of("vt_benefit", "very", "beneficial"),
         "Rate the training “very beneficial” or “beneficial” for their livelihood.", WHEAT),
        ("Plan to stay in the trade", *share_of("continue_trade", "def_yes", "prob_yes"),
         "Will definitely or probably keep working in the trained vocation next year.", BROWN),
    ]
    st.markdown("<div class='ep-kpis'>" + "".join(
        f"<div class='ep-kpi' style='border-bottom:4px solid {col}'><div class='lbl'>{lbl}</div>"
        f"<div class='val'>{val}</div><div class='sub'>{sub}</div><div class='what'>{what}</div></div>"
        for lbl, val, sub, what, col in kpis) + "</div>", unsafe_allow_html=True)

    section("Where are the graduates now? The five pathways")
    with st.container(border=True, key="card_paths"):
        strip, tiles, tenths = [], [], []
        hidden_total = n
        for code, letter, name, desc in PATHS:
            v = pw_c.get(code)
            col = PATH_COLORS[code]
            if v is None:
                val_html = f"&lt;{MIN_CELL}<small> graduates</small>"
            else:
                hidden_total -= v
                p = 100 * v / n
                val_html = f"{p:.0f}%<small> · {v} graduates</small>"
                if v:
                    strip.append(f"<div style='width:{p}%;background:{col}' title='{letter}. {name}: {p:.0f}%'>"
                                 f"{letter if p >= 4 else ''}</div>")
                    tenths.append((code, v * 10 / n))
            tiles.append(f"<div class='ep-path' style='border-left-color:{col}'><div class='h'>{letter} · {name}</div>"
                         f"<div class='v'>{val_html}</div><div class='d'>{desc}</div></div>")
        if hidden_total > 0:
            strip.append(f"<div style='width:{100 * hidden_total / n}%;background:{HIDDEN_GREY}' title='Not shown'></div>")
        phrases = out_of_ten(tenths) if hidden_total == 0 else []
        st.markdown("<div class='ep-card-what'>Every graduate is placed in one pathway according to their main "
                    "activity today. The bar shows how the graduates are split.</div>"
                    f"<div class='ep-strip'>{''.join(strip)}</div>"
                    + (f"<div class='ep-card-sub'>Out of every 10 graduates, about {'; '.join(phrases)}.</div>"
                       if phrases else "")
                    + f"<div class='ep-paths'>{''.join(tiles)}</div>", unsafe_allow_html=True)

    section("Key findings")
    with st.container(border=True, key="card_findings"):
        items = []
        top = top_option("pathway")
        if top:
            items.append(f"The most common pathway is <b>{top[0]}</b> ({top[1]:.0f}% of graduates).")
        e_any, e_any_sub = share_of("earning_status", "regular", "occasional")
        e_reg, _ = share_of("earning_status", "regular")
        if e_any != "—":
            items.append(f"<b>{e_any}</b> earn from their trade" + (f", and <b>{e_reg}</b> earn regularly" if e_reg != "—" else "")
                         + ".")
        inc = top_option("monthly_income")
        if inc:
            items.append(f"Among graduates who earn from the trade, the most common monthly income is <b>{inc[0]}</b> "
                         f"({inc[1]:.0f}%).")
        chg = share_of("income_change", "increased_sig", "increased_some")
        if chg[0] != "—":
            items.append(f"<b>{chg[0]}</b> of earners say their income has increased since the training.")
        rsn = top_option("reason_not_in_trade")
        if rsn:
            items.append(f"For graduates not working in their trade, the most common reason is <b>{rsn[0]}</b> "
                         f"({rsn[1]:.0f}%).")
        sup = top_option("support_needed")
        if sup:
            items.append(f"The support graduates most often ask for is <b>{sup[0]}</b> ({sup[1]:.0f}%).")
        tk = share_of("toolkit_use", "regularly")
        if tk[0] != "—":
            items.append(f"<b>{tk[0]}</b> use their toolkit regularly.")
        st.markdown("<ul class='ep-find'>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"
                    "<div class='ep-card-sub'>These sentences are written automatically from the current selection. "
                    "Figures hidden for privacy are left out.</div>", unsafe_allow_html=True)

    section("Comparisons")
    if dim != "all":
        card("pathway", title=f"Pathways by {DIMS[dim].lower()}")
        card("earning_status", title=f"Earning from the trade by {DIMS[dim].lower()}")
    else:
        CARD_N[0] += 1
        with st.container(border=True, key=f"card_trade_{CARD_N[0]}"):
            st.markdown("<div class='ep-card-title'>Which trades lead to income?</div>"
                        "<div class='ep-card-what'>Share of graduates of each trade who earn money from that trade, "
                        "regularly or occasionally.</div>"
                        f"<div class='ep-card-sub'>Trades with at least {MIN_CELL} graduates are listed; a trade needs "
                        f"at least {MIN_GROUP} graduates before its result is shown.</div>", unsafe_allow_html=True)
            chart_rate("is_earning", ["1"], "vocation", "Earning from the trade")
        st.caption("Tip: use **Compare results by** above to split these figures by province, gender or age group.")

# ---------------------------------------------------------------- pathways & work
with tabs[1]:
    section("The five employability pathways")
    card("pathway")
    section("Own business and paid work (Paths A and B)")
    l, r = st.columns(2)
    with l:
        card("workplace")
        card("repeat_customers")
    with r:
        card("find_customers")
    section("Apprentices (Path C) and graduates not working (Path E)")
    l, r = st.columns(2)
    with l:
        card("appr_place")
        card("appr_allowance")
    with r:
        card("past_work")

# ---------------------------------------------------------------- income
with tabs[2]:
    section("Earning from the trained vocation")
    card("earning_status")
    section("Graduates who earn from their trade")
    l, r = st.columns(2)
    with l:
        card("earning_freq")
        card("monthly_income")
        card("trade_income")
    with r:
        card("time_to_income")
        card("income_change")
        card("income_use")

# ---------------------------------------------------------------- barriers
with tabs[3]:
    section("What stops graduates from working in their trade")
    card("reason_not_in_trade")
    card("market_challenges")
    card("toolkit_reason")

# ---------------------------------------------------------------- support
with tabs[4]:
    section("Toolkit and follow-up support")
    l, r = st.columns(2)
    with l:
        card("toolkit_use")
        card("post_support")
    with r:
        card("toolkit_how")
        card("post_support_type")
    card("support_needed")

# ---------------------------------------------------------------- outlook
with tabs[5]:
    section("Plans and perceived benefit")
    card("plans_3_6m")
    l, r = st.columns(2)
    with l:
        card("continue_trade")
    with r:
        card("vt_benefit")
    card("monitor_assessment")

# ---------------------------------------------------------------- about
with tabs[6]:
    section("About this assessment")
    with st.container(border=True, key="card_about"):
        st.markdown(f"""
**What it is.** ADWSO staff interviewed vocational training graduates in person or by phone using a KoBoToolbox
questionnaire in English and Dari. Graduates under 18 took part only with the consent of a parent or guardian,
as well as their own agreement.

**The five pathways.** A. Own business (self-employed, business group or partnership) · B. Paid job
(including paid work with the Master Trainer) · C. Apprenticeship (still learning, without regular pay) ·
D. Another field · E. Not working.

**Which interviews are counted.** Interviews where consent was given. Interviews marked "Not approved" in ADWSO's
quality review are excluded. The total in KoBo can therefore be slightly higher than the number shown here.

**How up to date it is.** The dashboard reads the interviews directly from KoBo and updates itself every
{LIVE_TTL // 60} minutes; anyone can press **Refresh data** to fetch the latest interviews at once. A daily
snapshot is used as a back-up if KoBo cannot be reached.

**Privacy.** This dashboard shows totals only. It never contains names, phone numbers, locations below province
level, photos or individual answers. Any figure based on fewer than {MIN_CELL} graduates is shown as
"<{MIN_CELL}". For any group of fewer than {MIN_GROUP} graduates – for example a province with only a few
interviews – only the number of graduates is shown, not their answers. A filter selection is shown only when at
least {MIN_GROUP} graduates match.
""")
    card("method", "all")

st.markdown(f"<div class='ep-footer'>ADWSO · Employability Pathway Dashboard · Prepared by {CREDIT_NAME}, "
            f"{CREDIT_ROLE}</div>", unsafe_allow_html=True)
