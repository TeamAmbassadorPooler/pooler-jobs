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


# ---------------------------------------------------------------------------
# Branch callback numbers: each job gets the phone of its closest branch.
# Source: teamambassador.com/Our-Locations.aspx. Edit this list if a branch
# opens, closes or changes its number.
BRANCHES = [
    ("Birmingham", "35209", "(205) 640-7480"),
    ("Enterprise", "36330", "(334) 347-3496"),
    ("Montgomery", "36109", "(334) 271-1666"),
    ("Tuscaloosa", "35404", "(205) 758-5508"),
    ("Valley", "36854", "(706) 634-9075"),
    ("Batesville", "72501", "(870) 698-9400"),
    ("Bainbridge", "39819", "(229) 246-2297"),
    ("Cordele", "31015", "(229) 273-2999"),
    ("Douglas", "31533", "(912) 493-9327"),
    ("Douglasville", "30135", "(770) 942-0311"),
    ("Macon", "31210", "(478) 474-8600"),
    ("Pooler", "31322", "(912) 330-7210"),
    ("Suwanee", "30024", "(678) 765-8198"),
    ("Thomasville", "31792", "(229) 226-0647"),
    ("Tifton", "31794", "(229) 387-8055"),
    ("Valdosta", "31602", "(229) 253-1184"),
    ("Charlotte", "28217", "(704) 522-1188"),
    ("Clinton", "28328", "(910) 592-1904"),
    ("Gaffney", "29341", "(864) 488-0047"),
    ("Spartanburg", "29301", "(864) 574-0427"),
]
DESK_PHONE = "(912) 330-7210"  # the number Ambassador Desk writes on every job
MAX_MILES = 150  # farther than this from every branch: no phone, apply online only


def _city_key(city):
    return "".join(ch for ch in str(city).lower() if ch.isalnum())


class ZipBook:
    """ZIP code lookups from the offline `zipcodes` package (USPS data)."""

    def __init__(self):
        import zipcodes  # installed by the workflow: pip install zipcodes
        self.by_zip, self.by_city = {}, defaultdict(list)
        for z in zipcodes.list_all():
            if not z.get("lat") or not z.get("long"):
                continue
            rec = (z["zip_code"], z["state"], float(z["lat"]), float(z["long"]), z.get("zip_code_type"))
            self.by_zip[z["zip_code"]] = rec
            for c in [z["city"]] + list(z.get("acceptable_cities") or []):
                self.by_city[(_city_key(c), z["state"])].append(rec)

    def city_zip(self, city, state):
        recs = self.by_city.get((_city_key(city), state), [])
        std = [r for r in recs if r[4] == "STANDARD"] or recs
        return min(std) if std else None  # lowest standard ZIP = main post office area

    def locate(self, job):
        """Return (zip, lat, lon, how). Keeps a valid in-state ZIP, else fills from the city."""
        state = str(job.get("state", "")).strip().upper()
        z = str(job.get("zip") or "").strip()[:5]
        rec = self.by_zip.get(z)
        if rec and rec[1] == state:
            return rec[0], rec[2], rec[3], "kept"
        found = self.city_zip(job.get("city", ""), state)
        if found:
            return found[0], found[2], found[3], ("filled" if not z else "corrected")
        return (z or None), None, None, "unresolved"


def _miles(a, b, c, d):
    from math import radians, sin, cos, asin, sqrt
    a, b, c, d = map(radians, (a, b, c, d))
    h = sin((c - a) / 2) ** 2 + cos(a) * cos(c) * sin((d - b) / 2) ** 2
    return 3958.8 * 2 * asin(sqrt(h))


def assign_branches(jobs, book):
    branches = []
    for name, z, phone in BRANCHES:
        rec = book.by_zip[z]
        branches.append((name, phone, rec[2], rec[3]))
    log = defaultdict(int)
    for j in jobs:
        zip_, lat, lon, how = book.locate(j)
        log[how] += 1
        if how in ("filled", "corrected"):
            j["zip"] = zip_
        if lat is None:
            j["branch"], j["branchPhone"] = None, None
            log["no branch nearby"] += 1
            continue
        dist, name, phone = min((_miles(lat, lon, b[2], b[3]), b[0], b[1]) for b in branches)
        if dist > MAX_MILES:
            j["branch"], j["branchPhone"] = None, None
            log["no branch nearby"] += 1
        else:
            j["branch"], j["branchPhone"] = name, phone
    return dict(log)


def how_to_apply(job):
    if job.get("branchPhone"):
        return f"Apply online or call our {job['branch']} office at {job['branchPhone']}"
    return "Apply online and a recruiter will contact you"


def patch_job_page(path, job):
    if not path.exists():
        return
    page = path.read_text(encoding="utf-8")
    page = page.replace(f"Apply online or call {DESK_PHONE}", how_to_apply(job))
    # Google job markup: add or fix the postal code
    if job.get("zip"):
        pc = f'"postalCode": "{job["zip"]}"'
        i = page.find('"postalCode": "')
        if i != -1:
            k = page.index('"', i + len('"postalCode": "'))
            page = page[:i] + pc + page[k + 1:]
        else:
            page = page.replace('"addressRegion": ', pc + ',\n      "addressRegion": ', 1)
    path.write_text(page, encoding="utf-8")


def patch_feed(path, jobs_by_code):
    """Same phone and ZIP fixes in jobs.xml, the feed job boards read."""
    if not path.exists():
        return
    xml = path.read_text(encoding="utf-8")
    out, pos = [], 0
    while True:
        a = xml.find("<job>", pos)
        if a == -1:
            out.append(xml[pos:])
            break
        b = xml.index("</job>", a) + len("</job>")
        block = xml[a:b]
        r = block.find("<referencenumber><![CDATA[")
        code = block[r + 26:block.index("]]>", r)] if r != -1 else ""
        j = jobs_by_code.get(code)
        if j:
            block = block.replace(f"Apply online or call {DESK_PHONE}", how_to_apply(j))
            if j.get("zip"):
                p = block.find("<postalcode><![CDATA[")
                if p != -1:
                    q = block.index("]]>", p)
                    block = block[:p + 21] + j["zip"] + block[q:]
        out.append(xml[pos:a] + block)
        pos = b
    path.write_text("".join(out), encoding="utf-8")
# ---------------------------------------------------------------------------


def main():
    site = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    data = json.loads((site / "jobs.json").read_text(encoding="utf-8"))
    jobs = [j for j in data.get("jobs", []) if j.get("code") and j.get("state")]
    apply_url = data.get("applyUrl") or "https://www.teamambassador.com/Jobs.aspx"
    updated = (data.get("updated") or "")[:10]

    # Pages for jobs no longer in the feed (closed or switched off) don't get published
    codes = {j["code"] for j in jobs}
    for p in (site / "jobs").glob("*.html"):
        if p.stem not in codes:
            p.unlink()

    # Branch phone numbers and ZIP fixes
    log = assign_branches(jobs, ZipBook())
    for j in jobs:
        patch_job_page(site / "jobs" / f"{j['code']}.html", j)
    patch_feed(site / "jobs.xml", {j["code"]: j for j in jobs})
    (site / "jobs.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print("ZIPs:", log)

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
