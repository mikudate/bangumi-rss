#!/usr/bin/env python3
"""Generate static RSS 2.0 feeds for Bangumi user collections.

No server needed: the generated XML files can be published on GitHub Pages,
Netlify, object storage, or any static host.

Example:
    python bangumi_collections_feed.py \
        --config feeds.static.example.json \
        --out-dir feeds/bangumi \
        --opml feeds/bangumi/bangumi.opml \
        --base-url https://example.github.io/repo
"""

from __future__ import annotations

import argparse
import html
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

API = "https://api.bgm.tv"
USER_AGENT = "bangumi-collections-feed/1.0 (+https://github.com/DIYgod/RSSHub)"

SUBJECT_TYPE_NAMES = {
    "1": "书籍",
    "2": "动画",
    "3": "音乐",
    "4": "游戏",
    "6": "三次元",
}

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

COLLECTION_TYPE_NAMES = {
    "1": {"1": "想读", "2": "读过", "3": "在读", "4": "搁置", "5": "抛弃"},
    "2": {"1": "想看", "2": "看过", "3": "在看", "4": "搁置", "5": "抛弃"},
    "3": {"1": "想听", "2": "听过", "3": "在听", "4": "搁置", "5": "抛弃"},
    "4": {"1": "想玩", "2": "玩过", "3": "在玩", "4": "搁置", "5": "抛弃"},
    "6": {"1": "想看", "2": "看过", "3": "在看", "4": "搁置", "5": "抛弃"},
}

DEFAULT_TYPE_NAMES = COLLECTION_TYPE_NAMES["2"]


def get_type_name(subject_type: str, collection_type: str) -> str:
    return COLLECTION_TYPE_NAMES.get(str(subject_type), {}).get(str(collection_type)) or DEFAULT_TYPE_NAMES.get(str(collection_type), "")


def normalize_image(url: str | None) -> str:
    if not url:
        return ""
    return "https:" + url if url.startswith("//") else url


def format_date(value: str | None) -> str:
    return str(value)[:10] if value else ""


def parse_datetime(value: str | None) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)


def render_stars(rate: int) -> str:
    rate = max(0, min(10, int(rate or 0)))
    return "★" * rate + "☆" * (10 - rate) if rate else ""


def render_progress(item: dict) -> str:
    subject = item.get("subject") or {}
    subject_type = str(item.get("subject_type"))
    parts: list[str] = []

    if subject_type == "1":
        if int(item.get("vol_status") or 0) > 0:
            parts.append(f"卷 {int(item.get('vol_status'))} / {int(subject.get('volumes') or 0) or '?'}")
        if int(item.get("ep_status") or 0) > 0:
            parts.append(f"读到 {int(item.get('ep_status'))} / {int(subject.get('eps') or 0) or '?'} 话")
    elif subject_type in {"2", "6"}:
        if int(item.get("ep_status") or 0) > 0:
            parts.append(f"看到 {int(item.get('ep_status'))} / {int(subject.get('eps') or 0) or '?'} 话")

    return " · ".join(parts)


