#!/usr/bin/env python3
"""Generate a simple isometric 3D-style contribution banner for the profile README."""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = REPO_ROOT / "assets"
README_PATH = REPO_ROOT / "README.md"
DEFAULT_USERNAME = "canyang25"

SVG_WIDTH = 280
SVG_HEIGHT = 150
ROWS = 7
CELL_W = 4
CELL_H = 1
START_X = 34
START_Y = 52


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update the 3D contribution banner")
    parser.add_argument("--username", default=DEFAULT_USERNAME, help="GitHub username")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite assets/contrib-3d-banner.svg/png and refresh README alt count",
    )
    parser.add_argument("--version", default="preview", help="Output suffix when not overwriting")
    return parser.parse_args()


def fetch_calendar_with_token(username: str, token: str) -> dict:
    query = """
    query($login: String!) {
      user(login: $login) {
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                contributionCount
                contributionLevel
                date
                weekday
              }
            }
          }
        }
      }
    }
    """
    payload = json.dumps({"query": query, "variables": {"login": username}}).encode("utf-8")
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "canyang25-3d-banner-updater",
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read())
    return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def fetch_calendar_with_gh(username: str) -> dict:
    query = (
        "query($login:String!){ user(login:$login){ contributionsCollection { contributionCalendar "
        "{ totalContributions weeks { contributionDays { contributionCount contributionLevel date weekday } } } } } }"
    )
    out = subprocess.check_output(
        ["gh", "api", "graphql", "-f", f"query={query}", "-F", f"login={username}"],
        text=True,
        cwd=REPO_ROOT,
    )
    data = json.loads(out)
    return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def fetch_calendar(username: str) -> dict:
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        return fetch_calendar_with_token(username, token)
    return fetch_calendar_with_gh(username)


def level_score(level: str) -> int:
    return {
        "FOURTH_QUARTILE": 4,
        "THIRD_QUARTILE": 3,
        "SECOND_QUARTILE": 2,
        "FIRST_QUARTILE": 1,
    }.get(level, 0)


def bar_height(count: int, level: str, max_count: int) -> int:
    if count <= 0:
        return 2
    return round(2 + math.sqrt(count / max_count) * 14 + level_score(level) * 3)


def points(coords: list[tuple[float, float]]) -> str:
    return " ".join(f"{x:.1f},{y:.1f}" for x, y in coords)


def cube(cx: float, cy: float, height: int, active: bool, delay: float | None = None) -> str:
    top = [
        (cx, cy - height),
        (cx + CELL_W, cy - height + CELL_H),
        (cx, cy - height + 2 * CELL_H),
        (cx - CELL_W, cy - height + CELL_H),
    ]
    left = [
        (cx - CELL_W, cy - height + CELL_H),
        (cx, cy - height + 2 * CELL_H),
        (cx, cy + 2 * CELL_H),
        (cx - CELL_W, cy + CELL_H),
    ]
    right = [
        (cx + CELL_W, cy - height + CELL_H),
        (cx, cy - height + 2 * CELL_H),
        (cx, cy + 2 * CELL_H),
        (cx + CELL_W, cy + CELL_H),
    ]
    cls = "active tile" if active else "base tile"
    style = f' style="animation-delay:{delay:.2f}s"' if active and delay is not None else ""
    return (
        f'<g class="{cls}"{style}>'
        f'<polygon class="left" points="{points(left)}"/>'
        f'<polygon class="right" points="{points(right)}"/>'
        f'<polygon class="top" points="{points(top)}"/>'
        f"</g>"
    )


