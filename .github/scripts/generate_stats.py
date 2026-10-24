#!/usr/bin/env python3
"""
Generates three flat, crisp SVG stat cards (stats + rank, streak, languages)
and points the README at them.

Design notes
- Flat opaque fills only: no blur filters, no translucency, nothing to go hazy.
- Each card's filename carries a hash of its contents (stats.1a2b3c4d.svg), so a
  changed card always has a brand-new URL. Clients that cache images by URL
  (the mobile app that kept showing the old cards) can never serve stale ones.
- Unchanged data produces identical bytes, so no no-op commits.
- On any API failure nothing is touched and the script exits non-zero.

Standard library only.
"""

import hashlib
import json
import os
import re
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from xml.sax.saxutils import escape

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
README = os.path.join(ROOT, "README.md")
ASSETS = os.path.join(ROOT, "assets")
START, END = "<!-- STATS:START -->", "<!-- STATS:END -->"

REPO = os.environ.get("GITHUB_REPOSITORY", "Willow7737/Willow7737")
BRANCH = "main"
NAME = os.environ.get("PROFILE_NAME", "Weaver")

# Build/script files that say nothing about what you actually write.
IGNORED_LANGS = {"Makefile", "Dockerfile", "CMake", "Batchfile", "Shell", "Nix"}

# Palette
BG, BORDER = "#0f1418", "#1d262c"
TITLE, LABEL, VALUE = "#2fa688", "#d5dde0", "#a8dccd"
MUTED, TRACK = "#8b9aa0", "#222c33"
FLAME = "#f2a03d"
FONT = "'Segoe UI',Ubuntu,'Helvetica Neue',Helvetica,Arial,sans-serif"

W = 480  # all cards share one width so they stack cleanly

GRAPHQL = "https://api.github.com/graphql"
QUERY = """
query {
  viewer {
    followers { totalCount }
    pullRequests { totalCount }
    issues { totalCount }
    repositoriesContributedTo(first: 1, contributionTypes: [COMMIT, ISSUE, PULL_REQUEST, REPOSITORY]) { totalCount }
    repositories(first: 100, ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false) {
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestReviewContributions
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionCount date } }
      }
    }
  }
}
"""


# --------------------------------------------------------------------------- data

