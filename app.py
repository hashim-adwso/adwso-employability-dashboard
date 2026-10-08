"""
PUBLIC Streamlit dashboard – Employability Pathway of ADWSO vocational training graduates.

Reads ONLY data/summary.json (pre-aggregated, small cells suppressed).
It has no access to KoBo and never sees individual records.
"""
import json
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Employability Pathway – ADWSO", page_icon="📊", layout="wide")

SUMMARY = Path(__file__).parent / "data" / "summary.json"
BLUE = "#2a78d6"
CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#4a3aa7", "#e34948"]
HIDDEN_GREY = "#c9c8c3"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e6e5e1"


@st.cache_data(ttl=3600)
def load():
    return json.loads(SUMMARY.read_text(encoding="utf-8"))


if not SUMMARY.exists():
    st.title("Employability Pathway")
    st.info("Results will appear here after the first data refresh.")
    st.stop()
S = load()
IND = S["indicators"]
MIN_CELL = S["rules"]["min_cell"]


def pct(v, n):
    return None if v is None or not n else 100 * v / n


def fmt(v, n):
    return f"<{MIN_CELL}" if v is None else f"{pct(v, n):.0f}%"


def layout(fig, height):
    fig.update_layout(
        height=height, margin=dict(l=10, r=30, t=10, b=10), plot_bgcolor="white", paper_bgcolor="white",
        font=dict(color=INK, size=13), hoverlabel=dict(bgcolor="white", font_color=INK),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(color=INK2)),
        bargap=0.35,
    )
    fig.update_xaxes(gridcolor=GRID, zeroline=False, ticksuffix="%", color=INK2)
    fig.update_yaxes(color=INK, automargin=True)
    return fig


def option_rows(ind, block):
    rows = []
    for o in ind["options"]:
        v = block["counts"].get(o["code"])
        rows.append({"code": o["code"], "label": o["label"], "count": v, "pct": pct(v, block["n"])})
    rows = [r for r in rows if not (r["count"] == 0 and ind["multi"])]
    if ind["multi"]:
        rows.sort(key=lambda r: -1 if r["count"] is None else r["count"], reverse=True)
    return rows


def chart_overall(ind):
    block = ind["all"]
    rows = option_rows(ind, block)
    labels = [r["label"] for r in rows][::-1]
    vals = [r["pct"] or 0 for r in rows][::-1]
    text = [fmt(r["count"], block["n"]) for r in rows][::-1]
    fig = go.Figure(go.Bar(
        x=vals, y=labels, orientation="h", marker=dict(color=BLUE, cornerradius=4),
        text=text, textposition="outside", cliponaxis=False, textfont=dict(color=INK2),
        hovertemplate="%{y}<br>%{text}<extra></extra>",
    ))
    fig.update_xaxes(range=[0, max(vals + [10]) * 1.18])
    st.plotly_chart(layout(fig, 60 + 34 * len(rows)), use_container_width=True, config={"displayModeBar": False})
    note = "Respondents could choose more than one answer, so percentages can add up to more than 100%." if ind["multi"] else ""
    st.caption(f"Base: {ind['base']} (n = {block['n']}). {note}")
    with st.expander("Show as table"):
        st.dataframe(pd.DataFrame({"Answer": [r["label"] for r in rows],
                                   "Respondents": [f"<{MIN_CELL}" if r["count"] is None else r["count"] for r in rows],
                                   "Share": [fmt(r["count"], block["n"]) for r in rows]}),
                     hide_index=True, use_container_width=True)


def chart_breakdown(ind, dim, dim_name):
    groups = ind["by"].get(dim, [])
    if not groups:
        st.info("Not enough responses to show this breakdown safely.")
        return
    opts = ind["options"]
    if ind["multi"] or len(opts) > len(CATEGORICAL):
        table_breakdown(ind, groups, dim_name)
        return
    fig = go.Figure()
    ylabels = [f"{g['label']} (n={g['n']})" for g in groups][::-1]
    for i, o in enumerate(opts):
        vals = [pct(g["counts"].get(o["code"]), g["n"]) or 0 for g in groups][::-1]
        txt = [fmt(g["counts"].get(o["code"]), g["n"]) for g in groups][::-1]
        fig.add_trace(go.Bar(x=vals, y=ylabels, orientation="h", name=o["label"],
                             marker=dict(color=CATEGORICAL[i], line=dict(color="white", width=2)),
                             text=[t if v >= 8 else "" for t, v in zip(txt, vals)], textposition="inside",
                             insidetextanchor="middle", customdata=txt,
                             hovertemplate="%{y}<br>" + o["label"] + ": %{customdata}<extra></extra>"))
    hidden = []
    for g in groups[::-1]:
        shown = sum(v for v in g["counts"].values() if v is not None)
        hidden.append(100 * (g["n"] - shown) / g["n"] if g["n"] else 0)
    if any(h > 0.01 for h in hidden):
        fig.add_trace(go.Bar(x=hidden, y=ylabels, orientation="h", name=f"Not shown (fewer than {MIN_CELL} each)",
                             marker=dict(color=HIDDEN_GREY, line=dict(color="white", width=2)),
                             hovertemplate="%{y}<br>Small groups not shown<extra></extra>"))
    fig.update_layout(barmode="stack", legend_traceorder="normal")
    fig.update_xaxes(range=[0, 100])
    st.plotly_chart(layout(fig, 110 + 48 * len(groups)), use_container_width=True, config={"displayModeBar": False})
    st.caption(f"Base: {ind['base']}. Each bar adds up to 100% of that {dim_name.lower()}.")
    with st.expander("Show as table"):
        table_breakdown(ind, groups, dim_name, inline=False)


