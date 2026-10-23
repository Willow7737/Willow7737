#!/usr/bin/env python3
"""
Writes live GitHub stats into README.md as plain markdown (no images).

Everything between <!-- STATS:START --> and <!-- STATS:END --> is replaced.
Plain text can't be blurred, scaled, or served stale from an image cache, and
it renders identically on github.com and in mobile GitHub clients.

Standard library only. On any API failure the README is left untouched and the
script exits non-zero.
"""

import json
import os
import re
import sys
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone

README = os.path.join(os.path.dirname(__file__), "..", "..", "README.md")
START, END = "<!-- STATS:START -->", "<!-- STATS:END -->"
# Build/script files that say nothing about what you actually write.
IGNORED_LANGS = {"Makefile", "Dockerfile", "CMake", "Batchfile", "Shell", "Nix"}

GRAPHQL = "https://api.github.com/graphql"
QUERY = """
query {
  viewer {
    followers { totalCount }
    repositories(first: 100, ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false) {
      totalCount
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
      }
    }
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionCount date } }
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
        ((d["date"], d["contributionCount"]) for w in weeks for d in w["contributionDays"])
    )
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    cur = 0
    for date, count in reversed(days):
        if date > today or (date == today and count == 0):
            continue  # today isn't over yet; don't break the streak
        if count > 0:
            cur += 1
        else:
            break

    longest = run = 0
    for _, count in days:
        run = run + 1 if count > 0 else 0
        longest = max(longest, run)
    return cur, longest


def plural(n, word):
    return f"**{n:,}** {word}" + ("" if n == 1 else "s")


def render(v):
    repos = v["repositories"]["totalCount"]
    stars = sum(r["stargazerCount"] for r in v["repositories"]["nodes"])
    followers = v["followers"]["totalCount"]
    cal = v["contributionsCollection"]["contributionCalendar"]
    cur, longest = streaks(cal["weeks"])

    size_by = defaultdict(int)
    for repo in v["repositories"]["nodes"]:
        for e in repo["languages"]["edges"]:
            if e["node"]["name"] not in IGNORED_LANGS:
                size_by[e["node"]["name"]] += e["size"]
    total = sum(size_by.values())
    top = sorted(size_by.items(), key=lambda kv: kv[1], reverse=True)[:6]

    lines = [
        f"{plural(repos, 'public repository').replace('repositorys', 'repositories')} · "
        f"{plural(stars, 'star')} · {plural(followers, 'follower')}",
        "",
        f"**{cal['totalContributions']:,}** contributions in the past year · "
        f"current streak **{cur:,}** days · longest **{longest:,}** days",
    ]

    if total:
        width = 20
        name_w = max(len(n) for n, _ in top)
        rows = []
        for name, size in top:
            pct = size / total * 100
            filled = max(1, round(width * size / total))
            rows.append(f"{name:<{name_w}}  {'█' * filled}{'░' * (width - filled)}  {pct:5.1f}%")
        lines += ["", "```text", *rows, "```"]

    return "\n".join(lines)


def patch_readme(block):
    with open(README, encoding="utf-8") as f:
        text = f.read()
    pattern = re.compile(re.escape(START) + r".*?" + re.escape(END), re.DOTALL)
    if not pattern.search(text):
        sys.exit(f"Markers {START} / {END} not found in README.md")
    new = pattern.sub(lambda _: f"{START}\n{block}\n{END}", text)
    if new != text:
        with open(README, "w", encoding="utf-8") as f:
            f.write(new)
    print("README updated." if new != text else "No change.")


def main():
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_STATS_TOKEN")
    if not token:
        sys.exit("GITHUB_TOKEN / GH_STATS_TOKEN not set; README left untouched.")
    try:
        payload = gql(token)
    except Exception as e:
        sys.exit(f"API request failed ({e}); README left untouched.")

    viewer = (payload.get("data") or {}).get("viewer")
    if payload.get("errors") or not viewer:
        sys.exit(f"GraphQL error: {payload.get('errors') or 'empty response'}; README left untouched.")

    patch_readme(render(viewer))


if __name__ == "__main__":
    main()
