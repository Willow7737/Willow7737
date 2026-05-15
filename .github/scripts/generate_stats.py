#!/usr/bin/env python3
"""
GitHub Profile Stats SVG Generator
Uses GitHub GraphQL API (GITHUB_TOKEN) to generate self-contained SVGs.
Zero external services. Zero rate-limit issues.
"""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime
from collections import defaultdict

# ─── Tokyo Night Theme ───
T = {
    "bg": "#1a1b26",
    "card": "#1f2335",
    "border": "#292e42",
    "text": "#a9b1d6",
    "bright": "#c0caf5",
    "blue": "#7aa2f7",
    "cyan": "#7dcfff",
    "green": "#9ece6a",
    "purple": "#bb9af7",
    "red": "#f7768e",
    "yellow": "#e0af68",
    "orange": "#ff9e64",
}

GRAPHQL = "https://api.github.com/graphql"
QUERY = """
query {
  viewer {
    login
    followers { totalCount }
    following { totalCount }
    repositories(first: 100, ownerAffiliations: OWNER, privacy: PUBLIC) {
      totalCount
      nodes {
        name
        stargazerCount
        forkCount
        primaryLanguage { name color }
        languages(first: 10) {
          edges { size node { name color } }
        }
      }
    }
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            contributionCount
            date
            color
          }
        }
      }
    }
  }
}
"""


def gql(token):
    payload = json.dumps({"query": QUERY}).encode()
    req = urllib.request.Request(
        GRAPHQL,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "github-stats-gen",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def streaks(weeks):
    days = []
    for w in weeks:
        for d in w["contributionDays"]:
            days.append({"date": d["date"], "count": d["contributionCount"]})
    days.sort(key=lambda x: x["date"])
    today = datetime.now().strftime("%Y-%m-%d")

    cur = 0
    for d in reversed(days):
        if d["date"] == today and d["count"] == 0:
            continue
        if d["count"] > 0:
            cur += 1
        else:
            break

    longest = temp = 0
    for d in days:
        if d["count"] > 0:
            temp += 1
            longest = max(longest, temp)
        else:
            temp = 0
    return cur, longest


def save(path, svg):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg)
    print("  →", path)


def stats_svg(data):
    repos = data["repositories"]["totalCount"]
    stars = sum(r["stargazerCount"] for r in data["repositories"]["nodes"])
    forks = sum(r["forkCount"] for r in data["repositories"]["nodes"])
    followers = data["followers"]["totalCount"]
    following = data["following"]["totalCount"]
    contrib = data["contributionsCollection"]["contributionCalendar"]["totalContributions"]

    stats = [
        ("Repositories", repos, T["blue"]),
        ("Total Stars", stars, T["yellow"]),
        ("Total Forks", forks, T["purple"]),
        ("Contributions", f"{contrib:,}", T["green"]),
        ("Followers", followers, T["red"]),
        ("Following", following, T["cyan"]),
    ]

    rows = []
    for i, (label, value, color) in enumerate(stats):
        col = i % 2
        row = i // 2
        x = 15 + col * 240
        y = 70 + row * 42
        rows.append(
            f'<circle cx="{x+8}" cy="{y-4}" r="5" fill="{color}"/>'
            f'<text x="{x+22}" y="{y}" fill="{T["text"]}" font-size="14" font-family="Segoe UI,Ubuntu,sans-serif">{label}:</text>'
            f'<text x="{x+22+115}" y="{y}" fill="{T["bright"]}" font-size="14" font-weight="600" font-family="Segoe UI,Ubuntu,sans-serif">{value}</text>'
        )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="495" height="195" viewBox="0 0 495 195">
'
        f'  <rect fill="{T["card"]}" x="0.5" y="0.5" width="494" height="194" rx="6" stroke="{T["border"]}" stroke-width="1"/>
'
        f'  <text x="15" y="35" fill="{T["blue"]}" font-size="18" font-weight="600" font-family="Segoe UI,Ubuntu,sans-serif">GitHub Stats</text>
'
        f'  {"".join(rows)}
'
        f'</svg>'
    )


def langs_svg(data):
    lang_bytes = defaultdict(int)
    lang_color = {}
    for repo in data["repositories"]["nodes"]:
        for e in repo.get("languages", {}).get("edges", []):
            n = e["node"]["name"]
            lang_bytes[n] += e["size"]
            if n not in lang_color:
                lang_color[n] = e["node"]["color"] or T["text"]

    if not lang_bytes:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="300" height="100">