def table_breakdown(ind, groups, dim_name, inline=True):
    data = {"Answer": [o["label"] for o in ind["options"]]}
    for g in groups:
        data[f"{g['label']} (n={g['n']})"] = [fmt(g["counts"].get(o["code"]), g["n"]) for o in ind["options"]]
    df = pd.DataFrame(data)
    if ind["multi"]:
        df = df[~(df.iloc[:, 1:] == "0%").all(axis=1)]
    st.dataframe(df, hide_index=True, use_container_width=True)
    if inline:
        extra = " Respondents could choose more than one answer." if ind["multi"] else ""
        st.caption(f"Base: {ind['base']}. Percentages are within each {dim_name.lower()}.{extra}")


def show(key, dim, dim_name):
    ind = IND.get(key)
    if not ind:
        return
    st.markdown(f"#### {ind['title']}")
    if ind.get("too_few"):
        st.info(f"Fewer than {S['rules']['min_group']} responses so far ({ind['base']}). Results will appear once there are enough.")
        return
    if dim == "all":
        chart_overall(ind)
    else:
        chart_breakdown(ind, dim, dim_name)


# ---------------------------------------------------------------- sidebar
st.sidebar.title("Employability Pathway")
st.sidebar.caption("ADWSO vocational training graduates – post-training assessment 2026")
dims = {"all": "Overall", **{k: v for k, v in S["dimensions"].items() if k != "vocation"}}
dim = st.sidebar.radio("View results by", list(dims), format_func=dims.get)
st.sidebar.divider()
st.sidebar.markdown(
    f"**Data period:** {S['period'][0]} to {S['period'][1]}  \n**Last updated:** {S['generated']}" if S.get("period")
    else f"**Last updated:** {S['generated']}")
st.sidebar.caption(f"Privacy: only totals are shown. Groups with fewer than {MIN_CELL} respondents appear as "
                   f"\"<{MIN_CELL}\", and breakdown groups smaller than {S['rules']['min_group']} are combined.")

# ---------------------------------------------------------------- header + KPIs
st.title("Where are our vocational training graduates now?")
st.markdown("Results of ADWSO's Employability Pathway assessment of young people who completed vocational training.")

p = IND["pathway"]["all"]
n = p["n"]
c = p["counts"]
def share(*codes):
    vals = [c.get(k) for k in codes]
    return "—" if any(v is None for v in vals) else f"{100 * sum(vals) / n:.0f}%"
earn = IND["is_earning"]["all"]["counts"].get("1")
k = st.columns(5)
k[0].metric("Graduates assessed", f"{n:,}")
k[1].metric("Working in their trade", share("own_business", "employed"), help="Own business or paid work in the trained vocation (Paths A and B)")
k[2].metric("Earning from their trade", "—" if earn is None else f"{100 * earn / n:.0f}%",
            help="Any income from the trained vocation, including graduates working mainly in another field")
k[3].metric("Still in apprenticeship", share("apprentice"), help="Path C")
k[4].metric("Not working", share("not_working"), help="Path E")

tabs = st.tabs(["Pathways", "Income", "Barriers", "Toolkit & support", "Outlook", "About the data"])
dn = dims[dim]

with tabs[0]:
    st.markdown("Every graduate is placed in one of five pathways based on their main current activity.")
    show("pathway", dim, dn)
    if dim == "all":
        with st.expander("Pathway by vocation"):
            chart_breakdown(IND["pathway"], "vocation", "Vocation")
    cols = st.columns(2)
    with cols[0]:
        show("workplace", dim, dn)
        show("repeat_customers", dim, dn)
        show("appr_place", dim, dn)
    with cols[1]:
        show("find_customers", dim, dn)
        show("appr_allowance", dim, dn)
        show("past_work", dim, dn)

with tabs[1]:
    show("is_earning", dim, dn)
    cols = st.columns(2)
    with cols[0]:
        show("earning_freq", dim, dn)
        show("monthly_income", dim, dn)
        show("trade_income", dim, dn)
    with cols[1]:
        show("time_to_income", dim, dn)
        show("income_change", dim, dn)
        show("income_use", dim, dn)

with tabs[2]:
    show("reason_not_in_trade", dim, dn)
    show("market_challenges", dim, dn)
    show("toolkit_reason", dim, dn)

with tabs[3]:
    cols = st.columns(2)
    with cols[0]:
        show("toolkit_use", dim, dn)
        show("post_support", dim, dn)
    with cols[1]:
        show("toolkit_how", dim, dn)
        show("post_support_type", dim, dn)
    show("support_needed", dim, dn)

with tabs[4]:
    show("plans_3_6m", dim, dn)
    cols = st.columns(2)
    with cols[0]:
        show("continue_trade", dim, dn)
    with cols[1]:
        show("vt_benefit", dim, dn)
    show("monitor_assessment", dim, dn)

with tabs[5]:
    st.markdown(f"""
**About the assessment.** ADWSO staff interviewed vocational training graduates in person or by phone using a
KoBoToolbox questionnaire in English and Dari. Graduates under 18 took part only with the consent of a parent or
guardian, as well as their own agreement.

**The five pathways.**
A. Own business (self-employed, business group or partnership) · B. Paid employment (including paid work with the
Master Trainer) · C. Apprenticeship (still learning, without regular pay) · D. Working in another field ·
E. Not working.

**Respondents included:** {S['n_used']:,} graduates who gave consent. Submissions marked "Not approved" during
ADWSO's quality review are excluded.

**Privacy.** This dashboard shows totals only. It never contains names, phone numbers, locations below province
level, photos or individual answers. Any figure based on fewer than {MIN_CELL} graduates is shown as
"<{MIN_CELL}", and breakdown groups with fewer than {S['rules']['min_group']} graduates are combined into
"Other (combined)".
""")
    show("method", "all", "Overall")