def build_svg(calendar: dict) -> str:
    weeks = calendar["weeks"][-53:]
    cols = len(weeks)
    max_count = (
        max(
            (day["contributionCount"] for week in weeks for day in week.get("contributionDays", [])),
            default=1,
        )
        or 1
    )

    svg: list[str] = []
    svg.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{SVG_WIDTH}" height="{SVG_HEIGHT}" '
        f'viewBox="0 0 {SVG_WIDTH} {SVG_HEIGHT}">'
    )
    svg.append(
        "<defs>"
        '<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0%" stop-color="#f8fafc"/>'
        '<stop offset="100%" stop-color="#f1f5f9"/>'
        "</linearGradient>"
        '<linearGradient id="topFace" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0%" stop-color="#5eead4"/>'
        '<stop offset="55%" stop-color="#14b8a6"/>'
        '<stop offset="100%" stop-color="#0f766e"/>'
        "</linearGradient>"
        '<linearGradient id="leftFace" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0%" stop-color="#0f766e"/>'
        '<stop offset="100%" stop-color="#134e4a"/>'
        "</linearGradient>"
        '<linearGradient id="rightFace" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0%" stop-color="#99f6e4"/>'
        '<stop offset="100%" stop-color="#5eead4"/>'
        "</linearGradient>"
        '<filter id="glow" x="-50%" y="-50%" width="200%" height="200%">'
        '<feGaussianBlur stdDeviation="1" result="b"/>'
        "<feMerge><feMergeNode in=\"b\"/><feMergeNode in=\"SourceGraphic\"/></feMerge>"
        "</filter>"
        "</defs>"
    )
    svg.append(
        "<style>"
        ".title{font:700 10px -apple-system,BlinkMacSystemFont,Segoe UI,Arial;fill:#0f172a}"
        ".sub{font:500 8px -apple-system,BlinkMacSystemFont,Segoe UI,Arial;fill:#64748b}"
        ".base .top{fill:#e2e8f0}.base .left{fill:#cbd5e1}.base .right{fill:#94a3b8}"
        ".active .top{fill:url(#topFace)} .active .left{fill:url(#leftFace)} .active .right{fill:url(#rightFace)}"
        ".active{filter:url(#glow)}"
        "</style>"
    )
    svg.append('<rect x="0" y="0" width="280" height="150" fill="url(#bg)" rx="4"/>')
    svg.append(f'<text class="title" x="4" y="10">{calendar["totalContributions"]} contributions</text>')
    svg.append('<text class="sub" x="4" y="18">in the last year</text>')

    for diagonal in range(cols + ROWS - 1):
        for row in range(ROWS):
            col = diagonal - row
            if col < 0 or col >= cols:
                continue
            days = weeks[col].get("contributionDays", [])
            day = days[row] if row < len(days) else None
            count = day.get("contributionCount", 0) if day else 0
            level = day.get("contributionLevel", "NONE") if day else "NONE"
            height = bar_height(count, level, max_count)
            cx = START_X + (col - row) * CELL_W
            cy = START_Y + (col + row) * CELL_H
            delay = ((col + row) % 14) * 0.05
            svg.append(cube(cx, cy, height, count > 0, delay))

    svg.append("</svg>")
    return "\n".join(svg)


def render_png(svg_path: Path, png_path: Path) -> None:
    subprocess.check_call(
        [
            "rsvg-convert",
            "-w",
            "560",
            "-h",
            "300",
            str(svg_path),
            "-o",
            str(png_path),
        ]
    )


def update_readme_total(total: int) -> None:
    content = README_PATH.read_text()
    content = re.sub(
        r'alt="\d+ contributions in the last year"',
        f'alt="{total} contributions in the last year"',
        content,
    )
    README_PATH.write_text(content)


def main() -> int:
    args = parse_args()
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    calendar = fetch_calendar(args.username)
    svg = build_svg(calendar)

    stem = "contrib-3d-banner" if args.overwrite else f"contrib-3d-banner-{args.version}"
    svg_path = ASSETS_DIR / f"{stem}.svg"
    png_path = ASSETS_DIR / f"{stem}.png"
    svg_path.write_text(svg)
    render_png(svg_path, png_path)

    if args.overwrite:
        update_readme_total(calendar["totalContributions"])

    print(f"generated {svg_path}")
    print(f"generated {png_path}")
    print(f"total contributions: {calendar['totalContributions']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