def gql(token):
    req = urllib.request.Request(
        GRAPHQL,
        data=json.dumps({"query": QUERY}).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "profile-stats-generator",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def fmt_date(s):
    return datetime.strptime(s, "%Y-%m-%d").strftime("%b %-d, %Y")


def streaks(weeks, today=None):
    today = today or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    days = sorted(
        (d["date"], d["contributionCount"])
        for w in weeks
        for d in w["contributionDays"]
        if d["date"] <= today
    )

    # Current streak: today isn't over yet, so an empty today doesn't break it.
    i = len(days) - 1
    if i >= 0 and days[i][0] == today and days[i][1] == 0:
        i -= 1
    cur_end = days[i][0] if i >= 0 else None
    cur = 0
    while i >= 0 and days[i][1] > 0:
        cur += 1
        i -= 1
    cur_start = days[i + 1][0] if cur else None

    longest, run, run_start = 0, 0, None
    best = (None, None)
    for date, count in days:
        if count > 0:
            if run == 0:
                run_start = date
            run += 1
            if run > longest:
                longest, best = run, (run_start, date)
        else:
            run = 0

    return {
        "today": today,
        "first": days[0][0] if days else today,
        "cur": cur, "cur_start": cur_start, "cur_end": cur_end,
        "longest": longest, "long_start": best[0], "long_end": best[1],
    }


def rank(commits, prs, issues, reviews, stars, followers):
    """Approximation of github-readme-stats' ranking: weighted percentile score."""
    exp_cdf = lambda x: 1 - 2 ** -x
    log_cdf = lambda x: x / (1 + x)
    total_weight = 2 + 3 + 1 + 1 + 4 + 1
    score = (
        2 * exp_cdf(commits / 250)
        + 3 * exp_cdf(prs / 50)
        + 1 * exp_cdf(issues / 25)
        + 1 * exp_cdf(reviews / 2)
        + 4 * log_cdf(stars / 50)
        + 1 * log_cdf(followers / 10)
    ) / total_weight
    percentile = (1 - score) * 100
    thresholds = [1, 12.5, 25, 37.5, 50, 62.5, 75, 87.5, 100]
    levels = ["S", "A+", "A", "A-", "B+", "B", "B-", "C+", "C"]
    level = next((l for t, l in zip(thresholds, levels) if percentile <= t), "C")
    return level, score


def summarize(v):
    repos = v["repositories"]["nodes"]
    cc = v["contributionsCollection"]
    cal = cc["contributionCalendar"]

    size_by, color_by = defaultdict(int), {}
    for repo in repos:
        for e in repo["languages"]["edges"]:
            n = e["node"]["name"]
            if n in IGNORED_LANGS:
                continue
            size_by[n] += e["size"]
            color_by.setdefault(n, e["node"]["color"] or MUTED)
    top = sorted(size_by.items(), key=lambda kv: kv[1], reverse=True)[:8]

    s = {
        "stars": sum(r["stargazerCount"] for r in repos),
        "commits": cc["totalCommitContributions"],
        "reviews": cc["totalPullRequestReviewContributions"],
        "prs": v["pullRequests"]["totalCount"],
        "issues": v["issues"]["totalCount"],
        "contributed_to": v["repositoriesContributedTo"]["totalCount"],
        "followers": v["followers"]["totalCount"],
        "total": cal["totalContributions"],
        "langs": [(n, sz, color_by[n]) for n, sz in top],
        "streak": streaks(cal["weeks"]),
    }
    s["rank"], s["score"] = rank(
        s["commits"], s["prs"], s["issues"], s["reviews"], s["stars"], s["followers"]
    )
    return s


# --------------------------------------------------------------------------- svg

def card(h, body, label):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" '
        f'viewBox="0 0 {W} {h}" shape-rendering="geometricPrecision" '
        f'text-rendering="optimizeLegibility" role="img" aria-label="{escape(label, {chr(34): "&quot;"})}">\n'
        f'  <rect x="0.5" y="0.5" width="{W - 1}" height="{h - 1}" rx="6" fill="{BG}" stroke="{BORDER}"/>\n'
        f"{body}\n</svg>\n"
    )


def text(x, y, s, size=14, fill=LABEL, weight=400, anchor="start"):
    return (
        f'  <text x="{x}" y="{y}" fill="{fill}" font-size="{size}" font-weight="{weight}" '
        f'text-anchor="{anchor}" font-family="{FONT}">{escape(str(s))}</text>'
    )


def icon(name, x, y):
    paths = {
        "star": '<polygon points="8,1.5 10,6 14.5,6.4 11.1,9.4 12.2,14 8,11.6 3.8,14 4.9,9.4 1.5,6.4 6,6"/>',
        "commit": '<circle cx="8" cy="8" r="3"/><line x1="1" y1="8" x2="5" y2="8"/><line x1="11" y1="8" x2="15" y2="8"/>',
        "pr": ('<circle cx="4" cy="3.5" r="1.8"/><circle cx="4" cy="12.5" r="1.8"/><circle cx="12" cy="12.5" r="1.8"/>'
               '<line x1="4" y1="5.3" x2="4" y2="10.7"/><path d="M12 10.7V6.5a2 2 0 0 0-2-2H8.5"/>'),
        "issue": '<circle cx="8" cy="8" r="6.3"/><line x1="8" y1="4.8" x2="8" y2="8.6"/><circle cx="8" cy="11" r="0.6" fill="currentColor"/>',
        "repo": '<rect x="3" y="1.5" width="10" height="13" rx="1.5"/><line x1="3" y1="11.5" x2="13" y2="11.5"/>',
    }
    return (
        f'  <g transform="translate({x},{y})" fill="none" stroke="{TITLE}" color="{TITLE}" '
        f'stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round">{paths[name]}</g>'
    )


def k(n):
    return f"{n / 1000:.1f}".rstrip("0").rstrip(".") + "k" if n >= 1000 else f"{n:,}"