def item_html(item: dict, show_user: bool) -> str:
    subject = item.get("subject") or {}
    subject_id = item.get("subject_id")
    subject_url = f"https://bgm.tv/subject/{subject_id}"
    cover = normalize_image(subject.get("images", {}).get("common") or subject.get("images", {}).get("medium") or subject.get("images", {}).get("large"))
    title = subject.get("name_cn") or subject.get("name") or f"条目 {subject_id}"
    original_title = subject.get("name") if subject.get("name_cn") and subject.get("name") and subject.get("name") != subject.get("name_cn") else ""
    subject_type_name = SUBJECT_TYPE_NAMES.get(str(item.get("subject_type")), "条目")
    status_name = get_type_name(item.get("subject_type"), item.get("type"))
    rate = int(item.get("rate") or 0)
    score = float(subject.get("score") or 0)
    comment = (item.get("comment") or "").strip()
    tags = [str(tag) for tag in (item.get("tags") or []) if tag]
    meta = " · ".join(part for part in [format_date(subject.get("date")), subject_type_name, status_name, render_progress(item)] if part)
    updated = format_date(item.get("updated_at"))
    collection_url = f"https://bgm.tv/user/{item.get('_username')}/collections"

    parts: list[str] = []
    if cover:
        parts.append(
            f'<a href="{html.escape(subject_url, quote=True)}">'
            f'<img src="{html.escape(cover, quote=True)}" alt="{html.escape(title, quote=True)}" width="100" align="left" style="margin:0 12px 8px 0;border-radius:4px;">'
            f"</a>"
        )

    title_html = f'<b><a href="{html.escape(subject_url, quote=True)}">{html.escape(title)}</a></b>'
    if original_title:
        title_html += f"<br><small>{html.escape(original_title)}</small>"
    parts.append(f'<p style="margin:0 0 4px;">{title_html}</p>')

    if meta:
        parts.append(f'<p style="margin:0 0 4px;"><small>{html.escape(meta)}</small></p>')

    rating_html = "我的评分：" + (f"{render_stars(rate)} {rate}/10" if rate else "未评分")
    rating_html += "<br>Bangumi 评分：" + (f"{score:.1f}" if score else "暂无")
    parts.append(f'<p style="margin:0 0 4px;">{rating_html}</p>')

    if comment:
        comment_html = html.escape(comment).replace("\r\n", "\n").replace("\n", "<br>")
        parts.append(f'<p style="margin:8px 0;">{comment_html}</p>')

    if tags:
        parts.append(f'<p style="margin:0 0 4px;"><small>标签：{html.escape(" ".join("#" + tag for tag in tags[:8]))}</small></p>')

    source = ""
    if show_user:
        source = f'来自 <a href="{html.escape(collection_url, quote=True)}">{html.escape(item.get("_nickname") or "")}</a> · '
    parts.append(
        f'<p style="margin:0;"><small>{source}收藏于 {html.escape(updated or "未知")} · '
        f'<a href="{html.escape(subject_url, quote=True)}">查看条目</a></small></p>'
    )
    parts.append('<div style="clear:both;"></div>')

    return "".join(parts)


def collection_page_url(users: list[str], subject_type: str, collection_type: str) -> str:
    subject_path = SUBJECT_PATHS.get(subject_type)
    if not subject_path:
        return f"https://bgm.tv/user/{users[0]}/collections"
    type_path = TYPE_PATHS.get(collection_type)
    return f"https://bgm.tv/{subject_path}/list/{users[0]}{'/' + type_path if type_path else ''}"


def read_json(url: str, fixture_dir: str | None, fixture_name: str | None) -> dict:
    if fixture_dir and fixture_name:
        path = Path(fixture_dir) / fixture_name
        return json.loads(path.read_text(encoding="utf-8-sig"))

    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.loads(response.read().decode("utf-8"))


def get_user(username: str, fixture_dir: str | None) -> dict:
    try:
        data = read_json(f"{API}/v0/users/{urllib.parse.quote(username)}", fixture_dir, f"{username}_user.json")
        avatar = data.get("avatar") or {}
        return {
            "username": username,
            "nickname": data.get("nickname") or username,
            "avatar": normalize_image(avatar.get("large") or avatar.get("medium")),
        }
    except Exception as error:  # noqa: BLE001
        print(f"  ! user {username}: {error}", file=sys.stderr)
        return {"username": username, "nickname": username, "avatar": ""}


def get_collections(username: str, subject_type: str, collection_type: str, limit: int, fixture_dir: str | None) -> list[dict]:
    params = {"limit": str(min(limit, 100)), "offset": "0"}
    if subject_type != "all":
        params["subject_type"] = subject_type
    if collection_type != "all":
        params["type"] = collection_type
    url = f"{API}/v0/users/{urllib.parse.quote(username)}/collections?{urllib.parse.urlencode(params)}"
    data = read_json(url, fixture_dir, f"{username}_{subject_type}_{collection_type}.json")
    return data.get("data") or []


