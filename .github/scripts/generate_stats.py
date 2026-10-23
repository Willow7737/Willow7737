#!/usr/bin/env python3
"""
GitHub profile stats card generator.

Flat, opaque, crisp SVG cards (no blur filters, no translucency) sized to
render 1:1 inside the GitHub README column so nothing gets scaled or smeared.
Uses the GitHub GraphQL API. Standard library only.

On any API failure the existing assets are left untouched and the script exits
non-zero, so a transient error never overwrites good cards with an error image.
"""

import json
import os
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from xml.sax.saxutils import escape

ASSETS = os.path.join(os.path.dirname(__file__), "..", "..", "assets")

# Palette (Tokyo Night, flat)
BG = "#1a1b26"
BORDER = "#2f334d"
TRACK = "#2a2e45"
TEXT = "#a9b1d6"
BRIGHT = "#c0caf5"
MUTED = "#565f89"
BLUE = "#7aa2f7"
GREEN = "#9ece6a"
ORANGE = "#ff9e64"
PURPLE = "#bb9af7"

FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"

# Two cards sit side by side: 2 * 400 + 16 gap = 816, inside the ~830px README column.
CARD_W = 400
CARD_H = 180

GRAPHQL = "https://api.github.com/graphql"
QUERY = """
query {
  viewer {
    login
    followers { totalCount }
    repositories(first: 100, ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays { contributionCount date }
        }
      }
    }
  }
}
"""


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


def streaks(weeks):
    days = sorted(
        (
            {"date": d["date"], "count": d["contributionCount"]}
            for w in weeks
            for d in w["contributionDays"]
        ),
        key=lambda d: d["date"],
    )
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    cur = 0
    for d in reversed(days):
        if d["date"] > today:
            continue
        if d["date"] == today and d["count"] == 0:
            continue  # today isn't over yet; don't break the streak
        if d["count"] > 0:
            cur += 1
        else:
            break

    longest = run = 0
    for d in days:
        run = run + 1 if d["count"] > 0 else 0
        longest = max(longest, run)
    return cur, longest


def svg(w, h, body):
    # No timestamp comment: identical data must produce identical bytes,
    # otherwise the workflow commits a no-op change every run.
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" shape-rendering="geometricPrecision" '
        f'text-rendering="optimizeLegibility" role="img">\n'
        f'  <rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="10" '
        f'fill="{BG}" stroke="{BORDER}"/>\n'
        f"{body}\n</svg>\n"
    )


def text(x, y, s, size=13, fill=TEXT, weight=400, anchor="start"):
    return (
        f'  <text x="{x}" y="{y}" fill="{fill}" font-size="{size}" '
        f'font-weight="{weight}" text-anchor="{anchor}" '
        f'font-family="{FONT}">{escape(str(s))}</text>'
    )


def title(s, accent):
    return (
        f'  <rect x="24" y="24" width="3" height="16" rx="1.5" fill="{accent}"/>\n'
        + text(36, 37, s, size=15, fill=BRIGHT, weight=600)
    )


