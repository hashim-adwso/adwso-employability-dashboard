"""
PRIVATE STEP – builds the public summary for the Employability Pathway dashboard.

Downloads submissions from KoBoToolbox, keeps ONLY the fields needed for counting,
aggregates them, applies small-cell suppression and writes data/summary.json.

No names, phone numbers, GPS, photos, enumerator details, districts/villages,
free-text answers or individual records are ever written to disk.

Usage (normally run by the GitHub Actions workflow):
    KOBO_TOKEN=... python aggregate.py
Offline test:
    python aggregate.py --asset asset.json --data submissions.json
"""
import argparse
import datetime as dt
import json
import os
import sys
from collections import Counter

import requests

SERVER = os.environ.get("KOBO_SERVER", "https://kf.kobotoolbox.org")
ASSET_UID = os.environ.get("KOBO_ASSET_UID", "a4Pwb3bVXuNDAub4dRBNia")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "summary.json")

MIN_CELL = 5    # any count from 1 to 4 is hidden ("<5")
MIN_GROUP = 10  # a filtered view (e.g. one province) needs at least 10 respondents to show results

# Only these fields are read from each submission. Everything else is discarded.
KEEP = {
    "province", "gender", "age", "vocation", "consent_ok", "pathway", "is_earning", "earning_freq",
    "trade_income", "time_to_income", "monthly_income", "income_change", "income_use",
    "reason_not_in_trade", "market_challenges", "workplace", "find_customers", "repeat_customers",
    "has_customers", "appr_place", "appr_allowance", "past_work", "toolkit_use", "toolkit_how",
    "toolkit_reason", "post_support", "post_support_type", "plans_3_6m", "continue_trade",
    "support_needed", "vt_benefit", "monitor_assessment", "monitoring_method",
}

PATHWAY_LABELS = [
    ("own_business", "A. Own business"),
    ("employed", "B. Paid employment"),
    ("apprentice", "C. Apprenticeship"),
    ("other_field", "D. Working in another field"),
    ("not_working", "E. Not working"),
]
AGE_GROUPS = [("14-17", "14–17 years"), ("18+", "18 years and above")]

EARNERS = lambda r: r.get("is_earning") == "1"
# key, field, list(None = from form), multi, base filter, base description, title, page
INDICATORS = [
    ("pathway", "pathway", "_pathway", False, None, "All respondents", "Employability pathway", "pathways"),
    ("method", "monitoring_method", None, False, None, "All respondents", "Interview method", "about"),
    ("earning_freq", "earning_freq", "earning", False, EARNERS, "Respondents earning from their trade",
     "How often they earn from the trade", "income"),
    ("is_earning", "is_earning", "_yesno", False, None, "All respondents",
     "Earning any income from the trained vocation", "income"),
    ("trade_income", "trade_income", None, False, lambda r: r.get("pathway") == "other_field",
     "Path D – working in another field", "Still earning from the trade alongside other work", "income"),
    ("monthly_income", "monthly_income", None, False, EARNERS, "Respondents earning from their trade",
     "Monthly income from the trade (AFN)", "income"),
    ("time_to_income", "time_to_income", None, False, EARNERS, "Respondents earning from their trade",
     "Time from graduation to first income", "income"),
    ("income_change", "income_change", None, False, EARNERS, "Respondents earning from their trade",
     "Change in income compared with before the training", "income"),
    ("income_use", "income_use", None, True, EARNERS, "Respondents earning from their trade",
     "What the income is used for", "income"),
    ("workplace", "workplace", None, False, lambda r: r.get("pathway") in ("own_business", "employed"),
     "Paths A and B", "Main place of work", "pathways"),
    ("find_customers", "find_customers", None, True, lambda r: r.get("pathway") == "own_business",
     "Path A – own business", "How they find customers", "pathways"),
    ("repeat_customers", "repeat_customers", None, False, lambda r: r.get("has_customers") == "1",
     "Path A with customers", "Repeat customers or orders", "pathways"),
    ("appr_place", "appr_place", None, False, lambda r: r.get("pathway") == "apprentice",
     "Path C – apprentices", "Where the apprenticeship takes place", "pathways"),
    ("appr_allowance", "appr_allowance", None, False, lambda r: r.get("pathway") == "apprentice",
     "Path C – apprentices", "Receives payment or allowance during apprenticeship", "pathways"),
    ("past_work", "past_work", None, False, lambda r: r.get("pathway") == "not_working",
     "Path E – not working", "Worked or earned at any time since graduation", "pathways"),
    ("reason_not_in_trade", "reason_not_in_trade", None, True,
     lambda r: r.get("pathway") in ("other_field", "not_working"), "Paths D and E",
     "Reasons for not working in the trained vocation", "barriers"),
    ("market_challenges", "market_challenges", None, True,
     lambda r: r.get("pathway") in ("own_business", "not_working"), "Paths A and E",
     "Main challenges in finding customers, work or markets", "barriers"),
    ("toolkit_reason", "toolkit_reason", None, True,
     lambda r: r.get("toolkit_use") in ("sometimes", "rarely", "no"), "Toolkit used sometimes, rarely or not at all",
     "Reasons the toolkit is not used regularly", "barriers"),
    ("toolkit_use", "toolkit_use", None, False, None, "All respondents", "Use of the toolkit provided", "support"),
    ("toolkit_how", "toolkit_how", None, True,
     lambda r: r.get("toolkit_use") in ("regularly", "sometimes", "rarely"), "Respondents using the toolkit",
     "How the toolkit is used", "support"),
    ("post_support", "post_support", None, False, None, "All respondents",
     "Received support after the training", "support"),
    ("post_support_type", "post_support_type", None, True, lambda r: r.get("post_support") == "yes",
     "Respondents who received support", "Type of support received", "support"),
    ("support_needed", "support_needed", None, True, None, "All respondents",
     "Most important support still needed", "support"),
    ("plans_3_6m", "plans_3_6m", None, False, None, "All respondents", "Main plan for the next 3–6 months", "outlook"),
    ("continue_trade", "continue_trade", None, False, None, "All respondents",
     "Plans to continue in the trained vocation next year", "outlook"),
    ("vt_benefit", "vt_benefit", None, False, None, "All respondents",
     "Graduates' own rating of the training's benefit", "outlook"),
    ("monitor_assessment", "monitor_assessment", None, False, None, "All respondents",
     "Monitor's assessment of employability", "outlook"),
]
BREAKDOWNS = ["province", "gender", "age_group"]
VOCATION_INDICATORS = {"pathway", "is_earning"}