def stats_svg(s):
    rows = [
        ("star", "Total Stars Earned", f"{s['stars']:,}"),
        ("commit", "Total Commits (last year)", k(s["commits"])),
        ("pr", "Total PRs", f"{s['prs']:,}"),
        ("issue", "Total Issues", f"{s['issues']:,}"),
        ("repo", "Contributed to (last year)", f"{s['contributed_to']:,}"),
    ]
    parts = [text(28, 42, f"{NAME}'s GitHub Stats", size=20, fill=TITLE, weight=700)]
    for i, (ic, label, value) in enumerate(rows):
        y = 82 + i * 26
        parts.append(icon(ic, 28, y - 12))
        parts.append(text(54, y, label, size=13, fill=LABEL, weight=600))
        parts.append(text(278, y, value, size=13, fill=VALUE, weight=700))

    # Rank ring
    cx, cy, r = 400, 112, 38
    circ = 2 * 3.14159265 * r
    prog = max(0.03, min(1, s["score"])) * circ
    parts.append(f'  <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{TRACK}" stroke-width="7"/>')
    parts.append(
        f'  <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{TITLE}" stroke-width="7" '
        f'stroke-linecap="round" stroke-dasharray="{prog:.1f} {circ:.1f}" transform="rotate(-90 {cx} {cy})"/>'
    )
    parts.append(text(cx, cy + 8, s["rank"], size=24, fill=VALUE, weight=700, anchor="middle"))

    return card(
        218, "\n".join(parts),
        f"{NAME}'s GitHub stats: {s['stars']} stars, {s['commits']} commits, {s['prs']} PRs, "
        f"{s['issues']} issues, rank {s['rank']}",
    )


def flame(cx, cy, scale=1.0):
    d = "M0,-11 C3,-6 8,-3 8,3 A8,8 0 0 1 -8,3 C-8,0 -6,-2 -4,-5 C-3,-2 -2,-1 0,0 C2,-3 1,-7 0,-11 Z"
    return (
        f'  <path d="{d}" transform="translate({cx},{cy}) scale({scale})" fill="{FLAME}"/>'
    )


def streak_svg(s):
    st = s["streak"]
    cur_recent = lambda e: e and e >= (
        datetime.strptime(st["today"], "%Y-%m-%d") - timedelta(days=1)
    ).strftime("%Y-%m-%d")

    def rng(a, b):
        if not a:
            return ""
        end = "Present" if cur_recent(b) else fmt_date(b)
        return f"{fmt_date(a)} - {end}"

    parts = []
    # Dividers
    for x in (160, 320):
        parts.append(f'  <line x1="{x}" y1="28" x2="{x}" y2="132" stroke="{BORDER}"/>')

    # Left: total contributions
    parts += [
        text(80, 86, f"{s['total']:,}", size=28, fill=VALUE, weight=700, anchor="middle"),
        text(80, 110, "Total Contributions", size=12, fill=LABEL, anchor="middle"),
        text(80, 130, rng(st["first"], st["today"]), size=10, fill=MUTED, anchor="middle"),
    ]

    # Middle: current streak ring with flame in the gap
    cx, cy, r = 240, 76, 34
    circ = 2 * 3.14159265 * r
    gap = 26
    parts.append(
        f'  <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{FLAME}" stroke-width="4" '
        f'stroke-linecap="round" stroke-dasharray="{circ - gap:.1f} {gap:.1f}" '
        f'transform="rotate({-90 + (gap / circ) * 180:.1f} {cx} {cy})"/>'
    )
    parts.append(flame(cx, cy - r, 0.9))
    parts.append(text(cx, cy + 9, st["cur"], size=26, fill=FLAME, weight=700, anchor="middle"))
    parts.append(text(cx, 132, "Current Streak", size=12, fill=FLAME, weight=600, anchor="middle"))

    # Right: longest streak
    parts += [
        text(400, 86, st["longest"], size=28, fill=VALUE, weight=700, anchor="middle"),
        text(400, 110, "Longest Streak", size=12, fill=LABEL, anchor="middle"),
        text(400, 130, rng(st["long_start"], st["long_end"]), size=10, fill=MUTED, anchor="middle"),
    ]

    return card(
        160, "\n".join(parts),
        f"Streaks: {s['total']} contributions in the past year, current streak {st['cur']} days, "
        f"longest {st['longest']} days",
    )