'
            f'  <rect fill="{T["card"]}" width="300" height="100" rx="6"/>
'
            f'  <text x="150" y="55" text-anchor="middle" fill="{T["text"]}" font-size="14" font-family="sans-serif">No language data</text>
'
            f'</svg>'
        )

    total = sum(lang_bytes.values())
    items = sorted(lang_bytes.items(), key=lambda x: x[1], reverse=True)[:8]
    y = 65
    parts = []
    for name, size in items:
        pct = size / total * 100
        c = lang_color.get(name, T["text"])
        parts.append(
            f'<text x="15" y="{y}" fill="{T["bright"]}" font-size="14" font-weight="600" font-family="Segoe UI,sans-serif">{name}</text>'
            f'<text x="280" y="{y}" text-anchor="end" fill="{T["text"]}" font-size="14" font-family="Segoe UI,sans-serif">{pct:.1f}%</text>'
            f'<rect x="15" y="{y+10}" width="250" height="8" rx="4" fill="{T["border"]}"/>'
            f'<rect x="15" y="{y+10}" width="{250*pct/100:.1f}" height="8" rx="4" fill="{c}"/>'
        )
        y += 42

    h = y + 15
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="300" height="{h}" viewBox="0 0 300 {h}">
'
        f'  <rect fill="{T["card"]}" x="0.5" y="0.5" width="299" height="{h-1}" rx="6" stroke="{T["border"]}" stroke-width="1"/>
'
        f'  <text x="15" y="35" fill="{T["blue"]}" font-size="18" font-weight="600" font-family="Segoe UI,Ubuntu,sans-serif">Top Languages</text>
'
        f'  {"".join(parts)}
'
        f'</svg>'
    )


def activity_svg(data):
    weeks = data["contributionsCollection"]["contributionCalendar"]["weeks"]
    weeks = weeks[-53:] if len(weeks) > 53 else weeks
    cell, gap = 10, 3
    ml, mt = 15, 50
    cols = len(weeks)
    w = ml + cols * (cell + gap) + gap + 15
    h = mt + 7 * (cell + gap) + gap + 35

    cells = []
    for ci, week in enumerate(weeks):
        for ri, day in enumerate(week["contributionDays"]):
            x = ml + ci * (cell + gap)
            y = mt + ri * (cell + gap)
            fill = day["color"] if day["contributionCount"] > 0 else T["border"]
            cells.append(f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="2" fill="{fill}"/>')

    legend = (
        f'<text x="{ml}" y="{h-15}" fill="{T["text"]}" font-size="11" font-family="sans-serif">Less</text>'
        f'<rect x="{ml+35}" y="{h-24}" width="10" height="10" rx="2" fill="{T["border"]}"/>'
        f'<rect x="{ml+50}" y="{h-24}" width="10" height="10" rx="2" fill="#0e4429"/>'
        f'<rect x="{ml+65}" y="{h-24}" width="10" height="10" rx="2" fill="#006d32"/>'
        f'<rect x="{ml+80}" y="{h-24}" width="10" height="10" rx="2" fill="#26a641"/>'
        f'<rect x="{ml+95}" y="{h-24}" width="10" height="10" rx="2" fill="#39d353"/>'
        f'<text x="{ml+115}" y="{h-15}" fill="{T["text"]}" font-size="11" font-family="sans-serif">More</text>'
    )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
'
        f'  <rect fill="{T["bg"]}" width="{w}" height="{h}" rx="6"/>
'
        f'  <text x="15" y="30" fill="{T["blue"]}" font-size="16" font-weight="600" font-family="Segoe UI,Ubuntu,sans-serif">Contribution Activity</text>
'
        f'  {"".join(cells)}
'
        f'  {legend}
'
        f'</svg>'
    )