# ---------------------------------------------------------------- data access
def kobo_get(url, token):
    r = requests.get(url, headers={"Authorization": f"Token {token}"}, timeout=120)
    r.raise_for_status()
    return r.json()


def load_asset(path, token):
    if path:
        return json.load(open(path, encoding="utf-8"))
    return kobo_get(f"{SERVER}/api/v2/assets/{ASSET_UID}/?format=json", token)


def load_submissions(path, token):
    if path:
        return json.load(open(path, encoding="utf-8"))
    rows, url = [], f"{SERVER}/api/v2/assets/{ASSET_UID}/data/?format=json&limit=1000"
    while url:
        page = kobo_get(url, token)
        rows.extend(page.get("results", []))
        url = page.get("next")
    return rows


def clean(sub):
    """Reduce one raw submission to the whitelisted fields (group prefixes removed)."""
    status = (sub.get("_validation_status") or {}).get("uid", "")
    out = {}
    for k, v in sub.items():
        name = k.split("/")[-1]
        if name in KEEP and v not in (None, ""):
            out[name] = str(v)
    out["_not_approved"] = status == "validation_status_not_approved"
    out["_month"] = str(sub.get("_submission_time") or sub.get("today") or "")[:7]
    try:
        out["age_group"] = "14-17" if int(float(out.pop("age", "0"))) < 18 else "18+"
    except ValueError:
        out["age_group"] = None
    return out


# ---------------------------------------------------------------- labels
def build_labels(asset):
    content = asset["content"]
    choices = {}
    for c in content.get("choices", []):
        lab = c.get("label") or [c["name"]]
        choices.setdefault(c["list_name"], []).append((c["name"], lab[0] if isinstance(lab, list) else lab))
    field_list = {}
    for r in content.get("survey", []):
        name = r.get("name") or r.get("$autoname")
        if r.get("select_from_list_name"):
            field_list[name] = r["select_from_list_name"]
    choices["_pathway"] = PATHWAY_LABELS
    choices["_yesno"] = [("1", "Yes"), ("0", "No")]
    choices["_age_group"] = AGE_GROUPS
    return choices, field_list


# ---------------------------------------------------------------- suppression
def suppress_cells(counts, multi, n):
    """counts: {code: int}. Returns {code: int|None}; None is shown as '<5' (hidden).

    - A group with fewer than MIN_GROUP respondents shows its size only: every answer is hidden.
    - Any count from 1 to 4 is hidden.
    - Single-choice questions: if only one answer would be hidden, a second one is hidden too, so the
      hidden value cannot be worked out by subtracting the others from the group total.
    """
    if n < MIN_GROUP:
        return {k: None for k in counts}
    out = {k: (None if 0 < v < MIN_CELL else v) for k, v in counts.items()}
    if not multi:
        hidden = [k for k, v in out.items() if v is None]
        if len(hidden) == 1:
            shown = sorted((v, k) for k, v in out.items() if v)
            if shown:
                out[shown[0][1]] = None
            else:  # every other answer is 0 – hide those zeros as well
                out = {k: None for k in out}
    return out


def tabulate(rows, field, multi, codes):
    c = Counter()
    for r in rows:
        v = r.get(field)
        if not v:
            continue
        for code in (v.split() if multi else [v]):
            c[code] += 1
    return {code: c.get(code, 0) for code in codes}