def langs_svg(s):
    langs = s["langs"]
    parts = [text(28, 42, "Most Used Languages", size=20, fill=TITLE, weight=700)]
    if not langs:
        parts.append(text(28, 90, "No language data yet", size=13, fill=MUTED))
        return card(120, "\n".join(parts), "No language data yet")

    total = sum(sz for _, sz, _ in langs)
    bx, by, bw, bh = 28, 62, W - 56, 10
    parts.append(
        f'  <clipPath id="bar"><rect x="{bx}" y="{by}" width="{bw}" height="{bh}" rx="5"/></clipPath>\n'
        f'  <g clip-path="url(#bar)">'
    )
    x = bx
    for _, sz, color in langs:
        seg = bw * sz / total
        parts.append(f'    <rect x="{x:.2f}" y="{by}" width="{seg + 0.5:.2f}" height="{bh}" fill="{color}"/>')
        x += seg
    parts.append("  </g>")

    rows = (len(langs) + 1) // 2
    for i, (name, sz, color) in enumerate(langs):
        col, row = i // rows, i % rows  # fill down the first column, then the second
        x0 = 28 + col * 224
        y = 108 + row * 28
        parts.append(f'  <circle cx="{x0 + 6}" cy="{y - 5}" r="6" fill="{color}"/>')
        parts.append(
            f'  <text x="{x0 + 22}" y="{y}" font-size="13" font-family="{FONT}">'
            f'<tspan fill="{LABEL}" font-weight="600">{escape(name)}</tspan>'
            f'<tspan fill="{MUTED}" dx="6">{sz / total * 100:.2f}%</tspan></text>'
        )

    h = 108 + (rows - 1) * 28 + 28
    summary = ", ".join(f"{n} {sz / total * 100:.1f}%" for n, sz, _ in langs[:4])
    return card(h, "\n".join(parts), f"Most used languages: {summary}")


# --------------------------------------------------------------------------- output

def write_asset(stem, svg):
    os.makedirs(ASSETS, exist_ok=True)
    name = f"{stem}.{hashlib.sha1(svg.encode()).hexdigest()[:8]}.svg"
    with open(os.path.join(ASSETS, name), "w", encoding="utf-8") as f:
        f.write(svg)
    return name


def prune_assets(keep):
    pat = re.compile(r"^(stats|streak|langs)\.[0-9a-f]{8}\.svg$|\.svg$")
    for fn in os.listdir(ASSETS):
        if pat.search(fn) and fn not in keep:
            os.remove(os.path.join(ASSETS, fn))


def img(name, alt):
    url = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/assets/{name}"
    alt = escape(alt, {'"': "&quot;"})
    return f'<p align="center">\n  <img alt="{alt}" src="{url}" width="{W}"/>\n</p>'


def patch_readme(block):
    with open(README, encoding="utf-8") as f:
        text_ = f.read()
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    if not pattern.search(text_):
        sys.exit(f"Markers {START} / {END} not found in README.md")
    new = pattern.sub(lambda _: f"{START}\n{block}\n{END}", text_)
    if new != text_:
        with open(README, "w", encoding="utf-8") as f:
            f.write(new)
    return new != text_


def build(viewer):
    s = summarize(viewer)
    cards = [("stats", stats_svg(s)), ("streak", streak_svg(s)), ("langs", langs_svg(s))]
    names, blocks = [], []
    for stem, svg in cards:
        name = write_asset(stem, svg)
        label = re.search(r'aria-label="([^"]*)"', svg).group(1)
        names.append(name)
        blocks.append(img(name, label.replace("&quot;", '"')))
    prune_assets(set(names))
    changed = patch_readme("\n\n".join(blocks))
    print("README updated." if changed else "No change.", " ".join(names))
    return s


def main():
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_STATS_TOKEN")
    if not token:
        sys.exit("GITHUB_TOKEN / GH_STATS_TOKEN not set; nothing changed.")
    try:
        payload = gql(token)
    except Exception as e:
        sys.exit(f"API request failed ({e}); nothing changed.")

    viewer = (payload.get("data") or {}).get("viewer")
    if payload.get("errors") or not viewer:
        sys.exit(f"GraphQL error: {payload.get('errors') or 'empty response'}; nothing changed.")
    build(viewer)


if __name__ == "__main__":
    main()