def save(name, content):
    os.makedirs(ASSETS, exist_ok=True)
    path = os.path.join(ASSETS, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("  ->", os.path.normpath(path))


def stats_svg(v):
    repos = v["repositories"]["totalCount"]
    stars = sum(r["stargazerCount"] for r in v["repositories"]["nodes"])
    followers = v["followers"]["totalCount"]
    contrib = v["contributionsCollection"]["contributionCalendar"]["totalContributions"]

    items = [
        ("Public repositories", repos, BLUE),
        ("Stars earned", stars, ORANGE),
        ("Followers", followers, PURPLE),
        ("Contributions, last year", f"{contrib:,}", GREEN),
    ]
    parts = [title("GitHub", BLUE)]
    for i, (label, value, color) in enumerate(items):
        col, row = i % 2, i // 2
        x = 24 + col * 180
        y = 80 + row * 52
        parts.append(text(x, y, value, size=24, fill=color, weight=700))
        parts.append(text(x, y + 20, label, size=12, fill=MUTED))
    return svg(CARD_W, CARD_H, "\n".join(parts))


def streak_svg(v):
    cal = v["contributionsCollection"]["contributionCalendar"]
    cur, longest = streaks(cal["weeks"])
    total = cal["totalContributions"]

    cols = [
        (f"{total:,}", "Past year", GREEN),
        (cur, "Current streak", ORANGE),
        (longest, "Longest streak", PURPLE),
    ]
    parts = [title("Consistency", ORANGE)]
    col_w = (CARD_W - 48) / 3
    for i, (value, label, color) in enumerate(cols):
        cx = 24 + col_w * i + col_w / 2
        parts.append(text(f"{cx:.1f}", 100, value, size=28, fill=color, weight=700, anchor="middle"))
        parts.append(text(f"{cx:.1f}", 124, label, size=11, fill=MUTED, anchor="middle"))
        if i:
            lx = 24 + col_w * i
            parts.append(f'  <line x1="{lx:.1f}" y1="78" x2="{lx:.1f}" y2="130" stroke="{BORDER}"/>')
    return svg(CARD_W, CARD_H, "\n".join(parts))


def langs_svg(v):
    size_by, color_by = defaultdict(int), {}
    for repo in v["repositories"]["nodes"]:
        for e in repo["languages"]["edges"]:
            n = e["node"]["name"]
            size_by[n] += e["size"]
            color_by.setdefault(n, e["node"]["color"] or MUTED)

    w, h = 816, 110
    parts = [title("Languages", PURPLE)]
    if not size_by:
        parts.append(text(24, 76, "No language data yet", fill=MUTED))
        return svg(w, h, "\n".join(parts))

    total = sum(size_by.values())
    top = sorted(size_by.items(), key=lambda kv: kv[1], reverse=True)[:6]
    other = total - sum(s for _, s in top)

    # One stacked bar, clipped to rounded ends.
    bar_x, bar_y, bar_w, bar_h = 24, 54, w - 48, 8
    parts.append(
        f'  <clipPath id="bar"><rect x="{bar_x}" y="{bar_y}" width="{bar_w}" '
        f'height="{bar_h}" rx="4"/></clipPath>\n'
        f'  <g clip-path="url(#bar)">\n'
        f'    <rect x="{bar_x}" y="{bar_y}" width="{bar_w}" height="{bar_h}" fill="{TRACK}"/>'
    )
    x = bar_x
    for name, s in top:
        seg = bar_w * s / total
        parts.append(f'    <rect x="{x:.2f}" y="{bar_y}" width="{seg:.2f}" height="{bar_h}" fill="{color_by[name]}"/>')
        x += seg
    parts.append("  </g>")

    # Legend: one row of name + percent.
    legend = [(n, s, color_by[n]) for n, s in top]
    if other > 0:
        legend.append(("Other", other, MUTED))
    slot = (w - 48) / len(legend)
    for i, (name, s, color) in enumerate(legend):
        lx = 24 + slot * i
        parts.append(f'  <circle cx="{lx + 4:.1f}" cy="87" r="4" fill="{color}"/>')
        parts.append(text(f"{lx + 14:.1f}", 91, name, size=12, fill=BRIGHT, weight=600))
        parts.append(text(f"{lx + 14:.1f}", 106, f"{s / total * 100:.1f}%", size=11, fill=MUTED))
    return svg(w, h + 8, "\n".join(parts))


def activity_svg(v):
    weeks = v["contributionsCollection"]["contributionCalendar"]["weeks"][-53:]
    cell, gap = 11, 3
    ml, mt = 24, 56
    w = 816
    h = mt + 7 * (cell + gap) + 40

    counts = [d["contributionCount"] for wk in weeks for d in wk["contributionDays"]]
    peak = max(counts) if counts else 0
    levels = ["#22263b", "#2d4a3e", "#3f7a52", "#6ba84f", GREEN]

    def level(n):
        if n <= 0 or peak == 0:
            return levels[0]
        return levels[min(4, 1 + int(3 * (n - 1) / max(peak, 1)))]

    grid_w = len(weeks) * (cell + gap) - gap
    ox = ml + max(0, (w - 2 * ml - grid_w) / 2)
    parts = [title("Activity", GREEN)]
    for ci, wk in enumerate(weeks):
        for ri, d in enumerate(wk["contributionDays"]):
            x = ox + ci * (cell + gap)
            y = mt + ri * (cell + gap)
            parts.append(
                f'  <rect x="{x:.0f}" y="{y}" width="{cell}" height="{cell}" rx="2" '
                f'fill="{level(d["contributionCount"])}"/>'
            )

    ly = h - 20
    lx = w - 24 - (len(levels) * 14 + 70)
    parts.append(text(lx, ly + 9, "Less", size=11, fill=MUTED))
    for i, c in enumerate(levels):
        parts.append(f'  <rect x="{lx + 32 + i * 14}" y="{ly}" width="11" height="11" rx="2" fill="{c}"/>')
    parts.append(text(lx + 32 + len(levels) * 14 + 4, ly + 9, "More", size=11, fill=MUTED))
    return svg(w, h, "\n".join(parts))


def main():
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_STATS_TOKEN")
    if not token:
        sys.exit("GITHUB_TOKEN / GH_STATS_TOKEN not set; leaving existing assets untouched.")

    try:
        payload = gql(token)
    except Exception as e:  # network / HTTP failure
        sys.exit(f"API request failed ({e}); leaving existing assets untouched.")

    viewer = (payload.get("data") or {}).get("viewer")
    if payload.get("errors") or not viewer:
        sys.exit(f"GraphQL error: {payload.get('errors') or 'empty response'}; leaving existing assets untouched.")

    save("stats.svg", stats_svg(viewer))
    save("streak.svg", streak_svg(viewer))
    save("top-langs.svg", langs_svg(viewer))
    save("activity.svg", activity_svg(viewer))
    print("Done.")


if __name__ == "__main__":
    main()