def feed_title(results: list[dict], subject_type: str, collection_type: str) -> str:
    nicknames = [result["user"]["nickname"] for result in results]
    subject_label = "Bangumi 条目" if subject_type == "all" else SUBJECT_TYPE_NAMES.get(subject_type, "Bangumi 条目")
    if collection_type == "all":
        type_label = ""
    elif subject_type == "all":
        type_label = {"1": "想收藏", "2": "已收藏", "3": "进行中", "4": "搁置", "5": "抛弃"}.get(collection_type, "")
    else:
        type_label = get_type_name(subject_type, collection_type)

    if len(results) == 1:
        if type_label:
            return f"{nicknames[0]} {type_label}的 {subject_label}" if subject_type == "all" else f"{nicknames[0]} {type_label}的{subject_label}"
        return f"{nicknames[0]} 收藏的 {subject_label}" if subject_type == "all" else f"{nicknames[0]} 收藏的{subject_label}"

    label = f"{type_label}的 {subject_label}" if subject_type == "all" and type_label else (f"{type_label}的{subject_label}" if type_label else f"收藏的 {subject_label}")
    suffix = f" · {'、'.join(nicknames[:3])}"
    if len(nicknames) > 3:
        suffix += f" 等 {len(nicknames)} 人"
    return label + suffix


def build_feed_xml(feed: dict, base_url: str, limit: int, fixture_dir: str | None, delay: float) -> tuple[str, str, list[str], int] | None:
    users = [str(user).strip() for user in feed.get("users", []) if str(user).strip()]
    subject_type = str(feed.get("subject_type", "all"))
    collection_type = str(feed.get("type", "all"))
    slug = str(feed.get("slug") or "feed")

    results: list[dict] = []
    for username in users:
        user = get_user(username, fixture_dir)
        try:
            items = get_collections(username, subject_type, collection_type, limit, fixture_dir)
        except Exception as error:  # noqa: BLE001
            print(f"  ! collections {username}: {error}", file=sys.stderr)
            time.sleep(delay)
            continue
        results.append({"user": user, "items": items})
        print(f"  - {username}: {len(items)} items")
        time.sleep(delay)

    if not results:
        return None

    show_user = len(results) > 1
    raw_items = []
    for result in results:
        for item in result["items"]:
            raw_items.append({**item, "_username": result["user"]["username"], "_nickname": result["user"]["nickname"]})
    raw_items.sort(key=lambda item: parse_datetime(item.get("updated_at")), reverse=True)
    raw_items = raw_items[:limit]

    title = str(feed.get("title") or "").strip() or feed_title(results, subject_type, collection_type)
    link = collection_page_url(users, subject_type, collection_type)
    description = "Bangumi 用户收藏：" + "、".join(f"{result['user']['nickname']}（{len(result['items'])} 条）" for result in results)

    items_xml: list[str] = []
    for item in raw_items:
        subject = item.get("subject") or {}
        base_title = subject.get("name_cn") or subject.get("name") or f"条目 {item.get('subject_id')}"
        status_name = get_type_name(item.get("subject_type"), item.get("type"))
        prefix = f"【{status_name}】" if collection_type == "all" else ""
        user_prefix = f"[{item['_nickname']}] " if show_user else ""
        pub_date = parse_datetime(item.get("updated_at"))
        subject_link = f"https://bgm.tv/subject/{item.get('subject_id')}"
        guid = f"bgm.tv/collection/{item['_username']}/{item.get('subject_id')}"
        items_xml.append(
            "<item>"
            f"<title>{escape(user_prefix + prefix + base_title)}</title>"
            f"<link>{escape(subject_link)}</link>"
            f'<guid isPermaLink="false">{escape(guid)}</guid>'
            f"<pubDate>{format_datetime(pub_date.astimezone(timezone.utc))}</pubDate>"
            f"<dc:creator>{escape(item['_nickname'])}</dc:creator>"
            f"<description>{escape(item_html(item, show_user))}</description>"
            "</item>"
        )

    now = format_datetime(datetime.now(timezone.utc))
    self_url = f"{base_url.rstrip('/')}/bangumi/{slug}.xml"
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:dc="http://purl.org/dc/elements/1.1/">
  <channel>
    <title>{escape(title)}</title>
    <link>{escape(link)}</link>
    <description>{escape(description)}</description>
    <language>zh-CN</language>
    <lastBuildDate>{now}</lastBuildDate>
    <generator>bangumi-collections-feed</generator>
    <ttl>60</ttl>
    <atom:link href={quoteattr(self_url)} rel="self" type="application/rss+xml"/>
    {''.join(items_xml)}
  </channel>
