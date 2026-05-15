#!/usr/bin/env python3
"""
GitHub Profile Stats SVG Generator
Uses GitHub GraphQL API (GITHUB_TOKEN) to generate self-contained SVGs.
"""

import os
import sys
import json
import urllib.request
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
    print("  ->", path)


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
            '<circle cx="' + str(x + 8) + '" cy="' + str(y - 4) + '" r="5" fill="' + color + '"/>'
            '<text x="' + str(x + 22) + '" y="' + str(y) + '" fill="' + T["text"] + '" font-size="14" font-family="Segoe UI,Ubuntu,sans-serif">' + label + ':</text>'
            '<text x="' + str(x + 22 + 115) + '" y="' + str(y) + '" fill="' + T["bright"] + '" font-size="14" font-weight="600" font-family="Segoe UI,Ubuntu,sans-serif">' + str(value) + '</text>'
        )

    parts = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="495" height="195" viewBox="0 0 495 195">',
        '  <rect fill="' + T["card"] + '" x="0.5" y="0.5" width="494" height="194" rx="6" stroke="' + T["border"] + '" stroke-width="1"/>',
        '  <text x="15" y="35" fill="' + T["blue"] + '" font-size="18" font-weight="600" font-family="Segoe UI,Ubuntu,sans-serif">GitHub Stats</text>',
        '  ' + ''.join(rows),
        '</svg>',
    ]
    return '\n'.join(parts)


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
            '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="100">\n'
            '  <rect fill="' + T["card"] + '" width="300" height="100" rx="6"/>\n'
            '  <text x="150" y="55" text-anchor="middle" fill="' + T["text"] + '" font-size="14" font-family="sans-serif">No language data</text>\n'
            '</svg>'
        )

    total = sum(lang_bytes.values())
    items = sorted(lang_bytes.items(), key=lambda x: x[1], reverse=True)[:8]
    y = 65
    parts = []
    for name, size in items:
        pct = size / total * 100
        c = lang_color.get(name, T["text"])
        parts.append(
            '<text x="15" y="' + str(y) + '" fill="' + T["bright"] + '" font-size="14" font-weight="600" font-family="Segoe UI,sans-serif">' + name + '</text>'
            '<text x="280" y="' + str(y) + '" text-anchor="end" fill="' + T["text"] + '" font-size="14" font-family="Segoe UI,sans-serif">' + ("%.1f" % pct) + '%</text>'
            '<rect x="15" y="' + str(y + 10) + '" width="250" height="8" rx="4" fill="' + T["border"] + '"/>'
            '<rect x="15" y="' + str(y + 10) + '" width="' + str(250 * pct / 100) + '" height="8" rx="4" fill="' + c + '"/>'
        )
        y += 42

    h = y + 15
    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="' + str(h) + '" viewBox="0 0 300 ' + str(h) + '">',
        '  <rect fill="' + T["card"] + '" x="0.5" y="0.5" width="299" height="' + str(h - 1) + '" rx="6" stroke="' + T["border"] + '" stroke-width="1"/>',
        '  <text x="15" y="35" fill="' + T["blue"] + '" font-size="18" font-weight="600" font-family="Segoe UI,Ubuntu,sans-serif">Top Languages</text>',
        '  ' + ''.join(parts),
        '</svg>',
    ]
    return '\n'.join(lines)


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
            cells.append('<rect x="' + str(x) + '" y="' + str(y) + '" width="' + str(cell) + '" height="' + str(cell) + '" rx="2" fill="' + fill + '"/>')

    legend = (
        '<text x="' + str(ml) + '" y="' + str(h - 15) + '" fill="' + T["text"] + '" font-size="11" font-family="sans-serif">Less</text>'
        '<rect x="' + str(ml + 35) + '" y="' + str(h - 24) + '" width="10" height="10" rx="2" fill="' + T["border"] + '"/>'
        '<rect x="' + str(ml + 50) + '" y="' + str(h - 24) + '" width="10" height="10" rx="2" fill="#0e4429"/>'
        '<rect x="' + str(ml + 65) + '" y="' + str(h - 24) + '" width="10" height="10" rx="2" fill="#006d32"/>'
        '<rect x="' + str(ml + 80) + '" y="' + str(h - 24) + '" width="10" height="10" rx="2" fill="#26a641"/>'
        '<rect x="' + str(ml + 95) + '" y="' + str(h - 24) + '" width="10" height="10" rx="2" fill="#39d353"/>'
        '<text x="' + str(ml + 115) + '" y="' + str(h - 15) + '" fill="' + T["text"] + '" font-size="11" font-family="sans-serif">More</text>'
    )

    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="' + str(w) + '" height="' + str(h) + '" viewBox="0 0 ' + str(w) + ' ' + str(h) + '">',
        '  <rect fill="' + T["bg"] + '" width="' + str(w) + '" height="' + str(h) + '" rx="6"/>',
        '  <text x="15" y="30" fill="' + T["blue"] + '" font-size="16" font-weight="600" font-family="Segoe UI,Ubuntu,sans-serif">Contribution Activity</text>',
        '  ' + ''.join(cells),
        '  ' + legend,
        '</svg>',
    ]
    return '\n'.join(lines)