def group_rows(rows, dim, order):
    """Split rows by dimension. Every group is kept separately – groups are never merged.
    Small groups are still protected because every count of 1–4 is shown only as '<5'.
    For vocation (many small groups) only vocations with at least MIN_CELL respondents are listed."""
    groups = [(g, [r for r in rows if r.get(dim) == g]) for g in order]
    groups = [(g, rs) for g, rs in groups if rs]
    if dim == "vocation":
        groups = [(g, rs) for g, rs in groups if len(rs) >= MIN_CELL]
    return groups


def summarise(rows, field, multi, codes):
    return {"n": len(rows), "counts": suppress_cells(tabulate(rows, field, multi, codes), multi, len(rows))}


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--asset")
    ap.add_argument("--data")
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()
    token = os.environ.get("KOBO_TOKEN", "")
    if not (a.asset and a.data) and not token:
        sys.exit("Set KOBO_TOKEN (or pass --asset and --data for an offline test).")

    choices, field_list = build_labels(load_asset(a.asset, token))
    raw = load_submissions(a.data, token)
    rows = [clean(s) for s in raw]
    raw = None  # drop raw records from memory
    excluded_review = sum(r["_not_approved"] for r in rows)
    rows = [r for r in rows if not r["_not_approved"]]
    no_consent = sum(r.get("consent_ok") != "1" for r in rows)
    rows = [r for r in rows if r.get("consent_ok") == "1"]
    if len(rows) < MIN_GROUP:
        sys.exit(f"Only {len(rows)} usable submissions – too few to publish safely. Nothing written.")

    dim_order = {
        "province": [c for c, _ in choices.get(field_list.get("province", ""), [])],
        "gender": [c for c, _ in choices.get(field_list.get("gender", ""), [])],
        "age_group": [c for c, _ in AGE_GROUPS],
        "vocation": [c for c, _ in choices.get(field_list.get("vocation", ""), [])],
    }
    dim_labels = {
        "province": dict(choices.get(field_list.get("province", ""), [])),
        "gender": dict(choices.get(field_list.get("gender", ""), [])),
        "age_group": dict(AGE_GROUPS),
        "vocation": dict(choices.get(field_list.get("vocation", ""), [])),
    }

    def build_indicators(sub_rows, fixed):
        out = {}
        for key, field, lst, multi, base, base_desc, title, page in INDICATORS:
            opts = choices.get(lst or field_list.get(field, ""), [])
            codes = [c for c, _ in opts]
            base_rows = [r for r in sub_rows if (base is None or base(r))]
            if len(base_rows) < MIN_GROUP:
                out[key] = {"too_few": True, "n": len(base_rows)}
                continue
            ind = {"too_few": False, "all": summarise(base_rows, field, multi, codes), "by": {}}
            dims = [d for d in BREAKDOWNS if d not in fixed] + (["vocation"] if key in VOCATION_INDICATORS else [])
            for d in dims:
                ind["by"][d] = [{"group": g, "label": dim_labels[d].get(g, g), **summarise(rs, field, multi, codes)}
                                for g, rs in group_rows(base_rows, d, dim_order[d])]
            out[key] = ind
        return out

    meta = {}
    for key, field, lst, multi, base, base_desc, title, page in INDICATORS:
        opts = choices.get(lst or field_list.get(field, ""), [])
        meta[key] = {"title": title, "page": page, "base": base_desc, "multi": multi,
                     "options": [{"code": c, "label": l} for c, l in opts]}

    # Pre-computed views for every filter combination: "province|gender|age_group", '*' = all.
    present = {d: [g for g in dim_order[d] if any(r.get(d) == g for r in rows)] for d in BREAKDOWNS}
    views, view_n = {}, {}
    for p in ["*"] + present["province"]:
        for g in ["*"] + present["gender"]:
            for ag in ["*"] + present["age_group"]:
                sub = [r for r in rows if (p == "*" or r.get("province") == p)
                       and (g == "*" or r.get("gender") == g) and (ag == "*" or r.get("age_group") == ag)]
                vkey = f"{p}|{g}|{ag}"
                view_n[vkey] = len(sub)
                if len(sub) < MIN_GROUP:
                    continue
                fixed = {d for d, v in zip(BREAKDOWNS, (p, g, ag)) if v != "*"}
                views[vkey] = build_indicators(sub, fixed)

    months = sorted(r["_month"] for r in rows if r["_month"])
    summary = {
        "generated": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "period": [months[0], months[-1]] if months else None,
        "n_used": len(rows),
        "n_excluded_review": excluded_review if excluded_review >= MIN_CELL or excluded_review == 0 else None,
        "n_no_consent": no_consent if no_consent >= MIN_CELL or no_consent == 0 else None,
        "rules": {"min_cell": MIN_CELL, "min_group": MIN_GROUP},
        "dimensions": {"province": "Province", "gender": "Gender", "age_group": "Age group", "vocation": "Vocation"},
        "filters": {d: [{"code": c, "label": dim_labels[d].get(c, c)} for c in present[d]] for d in BREAKDOWNS},
        "meta": meta,
        "view_n": view_n,
        "views": views,
    }
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, separators=(",", ":"))
    print(f"Wrote {a.out}: {len(rows)} respondents, {len(views)} filter views.")


if __name__ == "__main__":
    main()