</rss>
"""

    return xml, title, users, len(raw_items)


def build_opml(entries: list[dict], base_url: str) -> str:
    outlines = []
    for entry in entries:
        outlines.append(
            f'<outline text={quoteattr(entry["title"])} title={quoteattr(entry["title"])} '
            f'type="rss" xmlUrl={quoteattr(entry["xml_url"])} htmlUrl={quoteattr(entry["html_url"])} />'
        )
    now = format_datetime(datetime.now(timezone.utc))
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<opml version="2.0">
  <head>
    <title>Bangumi 收藏 RSS</title>
    <dateCreated>{now}</dateCreated>
  </head>
  <body>
    {'\n    '.join(outlines)}
  </body>
</opml>
"""


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Generate static RSS feeds for Bangumi user collections.")
    parser.add_argument("--config", default="feeds.static.example.json", help="JSON config file")
    parser.add_argument("--out-dir", default="feeds/bangumi", help="Directory for generated XML files")
    parser.add_argument("--opml", default="feeds/bangumi/bangumi.opml", help="Output OPML path")
    parser.add_argument("--base-url", help="Public base URL, overrides config.base_url")
    parser.add_argument("--limit", type=int, default=100, help="Items per user (max 100)")
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between API requests in seconds")
    parser.add_argument("--fixture-dir", help="Read API responses from this directory instead of the network (for testing)")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config not found: {config_path}", file=sys.stderr)
        return 1
    config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    base_url = args.base_url or config.get("base_url") or "http://127.0.0.1:8811"
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    entries: list[dict] = []
    for index, feed in enumerate(config.get("feeds", []), start=1):
        slug = str(feed.get("slug") or f"feed-{index}")
        feeds = [feed]
        if feed.get("split"):
            feeds = [{**feed, "slug": f"{slug}-{user}", "title": f"{feed.get('title', slug)} · {user}", "users": [user]} for user in feed.get("users", [])]

        for current in feeds:
            current_slug = str(current.get("slug") or slug)
            print(f"Building {current_slug}...")
            result = build_feed_xml(current, base_url, min(args.limit, 100), args.fixture_dir, args.delay)
            if result is None:
                print(f"  ! skipped {current_slug}: no data", file=sys.stderr)
                continue
            xml, title, users, count = result
            output_path = out_dir / f"{current_slug}.xml"
            output_path.write_text(xml, encoding="utf-8")
            entries.append(
                {
                    "title": title,
                    "xml_url": f"{base_url.rstrip('/')}/bangumi/{current_slug}.xml",
                    "html_url": collection_page_url(users, str(current.get("subject_type", "all")), str(current.get("type", "all"))),
                }
            )
            print(f"  -> {output_path} ({count} items, {len(xml)} bytes)")

    if not entries:
        print("No feeds generated.", file=sys.stderr)
        return 1

    opml_path = Path(args.opml)
    opml_path.parent.mkdir(parents=True, exist_ok=True)
    opml_path.write_text(build_opml(entries, base_url), encoding="utf-8")
    print(f"OPML -> {opml_path} ({len(entries)} feeds)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
