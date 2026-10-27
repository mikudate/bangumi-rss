#!/usr/bin/env python3
"""Generate an OPML file for the patched RSSHub Bangumi collection route.

Example:
    python make_opml.py --config feeds.example.json --base http://localhost:1200 --out bangumi.opml
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

SUBJECT_PATHS = {
    "1": "book",
    "2": "anime",
    "3": "music",
    "4": "game",
    "6": "real",
}

TYPE_PATHS = {
    "1": "wish",
    "2": "collect",
    "3": "do",
    "4": "on_hold",
    "5": "dropped",
}


def build_feed_url(base: str, users: list[str], subject_type: str, collection_type: str) -> str:
    ids = ",".join(users)
    return f"{base.rstrip('/')}/bangumi.tv/user/collections/{ids}/{subject_type}/{collection_type}"


def build_html_url(users: list[str], subject_type: str, collection_type: str) -> str:
    first = users[0]
    subject_path = SUBJECT_PATHS.get(subject_type)
    if not subject_path:
        return f"https://bgm.tv/user/{first}/collections"
    type_path = TYPE_PATHS.get(collection_type)
    suffix = f"/{type_path}" if type_path else ""
    return f"https://bgm.tv/{subject_path}/list/{first}{suffix}"


def outline(title: str, xml_url: str, html_url: str) -> str:
    return (
        f'<outline text={quoteattr(title)} title={quoteattr(title)} '
        f'type="rss" xmlUrl={quoteattr(xml_url)} htmlUrl={quoteattr(html_url)} />'
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate OPML for Bangumi collection RSS feeds.")
    parser.add_argument("--config", default="feeds.example.json", help="JSON config file")
    parser.add_argument("--base", help="RSSHub base URL, overrides config.base")
    parser.add_argument("--out", default="bangumi.opml", help="Output OPML path")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config not found: {config_path}", file=sys.stderr)
        return 1

    config = json.loads(config_path.read_text(encoding="utf-8"))
    base = args.base or config.get("base") or "http://localhost:1200"

    outlines: list[str] = []
    for index, feed in enumerate(config.get("feeds", []), start=1):
        title = feed.get("title") or f"Bangumi 收藏 {index}"
        users = [str(user).strip() for user in feed.get("users", []) if str(user).strip()]
        subject_type = str(feed.get("subject_type", "all"))
        collection_type = str(feed.get("type", "all"))

        if not users:
            print(f"Skip feed {title!r}: no users", file=sys.stderr)
            continue
        if subject_type not in {"all", *SUBJECT_PATHS}:
            print(f"Skip feed {title!r}: unsupported subject_type={subject_type}", file=sys.stderr)
            continue
        if collection_type not in {"all", *TYPE_PATHS}:
            print(f"Skip feed {title!r}: unsupported type={collection_type}", file=sys.stderr)
            continue

        if feed.get("split"):
            for user in users:
                feed_title = f"{title} · {user}"
                xml_url = build_feed_url(base, [user], subject_type, collection_type)
                html_url = build_html_url([user], subject_type, collection_type)
                outlines.append(outline(feed_title, xml_url, html_url))
                print(f"{feed_title}\n  {xml_url}")
        else:
            xml_url = build_feed_url(base, users, subject_type, collection_type)
            html_url = build_html_url(users, subject_type, collection_type)
            outlines.append(outline(title, xml_url, html_url))
            print(f"{title}\n  {xml_url}")

    if not outlines:
        print("No feeds generated.", file=sys.stderr)
        return 1

    now = format_datetime(datetime.now(timezone.utc))
    body = "\n    ".join(outlines)
    opml = f"""<?xml version="1.0" encoding="UTF-8"?>
<opml version="2.0">
  <head>
    <title>Bangumi 收藏 RSS</title>
    <dateCreated>{escape(now)}</dateCreated>
  </head>
  <body>
    {body}
  </body>
</opml>
"""

    Path(args.out).write_text(opml, encoding="utf-8")
    print(f"\nOPML written to {args.out} ({len(outlines)} feeds)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
