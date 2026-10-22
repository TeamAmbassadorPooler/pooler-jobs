#!/usr/bin/env python3
"""Add state breakdown pages to the Ambassador job board.

Runs after Ambassador Desk publishes. Reads jobs.json and:
  - writes one page per state (jobs-georgia.html, jobs-alabama.html, ...)
  - adds a meta description and a "Browse by state" section to index.html
  - rebuilds sitemap.xml to include the index, the state pages and every job

Uses only the Python standard library. Usage: python build_markets.py [site_dir]
Safe to run more than once on the same files.
"""
import html
import json
import sys
from collections import defaultdict
from pathlib import Path

BASE = "https://teamambassadorpooler.github.io/pooler-jobs/"
COMPANY = "Ambassador Personnel"

INDEX_TITLE = "Ambassador Personnel Jobs — Temporary & Direct-Hire Openings"
INDEX_DESC = (
    "Open warehouse, production, maintenance, office and skilled-trade jobs from "
    "Ambassador Personnel in {n} states. Weekly pay on temporary jobs. Apply online."
)

STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "FL": "Florida", "GA": "Georgia",
    "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
    "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi",
    "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire",
    "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York", "NC": "North Carolina",
    "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania",
    "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee",
    "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming", "DC": "Washington DC",
}

# Same look as the Desk-generated pages.
STYLE = """<style>body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;margin:0;background:#f6f7f9;color:#1d2433;line-height:1.5}
main{max-width:760px;margin:0 auto;padding:24px 16px 48px}h1{font-size:26px;margin:0 0 4px}h2{font-size:18px;margin:0}
.sub{color:#5b6475;font-size:14px}.card{background:#fff;border:1px solid #e1e5ec;border-radius:10px;padding:14px 16px;margin:12px 0}
.card a{color:inherit;text-decoration:none}.meta{color:#5b6475;font-size:14px;margin-top:2px}
.btn{display:inline-block;background:#173f6e;color:#fff!important;padding:10px 18px;border-radius:8px;text-decoration:none;font-weight:600;margin:12px 0}
footer{color:#7a8294;font-size:12px;margin-top:32px}</style>"""

STATE_CSS = """.states{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0 4px;padding:0;list-style:none}
.states a{display:inline-block;background:#fff;border:1px solid #e1e5ec;border-radius:999px;padding:4px 12px;font-size:14px;color:#173f6e;text-decoration:none}
.states a:hover{border-color:#173f6e}
"""

START, END = "<!--markets:start-->", "<!--markets:end-->"


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def slug(code):
    return "jobs-" + STATES.get(code, code).lower().replace(" ", "-") + ".html"


def pay_text(pay):
    if not pay:
        return ""
    vals = [f"${float(p):.2f}" for p in pay]
    return "–".join(vals) + "/hr"


def meta_line(j):
    parts = [f"{j.get('city', '')}, {j.get('state', '')}", pay_text(j.get("pay")), j.get("shift"), j.get("type")]
    return " · ".join(p for p in parts if p)


def card(j, prefix):
    return (f'<div class="card"><a href="{prefix}jobs/{esc(j["code"])}.html"><h2>{esc(j["title"])}</h2>'
            f'<div class="meta">{esc(meta_line(j))}</div></a></div>')


def top_cities(jobs, n=6):
    counts = defaultdict(int)
    for j in jobs:
        counts[j.get("city", "").strip()] += 1
    cities = sorted((c for c in counts if c), key=lambda c: (-counts[c], c))
    return cities[:n]