def streak_svg(data):
    weeks = data["contributionsCollection"]["contributionCalendar"]["weeks"]
    cur, longest = streaks(weeks)
    total = data["contributionsCollection"]["contributionCalendar"]["totalContributions"]

    def block(cx, label, value, color):
        return (
            '<text x="' + str(cx) + '" y="80" text-anchor="middle" fill="' + T["text"] + '" font-size="14" font-family="Segoe UI,sans-serif">' + label + '</text>'
            '<text x="' + str(cx) + '" y="125" text-anchor="middle" fill="' + color + '" font-size="34" font-weight="700" font-family="Segoe UI,sans-serif">' + str(value) + '</text>'
        )

    b1 = block(124, "Total Contributions", f"{total:,}", T["green"])
    b2 = block(248, "Current Streak", cur, T["orange"] if cur > 0 else T["text"])
    b3 = block(372, "Longest Streak", longest, T["purple"])

    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="495" height="195" viewBox="0 0 495 195">',
        '  <rect fill="' + T["card"] + '" x="0.5" y="0.5" width="494" height="194" rx="6" stroke="' + T["border"] + '" stroke-width="1"/>',
        '  <text x="15" y="35" fill="' + T["blue"] + '" font-size="18" font-weight="600" font-family="Segoe UI,Ubuntu,sans-serif">GitHub Streak</text>',
        '  ' + b1 + b2 + b3,
        '</svg>',
    ]
    return '\n'.join(lines)


def trophies_svg(data):
    repos = data["repositories"]["totalCount"]
    stars = sum(r["stargazerCount"] for r in data["repositories"]["nodes"])
    forks = sum(r["forkCount"] for r in data["repositories"]["nodes"])
    followers = data["followers"]["totalCount"]
    contrib = data["contributionsCollection"]["contributionCalendar"]["totalContributions"]

    ach = []
    if stars >= 100:
        ach.append(("Starstruck", str(stars) + " Stars", T["yellow"]))
    if contrib >= 1000:
        ach.append(("Committer", f"{contrib:,}", T["green"]))
    if repos >= 20:
        ach.append(("Creator", str(repos) + " Repos", T["blue"]))
    if followers >= 50:
        ach.append(("Influencer", str(followers) + " Followers", T["red"]))
    if forks >= 20:
        ach.append(("Forker", str(forks) + " Forks", T["purple"]))
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
            '<rect x="' + str(x) + '" y="' + str(y) + '" width="' + str(bw) + '" height="' + str(bh) + '" rx="8" fill="' + T["card"] + '" stroke="' + color + '" stroke-width="2"/>'
            '<text x="' + str(x + bw / 2) + '" y="' + str(y + 22) + '" text-anchor="middle" fill="' + color + '" font-size="13" font-weight="600" font-family="Segoe UI,sans-serif">' + title + '</text>'
            '<text x="' + str(x + bw / 2) + '" y="' + str(y + 40) + '" text-anchor="middle" fill="' + T["text"] + '" font-size="11" font-family="Segoe UI,sans-serif">' + sub + '</text>'
        )

    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="' + str(tw) + '" height="' + str(th) + '" viewBox="0 0 ' + str(tw) + ' ' + str(th) + '">',
        '  <rect fill="' + T["bg"] + '" width="' + str(tw) + '" height="' + str(th) + '" rx="6"/>',
        '  <text x="15" y="22" fill="' + T["blue"] + '" font-size="16" font-weight="600" font-family="Segoe UI,Ubuntu,sans-serif">Achievements</text>',
        '  ' + ''.join(badges),
        '</svg>',
    ]
    return '\n'.join(lines)


def fallback():
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="100">\n'
        '  <rect fill="' + T["card"] + '" width="400" height="100" rx="6"/>\n'
        '  <text x="200" y="55" text-anchor="middle" fill="' + T["red"] + '" font-size="14" font-family="sans-serif">Stats temporarily unavailable</text>\n'
        '</svg>'
    )
    for n in ["stats", "streak", "top-langs", "activity", "trophies"]:
        save("assets/" + n + ".svg", svg)


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
