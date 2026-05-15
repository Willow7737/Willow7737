#!/usr/bin/env python3
"""
GitHub Profile Stats SVG Generator — ASTOUNDING EDITION
Glassmorphism, neon glows, embedded icons, animated shimmer.
Uses GitHub GraphQL API. Zero external dependencies for rendered assets.
"""

import os
import sys
import json
import urllib.request
from datetime import datetime
from collections import defaultdict

T = {
    "bg": "#1a1b26", "bg2": "#16161e", "card": "#1f2335",
    "border": "#414868", "border_neon": "#7aa2f7",
    "text": "#a9b1d6", "bright": "#c0caf5",
    "blue": "#7aa2f7", "cyan": "#7dcfff", "green": "#9ece6a",
    "purple": "#bb9af7", "red": "#f7768e", "yellow": "#e0af68",
    "orange": "#ff9e64", "pink": "#ff007f",
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

ICONS = {
    "repo": "M2 2.5A2.5 2.5 0 014.5 0h8.75a.75.75 0 01.75.75v12.5a.75.75 0 01-.75.75h-2.5a.75.75 0 110-1.5h1.75v-2h-8v2h1.75a.75.75 0 110 1.5h-2.5a.75.75 0 01-.75-.75V3.5a.75.75 0 01.75-.75zM4.5 1.5a1 1 0 00-1 1v10.5h8V2.5a1 1 0 00-1-1h-6z",
    "star": "M8 .25a.75.75 0 01.673.418l1.882 3.815 4.21.612a.75.75 0 01.416 1.279l-3.046 2.97.719 4.192a.75.75 0 01-1.088.791L8 12.347l-3.766 1.98a.75.75 0 01-1.088-.79l.72-4.194L.818 6.374a.75.75 0 01.416-1.28l4.21-.611L7.327.668A.75.75 0 018 .25z",
    "fork": "M5 3.25a1.75 1.75 0 11-3.5 0 1.75 1.75 0 013.5 0zm0 9.5a1.75 1.75 0 11-3.5 0 1.75 1.75 0 013.5 0zm7.5-5a1.75 1.75 0 11-3.5 0 1.75 1.75 0 013.5 0zM6.5 3.25a.75.75 0 01.75-.75h1a.75.75 0 010 1.5h-1a.75.75 0 01-.75-.75zM6.5 9.5a.75.75 0 01.75-.75h1a.75.75 0 010 1.5h-1a.75.75 0 01-.75-.75zm.75-3a.75.75 0 000 1.5h1a.75.75 0 000-1.5h-1z",
    "users": "M4.243 4.757a3.757 3.757 0 117.514 0 3.757 3.757 0 01-7.514 0zm-2.25 7.5a2.25 2.25 0 012.25-2.25h9a2.25 2.25 0 012.25 2.25v.75a.75.75 0 01-.75.75h-12a.75.75 0 01-.75-.75v-.75z",
    "flame": "M8 16c4.418 0 8-3.582 8-8 0-4.418-3.582-8-8-8-4.418 0-8 3.582-8 8 0 4.418 3.582 8 8 8zm.75-11.25a.75.75 0 00-1.5 0v1.5a.75.75 0 001.5 0v-1.5zM8 4a4 4 0 00-4 4 .75.75 0 001.5 0 2.5 2.5 0 015 0 .75.75 0 001.5 0 4 4 0 00-4-4z",
    "commit": "M11.93 8.5a4.002 4.002 0 01-7.86 0H.75a.75.75 0 010-1.5h3.32a4.002 4.002 0 017.86 0h3.32a.75.75 0 010 1.5zm-1.43-.75a2.5 2.5 0 10-5 0 2.5 2.5 0 005 0z",
}


def gql(token):
    payload = json.dumps({"query": QUERY}).encode()
    req = urllib.request.Request(
        GRAPHQL,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "github-stats-astounding",
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


def wrap_svg(content, w, h, extra_defs=""):
    ts = datetime.utcnow().isoformat()
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<!-- Generated: {ts} -->\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">\n'
        f'  <defs>\n'
        f'    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">\n'
        f'      <stop offset="0%" stop-color="{T["bg2"]}"/>\n'
        f'      <stop offset="100%" stop-color="{T["bg"]}"/>\n'
        f'    </linearGradient>\n'
        f'    <linearGradient id="neonBlue" x1="0%" y1="0%" x2="100%" y2="0%">\n'
        f'      <stop offset="0%" stop-color="{T["blue"]}"/>\n'
        f'      <stop offset="100%" stop-color="{T["cyan"]}"/>\n'
        f'    </linearGradient>\n'
        f'    <linearGradient id="neonPurple" x1="0%" y1="0%" x2="100%" y2="0%">\n'
        f'      <stop offset="0%" stop-color="{T["purple"]}"/>\n'
        f'      <stop offset="100%" stop-color="{T["pink"]}"/>\n'
        f'    </linearGradient>\n'
        f'    <linearGradient id="neonGreen" x1="0%" y1="0%" x2="100%" y2="0%">\n'
        f'      <stop offset="0%" stop-color="{T["green"]}"/>\n'
        f'      <stop offset="100%" stop-color="{T["cyan"]}"/>\n'
        f'    </linearGradient>\n'
        f'    <linearGradient id="neonOrange" x1="0%" y1="0%" x2="100%" y2="0%">\n'
        f'      <stop offset="0%" stop-color="{T["orange"]}"/>\n'
        f'      <stop offset="100%" stop-color="{T["yellow"]}"/>\n'
        f'    </linearGradient>\n'
        f'    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">\n'
        f'      <feGaussianBlur stdDeviation="3" result="blur"/>\n'
        f'      <feComposite in="SourceGraphic" in2="blur" operator="over"/>\n'
        f'    </filter>\n'
        f'    <filter id="cardShadow" x="-5%" y="-5%" width="110%" height="110%">\n'
        f'      <feDropShadow dx="0" dy="4" stdDeviation="6" flood-color="#000" flood-opacity="0.4"/>\n'
        f'    </filter>\n'
        f'    {extra_defs}\n'
        f'  </defs>\n'
        f'  <rect width="{w}" height="{h}" rx="12" fill="url(#bgGrad)"/>\n'
        f'  {content}\n'
        f'</svg>'
    )


def icon(name, x, y, size, color):
    d = ICONS.get(name, "")
    if not d:
        return ""
    s = size / 16
    return f'<g transform="translate({x},{y}) scale({s})"><path d="{d}" fill="{color}"/></g>'


def stats_svg(data):
    repos = data["repositories"]["totalCount"]
    stars = sum(r["stargazerCount"] for r in data["repositories"]["nodes"])
    forks = sum(r["forkCount"] for r in data["repositories"]["nodes"])
    followers = data["followers"]["totalCount"]
    following = data["following"]["totalCount"]
    contrib = data["contributionsCollection"]["contributionCalendar"]["totalContributions"]

    stats = [
        ("Repositories", repos, T["blue"], "repo", "neonBlue"),
        ("Total Stars", stars, T["yellow"], "star", "neonOrange"),
        ("Total Forks", forks, T["purple"], "fork", "neonPurple"),
        ("Contributions", f"{contrib:,}", T["green"], "commit", "neonGreen"),
        ("Followers", followers, T["red"], "users", "neonBlue"),
        ("Following", following, T["cyan"], "users", "neonPurple"),
    ]

    rows = []
    for i, (label, value, color, iname, grad) in enumerate(stats):
        col, row = i % 2, i // 2
        x, y = 20 + col * 235, 75 + row * 48
        rows.append(
            f'    <g transform="translate({x},{y})">\n'
            f'      {icon(iname, 0, -12, 18, color)}\n'
            f'      <text x="24" y="0" fill="{T["text"]}" font-size="13" font-family="Segoe UI,Ubuntu,sans-serif">{label}</text>\n'
            f'      <text x="24" y="16" fill="url(#{grad})" font-size="16" font-weight="700" font-family="Segoe UI,Ubuntu,sans-serif" filter="url(#glow)">{value}</text>\n'
            f'    </g>'
        )

    body = (
        f'  <rect x="10" y="10" width="475" height="175" rx="10" fill="{T["card"]}" fill-opacity="0.6" stroke="{T["border"]}" stroke-width="1" filter="url(#cardShadow)"/>\n'
        f'  <text x="30" y="45" fill="url(#neonBlue)" font-size="20" font-weight="700" font-family="Segoe UI,Ubuntu,sans-serif" filter="url(#glow)">GitHub Analytics</text>\n'
        f'  <line x1="30" y1="55" x2="465" y2="55" stroke="{T["border"]}" stroke-width="1"/>\n'
        + '\n'.join(rows)
    )
    return wrap_svg(body, 495, 195)


def langs_svg(data):
    lang_bytes, lang_color = defaultdict(int), {}
    for repo in data["repositories"]["nodes"]:
        for e in repo.get("languages", {}).get("edges", []):
            n = e["node"]["name"]
            lang_bytes[n] += e["size"]
            if n not in lang_color:
                lang_color[n] = e["node"]["color"] or T["text"]

    if not lang_bytes:
        body = (
            f'  <rect x="10" y="10" width="280" height="80" rx="10" fill="{T["card"]}" fill-opacity="0.6" stroke="{T["border"]}" stroke-width="1" filter="url(#cardShadow)"/>\n'
            f'  <text x="150" y="55" text-anchor="middle" fill="{T["text"]}" font-size="14" font-family="sans-serif">No language data</text>'
        )
        return wrap_svg(body, 300, 100)

    total = sum(lang_bytes.values())
    items = sorted(lang_bytes.items(), key=lambda x: x[1], reverse=True)[:8]
    y, parts = 70, []
    for name, size in items:
        pct = size / total * 100
        c = lang_color.get(name, T["text"])
        bar_w = 250 * pct / 100
        parts.append(
            f'    <text x="20" y="{y}" fill="{T["bright"]}" font-size="13" font-weight="600" font-family="Segoe UI,sans-serif">{name}</text>\n'
            f'    <text x="280" y="{y}" text-anchor="end" fill="{T["text"]}" font-size="13" font-family="Segoe UI,sans-serif">{pct:.1f}%</text>\n'
            f'    <rect x="20" y="{y + 8}" width="250" height="7" rx="3.5" fill="{T["border"]}" fill-opacity="0.4"/>\n'
            f'    <rect x="20" y="{y + 8}" width="{bar_w}" height="7" rx="3.5" fill="{c}" filter="url(#glow)">\n'
            f'      <animate attributeName="width" from="0" to="{bar_w}" dur="0.8s" fill="freeze" calcMode="spline" keySplines="0.4 0 0.2 1"/>\n'
            f'    </rect>'
        )
        y += 38

    h = y + 20
    body = (
        f'  <rect x="10" y="10" width="280" height="{h - 20}" rx="10" fill="{T["card"]}" fill-opacity="0.6" stroke="{T["border"]}" stroke-width="1" filter="url(#cardShadow)"/>\n'
        f'  <text x="20" y="40" fill="url(#neonPurple)" font-size="18" font-weight="700" font-family="Segoe UI,Ubuntu,sans-serif" filter="url(#glow)">Top Languages</text>\n'
        f'  <line x1="20" y1="48" x2="270" y2="48" stroke="{T["border"]}" stroke-width="1"/>\n'
        + '\n'.join(parts)
    )
    return wrap_svg(body, 300, h)


def activity_svg(data):
    weeks = data["contributionsCollection"]["contributionCalendar"]["weeks"]
    weeks = weeks[-53:] if len(weeks) > 53 else weeks
    cell, gap = 11, 3
    ml, mt = 20, 55
    cols = len(weeks)
    w = ml + cols * (cell + gap) + gap + 20
    h = mt + 7 * (cell + gap) + gap + 40

    cells = []
    for ci, week in enumerate(weeks):
        for ri, day in enumerate(week["contributionDays"]):
            x = ml + ci * (cell + gap)
            y = mt + ri * (cell + gap)
            fill = day["color"] if day["contributionCount"] > 0 else T["border"]
            opacity = "0.25" if day["contributionCount"] == 0 else "1"
            cells.append(
                f'    <rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3" fill="{fill}" fill-opacity="{opacity}"/>'
            )

    legend = (
        f'    <text x="{ml}" y="{h - 18}" fill="{T["text"]}" font-size="11" font-family="sans-serif">Less</text>\n'
        f'    <rect x="{ml + 35}" y="{h - 27}" width="11" height="11" rx="3" fill="{T["border"]}" fill-opacity="0.4"/>\n'
        f'    <rect x="{ml + 51}" y="{h - 27}" width="11" height="11" rx="3" fill="#0e4429"/>\n'
        f'    <rect x="{ml + 67}" y="{h - 27}" width="11" height="11" rx="3" fill="#006d32"/>\n'
        f'    <rect x="{ml + 83}" y="{h - 27}" width="11" height="11" rx="3" fill="#26a641"/>\n'
        f'    <rect x="{ml + 99}" y="{h - 27}" width="11" height="11" rx="3" fill="#39d353"/>\n'
        f'    <text x="{ml + 120}" y="{h - 18}" fill="{T["text"]}" font-size="11" font-family="sans-serif">More</text>'
    )

    body = (
        f'  <rect x="10" y="10" width="{w - 20}" height="{h - 20}" rx="10" fill="{T["card"]}" fill-opacity="0.6" stroke="{T["border"]}" stroke-width="1" filter="url(#cardShadow)"/>\n'
        f'  <text x="20" y="38" fill="url(#neonGreen)" font-size="16" font-weight="700" font-family="Segoe UI,Ubuntu,sans-serif" filter="url(#glow)">Contribution Activity</text>\n'
        + '\n'.join(cells) + '\n'
        + legend
    )
    return wrap_svg(body, w, h)


def streak_svg(data):
    weeks = data["contributionsCollection"]["contributionCalendar"]["weeks"]
    cur, longest = streaks(weeks)
    total = data["contributionsCollection"]["contributionCalendar"]["totalContributions"]

    def block(cx, label, value, color, grad):
        glow = 'filter="url(#glow)"' if cur > 0 and label == "Current Streak" else ''
        return (
            f'    <g transform="translate({cx}, 0)">\n'
            f'      <text x="0" y="85" text-anchor="middle" fill="{T["text"]}" font-size="12" font-family="Segoe UI,sans-serif">{label}</text>\n'
            f'      <text x="0" y="125" text-anchor="middle" fill="url(#{grad})" font-size="32" font-weight="800" font-family="Segoe UI,sans-serif" {glow}>{value}</text>\n'
            f'    </g>'
        )

    flame_icon = icon("flame", 235, 140, 24, T["orange"]) if cur > 0 else ""

    body = (
        f'  <rect x="10" y="10" width="475" height="175" rx="10" fill="{T["card"]}" fill-opacity="0.6" stroke="{T["border"]}" stroke-width="1" filter="url(#cardShadow)"/>\n'
        f'  <text x="30" y="45" fill="url(#neonOrange)" font-size="20" font-weight="700" font-family="Segoe UI,Ubuntu,sans-serif" filter="url(#glow)">GitHub Streak</text>\n'
        f'  <line x1="30" y1="55" x2="465" y2="55" stroke="{T["border"]}" stroke-width="1"/>\n'
        + block(125, "Total Contributions", f"{total:,}", T["green"], "neonGreen") + '\n'
        + block(250, "Current Streak", cur, T["orange"], "neonOrange") + '\n'
        + block(375, "Longest Streak", longest, T["purple"], "neonPurple") + '\n'
        + f'    {flame_icon}'
    )
    return wrap_svg(body, 495, 195)


def trophies_svg(data):
    repos = data["repositories"]["totalCount"]
    stars = sum(r["stargazerCount"] for r in data["repositories"]["nodes"])
    forks = sum(r["forkCount"] for r in data["repositories"]["nodes"])
    followers = data["followers"]["totalCount"]
    contrib = data["contributionsCollection"]["contributionCalendar"]["totalContributions"]

    ach = []
    if stars >= 100: ach.append(("Starstruck", f"{stars:,} Stars", "neonOrange", T["yellow"]))
    if contrib >= 1000: ach.append(("Committer", f"{contrib:,}", "neonGreen", T["green"]))
    if repos >= 20: ach.append(("Creator", f"{repos} Repos", "neonBlue", T["blue"]))
    if followers >= 50: ach.append(("Influencer", f"{followers} Followers", "neonPurple", T["purple"]))
    if forks >= 20: ach.append(("Forker", f"{forks} Forks", "neonPurple", T["pink"]))
    if len(ach) < 3: ach.append(("Developer", "Building...", "neonBlue", T["cyan"]))

    bw, bh, gap = 140, 60, 12
    tw = len(ach) * (bw + gap) + gap + 20
    th = 120

    badges = []
    for i, (title, sub, grad, stroke_c) in enumerate(ach):
        x = 20 + gap + i * (bw + gap)
        y = 40
        shimmer = (
            f'      <rect x="{x + 2}" y="{y + 2}" width="{bw - 4}" height="{bh - 4}" rx="8" fill="url(#{grad})" fill-opacity="0.08"/>\n'
            f'      <rect x="{x + 2}" y="{y + 2}" width="{bw - 4}" height="{bh - 4}" rx="8" fill="url(#shimmer)" fill-opacity="0.15">\n'
            f'        <animate attributeName="x" from="{x - 50}" to="{x + bw + 50}" dur="2s" repeatCount="indefinite"/>\n'
            f'      </rect>'
        ) if i == 0 else f'      <rect x="{x + 2}" y="{y + 2}" width="{bw - 4}" height="{bh - 4}" rx="8" fill="url(#{grad})" fill-opacity="0.08"/>'

        badges.append(
            f'    <g>\n'
            f'      <rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="10" fill="{T["card"]}" fill-opacity="0.7" stroke="{stroke_c}" stroke-width="2" filter="url(#cardShadow)"/>\n'
            + shimmer + '\n'
            f'      <text x="{x + bw / 2}" y="{y + 24}" text-anchor="middle" fill="url(#{grad})" font-size="14" font-weight="700" font-family="Segoe UI,sans-serif" filter="url(#glow)">{title}</text>\n'
            f'      <text x="{x + bw / 2}" y="{y + 44}" text-anchor="middle" fill="{T["text"]}" font-size="11" font-family="Segoe UI,sans-serif">{sub}</text>\n'
            f'    </g>'
        )

    extra_defs = (
        f'    <linearGradient id="shimmer" x1="0%" y1="0%" x2="100%" y2="0%">\n'
        f'      <stop offset="0%" stop-color="#fff" stop-opacity="0"/>\n'
        f'      <stop offset="50%" stop-color="#fff" stop-opacity="0.4"/>\n'
        f'      <stop offset="100%" stop-color="#fff" stop-opacity="0"/>\n'
        f'    </linearGradient>\n'
    )

    body = (
        f'  <text x="20" y="28" fill="url(#neonPurple)" font-size="16" font-weight="700" font-family="Segoe UI,Ubuntu,sans-serif" filter="url(#glow)">Achievements</text>\n'
        + '\n'.join(badges)
    )
    return wrap_svg(body, tw, th, extra_defs=extra_defs)


def fallback(msg="Stats temporarily unavailable"):
    ts = datetime.utcnow().isoformat()
    svg = (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<!-- Generated: {ts} -->\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="400" height="100">\n'
        f'  <rect fill="{T["card"]}" width="400" height="100" rx="10"/>\n'
        f'  <text x="200" y="55" text-anchor="middle" fill="{T["red"]}" font-size="14" font-family="sans-serif">{msg}</text>\n'
        f'</svg>'
    )
    for n in ["stats", "streak", "top-langs", "activity", "trophies"]:
        save("assets/" + n + ".svg", svg)


def main():
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_STATS_TOKEN")
    if not token:
        print("Error: GITHUB_TOKEN not set", file=sys.stderr)
        fallback("GITHUB_TOKEN missing")
        sys.exit(1)

    try:
        data = gql(token)
    except Exception as e:
        print(f"API Error: {e}", file=sys.stderr)
        fallback("API request failed")
        sys.exit(0)

    if "errors" in data:
        print(f"GraphQL errors: {data['errors']}", file=sys.stderr)
        fallback("GraphQL error")
        sys.exit(0)

    if "data" not in data or data["data"] is None or data["data"].get("viewer") is None:
        print("Invalid response structure", file=sys.stderr)
        fallback("Invalid API response")
        sys.exit(0)

    viewer = data["data"]["viewer"]

    save("assets/stats.svg", stats_svg(viewer))
    save("assets/top-langs.svg", langs_svg(viewer))
    save("assets/activity.svg", activity_svg(viewer))
    save("assets/streak.svg", streak_svg(viewer))
    save("assets/trophies.svg", trophies_svg(viewer))
    print("Done.")


if __name__ == "__main__":
    main()