def state_page(code, jobs, data, apply_url, footer):
    name = STATES.get(code, code)
    n = len(jobs)
    noun = "job" if n == 1 else "jobs"
    cities = top_cities(jobs)
    city_txt = ", ".join(cities)
    title = f"Jobs in {name} | {COMPANY}"
    desc = f"{n} open {noun} in {name} from {COMPANY}" + (f" — {city_txt}" if city_txt else "") + ". Apply online."
    y, m, d = (data.get("updated", "")[:10].split("-") + ["", "", ""])[:3]
    updated = f"{int(m)}/{int(d)}/{y}" if y and m and d else ""
    intro = (f"{COMPANY} has {n} open {noun} in {name}"
             + (f", including openings in {city_txt}" if city_txt else "") + ".")
    cards = "\n".join(card(j, "") for j in jobs)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)}</title>
{STYLE}
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{BASE}{slug(code)}">
</head>
<body><main>
<p class="sub"><a href="index.html">← All jobs</a></p>
<h1>Jobs in {esc(name)}</h1>
<p class="sub">{n} open {noun} · updated {esc(updated)}</p>
<p>{esc(intro)}</p>
{cards}
<a class="btn" href="{esc(apply_url)}" rel="nofollow">Apply online</a>
{footer}
</main></body></html>
"""


def patch_index(index_html, by_state, n_states):
    # Title and meta description
    if "<title>" in index_html:
        a = index_html.index("<title>")
        b = index_html.index("</title>", a) + len("</title>")
        index_html = index_html[:a] + f"<title>{esc(INDEX_TITLE)}</title>" + index_html[b:]
    if 'name="description"' not in index_html:
        index_html = index_html.replace(
            "</title>", f'</title>\n<meta name="description" content="{esc(INDEX_DESC.format(n=n_states))}">', 1)

    # "Browse by state" block, replaced on every run
    links = "".join(
        f'<li><a href="{slug(c)}">{esc(STATES.get(c, c))} ({len(by_state[c])})</a></li>'
        for c in sorted(by_state, key=lambda c: STATES.get(c, c)))
    block = f'{START}\n<h2>Browse by state</h2>\n<ul class="states">{links}</ul>\n{END}'
    if START in index_html:
        a = index_html.index(START)
        b = index_html.index(END) + len(END)
        index_html = index_html[:a] + block + index_html[b:]
    else:
        marker = '<p class="sub">'
        i = index_html.find(marker)
        if i == -1:
            raise SystemExit("index.html layout changed: could not find the job count line")
        i = index_html.index("</p>", i) + len("</p>")
        index_html = index_html[:i] + "\n" + block + index_html[i:]

    # Chip styles, if the Desk's stylesheet doesn't have them yet
    if ".states{" not in index_html:
        index_html = index_html.replace("footer{", STATE_CSS + "footer{", 1)
    return index_html


def sitemap(jobs, by_state, updated):
    urls = [BASE] + [BASE + slug(c) for c in sorted(by_state)]
    urls += [f"{BASE}jobs/{j['code']}.html" for j in jobs]
    seen, rows = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u)
            rows.append(f"<url><loc>{esc(u)}</loc><lastmod>{updated}</lastmod></url>")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
            + "\n".join(rows) + "\n</urlset>\n")


def main():
    site = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    data = json.loads((site / "jobs.json").read_text(encoding="utf-8"))
    jobs = [j for j in data.get("jobs", []) if j.get("code") and j.get("state")]
    apply_url = data.get("applyUrl") or "https://www.teamambassador.com/Jobs.aspx"
    updated = (data.get("updated") or "")[:10]

    by_state = defaultdict(list)
    for j in jobs:
        by_state[j["state"].strip().upper()].append(j)

    index_path = site / "index.html"
    index_html = index_path.read_text(encoding="utf-8")
    footer = ""
    if "<footer>" in index_html:
        footer = index_html[index_html.index("<footer>"):index_html.index("</footer>") + len("</footer>")]

    # Remove state pages left over from states with no jobs now
    for old in site.glob("jobs-*.html"):
        old.unlink()

    for code, sjobs in by_state.items():
        (site / slug(code)).write_text(state_page(code, sjobs, data, apply_url, footer), encoding="utf-8")

    index_path.write_text(patch_index(index_html, by_state, len(by_state)), encoding="utf-8")
    (site / "sitemap.xml").write_text(sitemap(jobs, by_state, updated), encoding="utf-8")
    print(f"{len(jobs)} jobs, {len(by_state)} state pages written")


if __name__ == "__main__":
    main()