def streak_svg(data):
    weeks = data["contributionsCollection"]["contributionCalendar"]["weeks"]
    cur, longest = streaks(weeks)
    total = data["contributionsCollection"]["contributionCalendar"]["totalContributions"]

    def block(cx, label, value, color):
        return (
            f'<text x="{cx}" y="{80}" text-anchor="middle" fill="{T["text"]}" font-size="14" font-family="Segoe UI,sans-serif">{label}</text>'
            f'<text x="{cx}" y="{125}" text-anchor="middle" fill="{color}" font-size="34" font-weight="700" font-family="Segoe UI,sans-serif">{value}</text>'
        )

    b1 = block(124, "Total Contributions", f"{total:,}", T["green"])
    b2 = block(248, "Current Streak", cur, T["orange"] if cur > 0 else T["text"])
    b3 = block(372, "Longest Streak", longest, T["purple"])

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="495" height="195" viewBox="0 0 495 195">
'
        f'  <rect fill="{T["card"]}" x="0.5" y="0.5" width="494" height="194" rx="6" stroke="{T["border"]}" stroke-width="1"/>
'
        f'  <text x="15" y="35" fill="{T["blue"]}" font-size="18" font-weight="600" font-family="Segoe UI,Ubuntu,sans-serif">GitHub Streak</text>
'
        f'  {b1}{b2}{b3}
'
        f'</svg>'
    )


def trophies_svg(data):
    repos = data["repositories"]["totalCount"]
    stars = sum(r["stargazerCount"] for r in data["repositories"]["nodes"])
    forks = sum(r["forkCount"] for r in data["repositories"]["nodes"])
    followers = data["followers"]["totalCount"]
    contrib = data["contributionsCollection"]["contributionCalendar"]["totalContributions"]

    ach = []
    if stars >= 100:
        ach.append(("Starstruck", f"{stars} Stars", T["yellow"]))
    if contrib >= 1000:
        ach.append(("Committer", f"{contrib:,}", T["green"]))
    if repos >= 20:
        ach.append(("Creator", f"{repos} Repos", T["blue"]))
    if followers >= 50:
        ach.append(("Influencer", f"{followers} Followers", T["red"]))
    if forks >= 20:
        ach.append(("Forker", f"{forks} Forks", T["purple"]))
    if len(ach) < 3:
        ach.append(("Developer", "Building...", T["cyan"]))

    bw, bh, gap = 130, 52, 10
    tw = len(ach) * (bw + gap) + gap
    th = 100

    badges = []
    for i, (title, sub, color) in enumerate(ach):
        x = gap + i * (bw + gap)
        y = 32
        badges.append(
            f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="8" fill="{T["card"]}" stroke="{color}" stroke-width="2"/>'
            f'<text x="{x+bw/2}" y="{y+22}" text-anchor="middle" fill="{color}" font-size="13" font-weight="600" font-family="Segoe UI,sans-serif">{title}</text>'
            f'<text x="{x+bw/2}" y="{y+40}" text-anchor="middle" fill="{T["text"]}" font-size="11" font-family="Segoe UI,sans-serif">{sub}</text>'
        )

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{tw}" height="{th}" viewBox="0 0 {tw} {th}">
'
        f'  <rect fill="{T["bg"]}" width="{tw}" height="{th}" rx="6"/>
'
        f'  <text x="15" y="22" fill="{T["blue"]}" font-size="16" font-weight="600" font-family="Segoe UI,Ubuntu,sans-serif">Achievements</text>
'
        f'  {"".join(badges)}
'
        f'</svg>'
    )


def fallback():
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="400" height="100">
'
        f'  <rect fill="{T["card"]}" width="400" height="100" rx="6"/>
'
        f'  <text x="200" y="55" text-anchor="middle" fill="{T["red"]}" font-size="14" font-family="sans-serif">Stats temporarily unavailable</text>
'
        f'</svg>'
    )
    for n in ["stats", "streak", "top-langs", "activity", "trophies"]:
        save(f"assets/{n}.svg", svg)


def main():
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_STATS_TOKEN")
    if not token:
        print("Error: GITHUB_TOKEN not set", file=sys.stderr)
        sys.exit(1)

    try:
        data = gql(token)
        if "errors" in data:
            raise Exception(data["errors"])
        data = data["data"]["viewer"]
    except Exception as e:
        print(f"API Error: {e}", file=sys.stderr)
        fallback()
        sys.exit(0)

    save("assets/stats.svg", stats_svg(data))
    save("assets/top-langs.svg", langs_svg(data))
    save("assets/activity.svg", activity_svg(data))
    save("assets/streak.svg", streak_svg(data))
    save("assets/trophies.svg", trophies_svg(data))
    print("Done.")


if __name__ == "__main__":
    main()
