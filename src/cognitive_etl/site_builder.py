from __future__ import annotations

import json
import os
import shutil
from collections import Counter, defaultdict
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from jinja2 import Environment, FileSystemLoader

from cognitive_etl.config import CONTENT_DIR, DATA_DIR, DIST_DIR, STATIC_DIR, TEMPLATE_DIR, get_site_config
from cognitive_etl.routes import build_content_relpath, build_detail_href

DEFAULT_GRAPH: dict[str, list[dict[str, Any]]] = {"nodes": [], "edges": []}


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_datetime(value: str | None) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        try:
            return datetime.fromisoformat(f"{value}T00:00:00+00:00")
        except ValueError:
            return datetime.min.replace(tzinfo=timezone.utc)


def format_last_synced(value: str | None) -> str:
    moment = parse_datetime(value)
    if moment.year == datetime.min.year:
        return "Not synced yet"
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default

    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: Any) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, default=str)


def first_text(record: dict[str, Any], *keys: str) -> str:
    for key in keys:
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def relation_ids(record: dict[str, Any], *keys: str) -> list[str]:
    for key in keys:
        value = record.get(key)
        if isinstance(value, list) and value:
            return value
    return []


def capture_title(capture: dict[str, Any]) -> str:
    return first_text(capture, "Name", "Title", "Capture", "Excerpt") or "Untitled Capture"


def capture_type(capture: dict[str, Any]) -> str:
    return first_text(capture, "Capture Type", "Type") or "Capture"


def capture_status(capture: dict[str, Any]) -> str:
    return first_text(capture, "Status", "Stage") or "Inbox"


def capture_summary(capture: dict[str, Any]) -> str:
    return (
        first_text(capture, "Summary", "Excerpt", "What Stuck", "Why It Matters", "Reflection")
        or first_text(capture, "content_plain")
    )


def capture_source_ids(capture: dict[str, Any]) -> list[str]:
    return relation_ids(capture, "Source", "Sources")


def capture_atom_ids(capture: dict[str, Any]) -> list[str]:
    return relation_ids(capture, "Spawned Atoms", "Atoms")


def capture_artifact_ids(capture: dict[str, Any]) -> list[str]:
    return relation_ids(capture, "Artifacts", "Used In Artifacts")


def build_search_index(
    captures: list[dict[str, Any]],
    atoms: list[dict[str, Any]],
    artifacts: list[dict[str, Any]],
    sources: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    index: list[dict[str, Any]] = []

    for capture in captures:
        index.append(
            {
                "type": "capture",
                "id": capture.get("Capture ID", capture.get("id", "")),
                "title": capture_title(capture),
                "body": capture_summary(capture),
                "domain": capture.get("Domain", []),
                "tags": [capture_type(capture), capture_status(capture)],
                "href": build_detail_href("capture", capture),
            }
        )

    for atom in atoms:
        index.append(
            {
                "type": "atom",
                "id": atom.get("Atom ID", atom.get("id", "")),
                "title": atom.get("Claim", ""),
                "body": atom.get("Definition", "") or atom.get("content_plain", ""),
                "domain": atom.get("Domain", []),
                "tags": [atom.get("Type", ""), atom.get("Confidence", "")],
                "href": build_detail_href("atom", atom),
            }
        )

    for artifact in artifacts:
        index.append(
            {
                "type": "artifact",
                "id": artifact.get("Artifact ID", artifact.get("id", "")),
                "title": artifact.get("Name", ""),
                "body": artifact.get("Chapter/Section", "") or artifact.get("content_plain", ""),
                "domain": artifact.get("Domain", []),
                "tags": [artifact.get("Format", ""), artifact.get("Status", "")],
                "href": build_detail_href("artifact", artifact),
            }
        )

    for source in sources:
        index.append(
            {
                "type": "source",
                "id": source.get("Source ID", source.get("id", "")),
                "title": source.get("Name", ""),
                "body": source.get("Key Takeaway", "") or source.get("content_plain", ""),
                "domain": source.get("Domain", []),
                "tags": [source.get("Type", ""), source.get("Author", "")],
                "href": build_detail_href("source", source),
            }
        )

    return index


def default_stats(
    sources: list[dict[str, Any]],
    captures: list[dict[str, Any]],
    atoms: list[dict[str, Any]],
    artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "total_sources": len(sources),
        "total_captures": len(captures),
        "total_atoms": len(atoms),
        "total_artifacts": len(artifacts),
        "shipped_artifacts": 0,
        "total_points": 0,
        "total_reuse": 0,
        "domains": {},
        "last_synced": utc_timestamp(),
    }


def build_related_source_map(sources: list[dict[str, Any]]) -> dict[str, set[str]]:
    related_map: dict[str, set[str]] = {source["id"]: set() for source in sources}
    known_sources = set(related_map)

    for source in sources:
        source_id = source["id"]
        for related_id in source.get("Related Sources", []) or []:
            if related_id not in known_sources or related_id == source_id:
                continue
            related_map[source_id].add(related_id)
            related_map[related_id].add(source_id)

    return related_map


def enrich_sources(
    sources: list[dict[str, Any]],
    source_lookup: dict[str, str],
    source_href_lookup: dict[str, str],
    source_content_lookup: dict[str, str],
    capture_lookup: dict[str, str],
    capture_href_lookup: dict[str, str],
    capture_content_lookup: dict[str, str],
    source_capture_ids: dict[str, list[str]],
    atom_lookup: dict[str, str],
    atom_href_lookup: dict[str, str],
    atom_content_lookup: dict[str, str],
    artifact_lookup: dict[str, str],
    artifact_href_lookup: dict[str, str],
    artifact_content_lookup: dict[str, str],
) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    related_source_map = build_related_source_map(sources)

    for source in sorted(sources, key=lambda item: parse_datetime(item.get("created_time")), reverse=True):
        record = dict(source)
        processed = int(record.get("Chapters Processed") or 0)
        total = int(record.get("Total Chapters") or 0)
        related_ids = sorted(related_source_map.get(record["id"], set()), key=lambda item: source_lookup.get(item, item))
        capture_ids = source_capture_ids.get(record["id"], [])
        atom_ids = record.get("Atoms") or []
        artifact_ids = record.get("Artifacts") or []

        record["notion_url"] = record.get("url", "")
        record["detail_href"] = build_detail_href("source", record)
        record["content_path"] = build_content_relpath("source", record)
        record["public_url"] = normalize_public_url(record.get("Source URL", ""))
        record["progress_label"] = f"{processed}/{total} ch." if total else "No chapter target"
        record["progress_ratio"] = processed / total if total else 0
        record["capture_count"] = len(capture_ids)
        record["atom_count"] = len(atom_ids)
        record["artifact_count"] = len(artifact_ids)
        record["related_source_count"] = len(related_ids)
        record["related_sources_info"] = [
            {
                "name": source_lookup.get(related_id, related_id),
                "url": source_href_lookup.get(related_id, ""),
                "content_path": source_content_lookup.get(related_id, ""),
            }
            for related_id in related_ids
        ]
        record["captures_info"] = build_relation_items(capture_ids, capture_lookup, capture_href_lookup, capture_content_lookup)
        record["atoms_info"] = build_relation_items(atom_ids, atom_lookup, atom_href_lookup, atom_content_lookup)
        record["artifacts_info"] = build_relation_items(artifact_ids, artifact_lookup, artifact_href_lookup, artifact_content_lookup)
        record["content_html"] = render_content_html(record.get("content") or []) or build_source_fallback_html(record)
        enriched.append(record)

    return enriched


def enrich_captures(
    captures: list[dict[str, Any]],
    source_lookup: dict[str, str],
    source_href_lookup: dict[str, str],
    source_content_lookup: dict[str, str],
    atom_lookup: dict[str, str],
    atom_href_lookup: dict[str, str],
    atom_content_lookup: dict[str, str],
    artifact_lookup: dict[str, str],
    artifact_href_lookup: dict[str, str],
    artifact_content_lookup: dict[str, str],
) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []

    for capture in sorted(captures, key=lambda item: parse_datetime(item.get("created_time")), reverse=True):
        record = dict(capture)
        source_ids = capture_source_ids(record)
        atom_ids = capture_atom_ids(record)
        artifact_ids = capture_artifact_ids(record)

        record["display_title"] = capture_title(record)
        record["display_type"] = capture_type(record)
        record["display_status"] = capture_status(record)
        record["summary"] = capture_summary(record)
        record["notion_url"] = record.get("url", "")
        record["detail_href"] = build_detail_href("capture", record)
        record["content_path"] = build_content_relpath("capture", record)
        record["public_url"] = normalize_public_url(
            first_text(record, "Capture URL", "Source URL", "Artifact URL", "Public URL")
        )
        record["source_names"] = [source_lookup.get(source_id, source_id) for source_id in source_ids]
        record["source_summary"] = ", ".join(record["source_names"]) if record["source_names"] else "No source linked"
        record["source_count"] = len(source_ids)
        record["atom_count"] = len(atom_ids)
        record["artifact_count"] = len(artifact_ids)
        record["sources_info"] = build_relation_items(source_ids, source_lookup, source_href_lookup, source_content_lookup)
        record["atoms_info"] = build_relation_items(atom_ids, atom_lookup, atom_href_lookup, atom_content_lookup)
        record["artifacts_info"] = build_relation_items(artifact_ids, artifact_lookup, artifact_href_lookup, artifact_content_lookup)
        record["content_html"] = render_content_html(record.get("content") or []) or build_capture_fallback_html(record)
        enriched.append(record)

    return enriched


def enrich_atoms(
    atoms: list[dict[str, Any]],
    source_lookup: dict[str, str],
    source_href_lookup: dict[str, str],
    source_content_lookup: dict[str, str],
    capture_lookup: dict[str, str],
    capture_href_lookup: dict[str, str],
    capture_content_lookup: dict[str, str],
    atom_capture_ids: dict[str, list[str]],
    atom_lookup: dict[str, str],
    atom_href_lookup: dict[str, str],
    atom_content_lookup: dict[str, str],
    artifact_lookup: dict[str, str],
    artifact_href_lookup: dict[str, str],
    artifact_content_lookup: dict[str, str],
) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []

    for atom in sorted(atoms, key=lambda item: parse_datetime(item.get("created_time")), reverse=True):
        record = dict(atom)
        source_ids = record.get("Source") or []
        capture_ids = atom_capture_ids.get(record["id"], [])
        related_ids = record.get("Related Atoms") or []
        artifact_ids = record.get("Used In Artifacts") or []
        confidence = str(record.get("Confidence") or "")

        record["notion_url"] = record.get("url", "")
        record["detail_href"] = build_detail_href("atom", record)
        record["content_path"] = build_content_relpath("atom", record)
        record["source_names"] = [source_lookup.get(source_id, source_id) for source_id in source_ids]
        record["source_summary"] = ", ".join(record["source_names"]) if record["source_names"] else "No source linked"
        record["capture_count"] = len(capture_ids)
        record["related_count"] = len(related_ids)
        record["artifact_count"] = len(artifact_ids)
        record["artifact_names"] = [artifact_lookup.get(artifact_id, artifact_id) for artifact_id in artifact_ids]
        record["confidence_score"] = int(confidence[0]) if confidence[:1].isdigit() else 0
        record["sources_info"] = build_relation_items(source_ids, source_lookup, source_href_lookup, source_content_lookup)
        record["captures_info"] = build_relation_items(capture_ids, capture_lookup, capture_href_lookup, capture_content_lookup)
        record["related_atoms_info"] = build_relation_items(related_ids, atom_lookup, atom_href_lookup, atom_content_lookup)
        record["artifacts_info"] = build_relation_items(artifact_ids, artifact_lookup, artifact_href_lookup, artifact_content_lookup)
        record["content_html"] = render_content_html(record.get("content") or []) or build_atom_fallback_html(record)
        enriched.append(record)

    return enriched


def enrich_artifacts(
    artifacts: list[dict[str, Any]],
    source_lookup: dict[str, str],
    source_href_lookup: dict[str, str],
    source_content_lookup: dict[str, str],
    capture_lookup: dict[str, str],
    capture_href_lookup: dict[str, str],
    capture_content_lookup: dict[str, str],
    artifact_capture_ids: dict[str, list[str]],
    atom_lookup: dict[str, str],
    atom_href_lookup: dict[str, str],
    atom_content_lookup: dict[str, str],
) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []

    for artifact in sorted(
        artifacts,
        key=lambda item: parse_datetime(item.get("Date Shipped") or item.get("created_time")),
        reverse=True,
    ):
        record = dict(artifact)
        source_ids = record.get("Source") or []
        capture_ids = artifact_capture_ids.get(record["id"], [])
        atom_ids = record.get("Built From") or []

        record["notion_url"] = record.get("url", "")
        record["detail_href"] = build_detail_href("artifact", record)
        record["content_path"] = build_content_relpath("artifact", record)
        record["public_url"] = normalize_public_url(record.get("Artifact URL", ""))
        record["source_names"] = [source_lookup.get(source_id, source_id) for source_id in source_ids]
        record["atom_names"] = [atom_lookup.get(atom_id, atom_id) for atom_id in atom_ids]
        record["source_summary"] = ", ".join(record["source_names"]) if record["source_names"] else "No source linked"
        record["capture_count"] = len(capture_ids)
        record["built_from_count"] = len(atom_ids)
        record["sources_info"] = build_relation_items(source_ids, source_lookup, source_href_lookup, source_content_lookup)
        record["captures_info"] = build_relation_items(capture_ids, capture_lookup, capture_href_lookup, capture_content_lookup)
        record["atoms_info"] = build_relation_items(atom_ids, atom_lookup, atom_href_lookup, atom_content_lookup)
        record["content_html"] = render_content_html(record.get("content") or []) or build_artifact_fallback_html(record)
        enriched.append(record)

    return enriched


def build_source_pipeline(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = Counter((source.get("Status") or "Queue") for source in sources)
    order = ("Queue", "Reading", "Extracting", "Done")
    return [{"label": status, "count": counts.get(status, 0)} for status in order]


def build_capture_pipeline(captures: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = Counter(capture_status(capture) for capture in captures)
    order = ("Inbox", "Distilling", "Linked", "Used")
    pipeline = [{"label": status, "count": counts.get(status, 0)} for status in order]

    for status, count in sorted(counts.items()):
        if status not in order:
            pipeline.append({"label": status, "count": count})

    return pipeline


def build_domain_summary(stats: dict[str, Any]) -> list[dict[str, Any]]:
    domains = stats.get("domains", {}) or {}
    return [
        {"name": name, "count": count}
        for name, count in sorted(domains.items(), key=lambda item: (-item[1], item[0]))
    ]


def normalize_public_url(value: str | None) -> str:
    if not value:
        return ""

    candidate = value.strip()
    parsed = urlparse(candidate)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return ""

    hostname = parsed.netloc.lower()
    bare_hostname = hostname[4:] if hostname.startswith("www.") else hostname

    # `notion.so` links are usually workspace-private. Public Notion publishing should
    # use `notion.site` or a custom public domain, which we allow.
    if bare_hostname == "notion.so" or bare_hostname.endswith(".notion.so"):
        return ""

    return candidate


def build_relation_items(
    ids: list[str],
    title_lookup: dict[str, str],
    href_lookup: dict[str, str],
    content_lookup: dict[str, str] | None = None,
) -> list[dict[str, str]]:
    return [
        {
            "title": title_lookup.get(item_id, item_id),
            "href": href_lookup.get(item_id, ""),
            "content_path": content_lookup.get(item_id, "") if content_lookup else "",
        }
        for item_id in ids
    ]


def build_source_preview(record: dict[str, Any]) -> dict[str, str]:
    return {
        "title": record.get("Name", "Untitled"),
        "href": record.get("detail_href", ""),
        "content_path": record.get("content_path", ""),
        "kicker": record.get("Author", ""),
        "meta": record.get("progress_label", ""),
        "summary": record.get("Key Takeaway", ""),
    }


def build_capture_preview(record: dict[str, Any]) -> dict[str, str]:
    return {
        "title": record.get("display_title", "Untitled Capture"),
        "href": record.get("detail_href", ""),
        "content_path": record.get("content_path", ""),
        "kicker": record.get("display_type", "Capture"),
        "meta": record.get("display_status", ""),
        "summary": record.get("summary", ""),
        "excerpt": first_text(record, "Excerpt"),
        "support": first_text(record, "Why It Matters", "What Stuck"),
    }


def build_atom_preview(record: dict[str, Any]) -> dict[str, str]:
    return {
        "title": record.get("Claim", "Untitled Atom"),
        "href": record.get("detail_href", ""),
        "content_path": record.get("content_path", ""),
        "kicker": record.get("Type", "atom"),
        "meta": record.get("source_summary", ""),
        "summary": record.get("Definition", ""),
        "excerpt": record.get("Source Quote", ""),
        "support": first_text(record, "Because", "Boundaries"),
    }


def build_artifact_preview(record: dict[str, Any]) -> dict[str, str]:
    points = record.get("Points", 0) or 0
    points_label = f"+{points} pts" if points else ""
    return {
        "title": record.get("Name", "Untitled Artifact"),
        "href": record.get("detail_href", ""),
        "content_path": record.get("content_path", ""),
        "kicker": record.get("Format", "Artifact"),
        "meta": record.get("Status", ""),
        "summary": record.get("Chapter/Section", ""),
        "support": points_label,
    }


def render_preview_cards_html(items: list[dict[str, str]]) -> str:
    if not items:
        return ""

    fragments = ['<div class="note-stack">']
    for item in items:
        title = escape(item.get("title", "Untitled"))
        href = escape(item.get("href", ""))
        kicker = escape(item.get("kicker", ""))
        meta = escape(item.get("meta", ""))
        summary = escape(item.get("summary", ""))
        excerpt = escape(item.get("excerpt", ""))
        support = escape(item.get("support", ""))

        fragments.append('<article class="note-preview">')
        if kicker or meta:
            meta_parts = " · ".join(part for part in (kicker, meta) if part)
            fragments.append(f'<p class="note-preview__kicker">{meta_parts}</p>')
        if href:
            fragments.append(f'<h4 class="note-preview__title"><a href="{href}">{title}</a></h4>')
        else:
            fragments.append(f'<h4 class="note-preview__title">{title}</h4>')
        if summary:
            fragments.append(f'<p class="note-preview__body">{summary}</p>')
        if excerpt:
            fragments.append(f'<blockquote class="note-preview__quote">“{excerpt}”</blockquote>')
        if support:
            fragments.append(f'<p class="note-preview__support">{support}</p>')
        fragments.append("</article>")

    fragments.append("</div>")
    return "".join(fragments)


def render_preview_cards_markdown(items: list[dict[str, str]], current_content_path: str) -> str:
    if not items:
        return ""

    current_dir = Path(current_content_path).parent
    sections: list[str] = []

    for item in items:
        title = item.get("title", "Untitled")
        content_path = item.get("content_path", "")
        if content_path:
            rel_path = Path(os.path.relpath(content_path, start=current_dir)).as_posix()
            sections.append(f"### [{title}]({rel_path})")
        else:
            sections.append(f"### {title}")

        meta = " · ".join(part for part in (item.get("kicker", ""), item.get("meta", "")) if part)
        if meta:
            sections.extend(["", meta])
        if item.get("summary"):
            sections.extend(["", item["summary"]])
        if item.get("excerpt"):
            sections.extend(["", f'> "{item["excerpt"]}"'])
        if item.get("support"):
            sections.extend(["", item["support"]])
        sections.extend(["", ""])

    return "\n".join(sections).strip()


def render_content_html(blocks: list[dict[str, Any]]) -> str:
    if not blocks:
        return ""

    fragments: list[str] = []
    index = 0

    while index < len(blocks):
        block = blocks[index]
        block_type = block.get("type", "")
        text = escape(block.get("text", ""))
        caption = escape(block.get("caption", ""))
        children_html = render_content_html(block.get("children") or [])

        if block_type in {"bulleted_list_item", "numbered_list_item"}:
            list_type = block_type
            tag = "ul" if list_type == "bulleted_list_item" else "ol"
            items: list[str] = []
            while index < len(blocks) and blocks[index].get("type") == list_type:
                item = blocks[index]
                item_text = escape(item.get("text", ""))
                item_children = render_content_html(item.get("children") or [])
                items.append(f"<li>{item_text}{item_children}</li>")
                index += 1
            fragments.append(f'<{tag} class="content-list">{"".join(items)}</{tag}>')
            continue

        if block_type == "paragraph":
            fragments.append(f"<p>{text}</p>")
        elif block_type == "heading_1":
            fragments.append(f"<h2>{text}</h2>")
        elif block_type == "heading_2":
            fragments.append(f"<h3>{text}</h3>")
        elif block_type == "heading_3":
            fragments.append(f"<h4>{text}</h4>")
        elif block_type == "quote":
            fragments.append(f"<blockquote>{text}</blockquote>")
        elif block_type == "callout":
            icon = escape(block.get("icon", ""))
            fragments.append(f'<div class="content-callout"><strong>{icon}</strong><span>{text}</span></div>')
        elif block_type == "to_do":
            checked = "checked" if block.get("checked") else ""
            fragments.append(
                f'<label class="content-todo"><input type="checkbox" disabled {checked}><span>{text}</span></label>'
            )
        elif block_type == "toggle":
            fragments.append(f"<details><summary>{text or 'More'}</summary>{children_html}</details>")
        elif block_type == "code":
            language = escape(block.get("language", ""))
            fragments.append(f'<pre class="content-code"><code data-language="{language}">{text}</code></pre>')
        elif block_type == "divider":
            fragments.append("<hr>")
        elif block_type in {"bookmark", "embed", "link_preview"}:
            url = escape(block.get("url", ""))
            if url:
                label = text or url
                fragments.append(
                    f'<p><a href="{url}" target="_blank" rel="noreferrer">{label}</a></p>'
                )
        elif block_type in {"image", "file", "pdf", "video", "audio"}:
            url = escape(block.get("url", ""))
            if url:
                media_label = caption or text or block_type.replace("_", " ").title()
                fragments.append(
                    f'<figure class="content-media"><a href="{url}" target="_blank" rel="noreferrer">{media_label}</a></figure>'
                )
        elif text:
            fragments.append(f"<p>{text}</p>")

        if children_html and block_type not in {"toggle", "bulleted_list_item", "numbered_list_item"}:
            fragments.append(children_html)

        index += 1

    return "".join(fragments)


def render_content_markdown(blocks: list[dict[str, Any]], depth: int = 0) -> str:
    if not blocks:
        return ""

    lines: list[str] = []
    index = 0

    while index < len(blocks):
        block = blocks[index]
        block_type = block.get("type", "")
        text = (block.get("text") or "").strip()
        caption = (block.get("caption") or "").strip()
        children = block.get("children") or []

        if block_type in {"bulleted_list_item", "numbered_list_item"}:
            list_type = block_type
            while index < len(blocks) and blocks[index].get("type") == list_type:
                item = blocks[index]
                item_text = (item.get("text") or "").strip()
                marker = "-" if list_type == "bulleted_list_item" else "1."
                indent = "  " * depth
                lines.append(f"{indent}{marker} {item_text}".rstrip())
                nested = render_content_markdown(item.get("children") or [], depth + 1)
                if nested:
                    lines.append(nested)
                index += 1
            lines.append("")
            continue

        if block_type == "paragraph" and text:
            lines.extend([text, ""])
        elif block_type == "heading_1" and text:
            lines.extend([f"# {text}", ""])
        elif block_type == "heading_2" and text:
            lines.extend([f"## {text}", ""])
        elif block_type == "heading_3" and text:
            lines.extend([f"### {text}", ""])
        elif block_type == "quote" and text:
            lines.extend([f"> {text}", ""])
        elif block_type == "callout":
            icon = (block.get("icon") or "").strip()
            prefix = f"{icon} " if icon else ""
            lines.extend([f"> {prefix}{text}".rstrip(), ""])
        elif block_type == "to_do":
            checked = "x" if block.get("checked") else " "
            lines.extend([f"- [{checked}] {text}".rstrip(), ""])
        elif block_type == "toggle":
            heading = text or "More"
            lines.extend([f"#### {heading}", ""])
            nested = render_content_markdown(children, depth)
            if nested:
                lines.extend([nested, ""])
        elif block_type == "code":
            language = (block.get("language") or "").strip()
            lines.extend([f"```{language}", text, "```", ""])
        elif block_type == "divider":
            lines.extend(["---", ""])
        elif block_type in {"bookmark", "embed", "link_preview"}:
            url = (block.get("url") or "").strip()
            if url:
                label = text or url
                lines.extend([f"[{label}]({url})", ""])
        elif block_type in {"image", "file", "pdf", "video", "audio"}:
            url = (block.get("url") or "").strip()
            if url:
                label = caption or text or block_type.replace("_", " ").title()
                lines.extend([f"[{label}]({url})", ""])
        elif text:
            lines.extend([text, ""])

        if children and block_type not in {"toggle", "bulleted_list_item", "numbered_list_item"}:
            nested = render_content_markdown(children, depth)
            if nested:
                lines.extend([nested, ""])

        index += 1

    return "\n".join(line.rstrip() for line in lines).strip()


def build_markdown_link_list(items: list[dict[str, str]], current_content_path: str) -> str:
    current_dir = Path(current_content_path).parent
    lines = [
        f"- [{item['title']}]({Path(os.path.relpath(item['content_path'], start=current_dir)).as_posix()})"
        for item in items
        if item.get("title") and item.get("content_path")
    ]
    return "\n".join(lines)


def format_markdown_value(value: Any) -> str:
    if value is None or value == "":
        return '""'
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    escaped = str(value).replace('"', '\\"')
    return f'"{escaped}"'


def build_frontmatter(metadata: dict[str, Any]) -> str:
    lines = ["---"]
    for key, value in metadata.items():
        if isinstance(value, list):
            lines.append(f"{key}:")
            if value:
                for item in value:
                    lines.append(f"  - {format_markdown_value(item)}")
            else:
                lines.append("  []")
            continue
        lines.append(f"{key}: {format_markdown_value(value)}")
    lines.append("---")
    return "\n".join(lines)


def build_link_list_html(items: list[dict[str, str]]) -> str:
    if not items:
        return ""
    links = "".join(
        f'<li><a href="{escape(item["href"])}">{escape(item["title"])}</a></li>'
        for item in items
        if item.get("href") and item.get("title")
    )
    return f'<ul class="content-list">{links}</ul>' if links else ""


def build_source_fallback_html(record: dict[str, Any]) -> str:
    sections: list[str] = []
    if record.get("Key Takeaway"):
        sections.append(f"<p>{escape(record['Key Takeaway'])}</p>")
    if record.get("Author"):
        sections.append(f"<p><strong>Author:</strong> {escape(record['Author'])}</p>")
    if record.get("captures_preview"):
        sections.append("<h3>Raw captures</h3>")
        sections.append(render_preview_cards_html(record["captures_preview"]))
    elif record.get("captures_info"):
        sections.append("<h3>Captures</h3>")
        sections.append(build_link_list_html(record["captures_info"]))
    if record.get("atom_previews"):
        sections.append("<h3>Key atoms</h3>")
        sections.append(render_preview_cards_html(record["atom_previews"]))
    elif record.get("atoms_info"):
        sections.append("<h3>Linked Atoms</h3>")
        sections.append(build_link_list_html(record["atoms_info"]))
    if record.get("artifact_previews"):
        sections.append("<h3>Published outputs</h3>")
        sections.append(render_preview_cards_html(record["artifact_previews"]))
    elif record.get("artifacts_info"):
        sections.append("<h3>Artifacts Built From This Source</h3>")
        sections.append(build_link_list_html(record["artifacts_info"]))
    return "".join(section for section in sections if section)


def build_capture_fallback_html(record: dict[str, Any]) -> str:
    sections: list[str] = []
    if record.get("summary"):
        sections.append(f"<p>{escape(record['summary'])}</p>")
    if record.get("Excerpt"):
        sections.append(f'<blockquote class="atom-card__quote">“{escape(record["Excerpt"])}”</blockquote>')
    if first_text(record, "Why It Matters", "What Stuck"):
        sections.append(f"<p>{escape(first_text(record, 'Why It Matters', 'What Stuck'))}</p>")
    if record.get("source_previews"):
        sections.append("<h3>Source context</h3>")
        sections.append(render_preview_cards_html(record["source_previews"]))
    elif record.get("sources_info"):
        sections.append("<h3>Source Context</h3>")
        sections.append(build_link_list_html(record["sources_info"]))
    if record.get("atom_previews"):
        sections.append("<h3>Spawned atoms</h3>")
        sections.append(render_preview_cards_html(record["atom_previews"]))
    elif record.get("atoms_info"):
        sections.append("<h3>Spawned Atoms</h3>")
        sections.append(build_link_list_html(record["atoms_info"]))
    if record.get("artifact_previews"):
        sections.append("<h3>Used in artifacts</h3>")
        sections.append(render_preview_cards_html(record["artifact_previews"]))
    elif record.get("artifacts_info"):
        sections.append("<h3>Used In Artifacts</h3>")
        sections.append(build_link_list_html(record["artifacts_info"]))
    return "".join(section for section in sections if section)


def build_atom_fallback_html(record: dict[str, Any]) -> str:
    sections: list[str] = []
    if record.get("Definition"):
        sections.append(f"<p>{escape(record['Definition'])}</p>")
    if record.get("Source Quote"):
        sections.append(f'<blockquote class="atom-card__quote">“{escape(record["Source Quote"])}”</blockquote>')
    if record.get("Because"):
        sections.append(f"<p><strong>Because:</strong> {escape(record['Because'])}</p>")
    if record.get("Boundaries"):
        sections.append(f"<p><strong>Boundaries:</strong> {escape(record['Boundaries'])}</p>")
    if record.get("capture_previews"):
        sections.append("<h3>Capture context</h3>")
        sections.append(render_preview_cards_html(record["capture_previews"]))
    elif record.get("captures_info"):
        sections.append("<h3>Capture Context</h3>")
        sections.append(build_link_list_html(record["captures_info"]))
    if record.get("source_previews"):
        sections.append("<h3>Source grounding</h3>")
        sections.append(render_preview_cards_html(record["source_previews"]))
    elif record.get("sources_info"):
        sections.append("<h3>Source Context</h3>")
        sections.append(build_link_list_html(record["sources_info"]))
    if record.get("artifact_previews"):
        sections.append("<h3>Where this appears</h3>")
        sections.append(render_preview_cards_html(record["artifact_previews"]))
    elif record.get("artifacts_info"):
        sections.append("<h3>Used In Artifacts</h3>")
        sections.append(build_link_list_html(record["artifacts_info"]))
    return "".join(section for section in sections if section)


def build_artifact_fallback_html(record: dict[str, Any]) -> str:
    sections: list[str] = []
    if record.get("Chapter/Section"):
        sections.append(f"<p>{escape(record['Chapter/Section'])}</p>")
    if record.get("source_previews"):
        sections.append("<h3>Source grounding</h3>")
        sections.append(render_preview_cards_html(record["source_previews"]))
    elif record.get("sources_info"):
        sections.append("<h3>Source Material</h3>")
        sections.append(build_link_list_html(record["sources_info"]))
    if record.get("atom_previews"):
        sections.append("<h3>Core ideas in this artifact</h3>")
        sections.append(render_preview_cards_html(record["atom_previews"]))
    elif record.get("atoms_info"):
        sections.append("<h3>Built From</h3>")
        sections.append(build_link_list_html(record["atoms_info"]))
    if record.get("capture_previews"):
        sections.append("<h3>Supporting captures</h3>")
        sections.append(render_preview_cards_html(record["capture_previews"]))
    elif record.get("captures_info"):
        sections.append("<h3>Capture Context</h3>")
        sections.append(build_link_list_html(record["captures_info"]))
    return "".join(section for section in sections if section)


def build_source_fallback_markdown(record: dict[str, Any], current_content_path: str) -> str:
    sections: list[str] = []
    if record.get("Key Takeaway"):
        sections.extend(["## Summary", "", record["Key Takeaway"], ""])
    if record.get("Author"):
        sections.extend(["## Author", "", record["Author"], ""])
    if record.get("captures_preview"):
        previews = render_preview_cards_markdown(record["captures_preview"], current_content_path)
        if previews:
            sections.extend(["## Raw Captures", "", previews, ""])
    elif record.get("captures_info"):
        links = build_markdown_link_list(record["captures_info"], current_content_path)
        if links:
            sections.extend(["## Captures", "", links, ""])
    if record.get("related_sources_info"):
        links = build_markdown_link_list(record["related_sources_info"], current_content_path)
        if links:
            sections.extend(["## Related Sources", "", links, ""])
    if record.get("atom_previews"):
        previews = render_preview_cards_markdown(record["atom_previews"], current_content_path)
        if previews:
            sections.extend(["## Key Atoms", "", previews, ""])
    elif record.get("atoms_info"):
        links = build_markdown_link_list(record["atoms_info"], current_content_path)
        if links:
            sections.extend(["## Linked Atoms", "", links, ""])
    if record.get("artifact_previews"):
        previews = render_preview_cards_markdown(record["artifact_previews"], current_content_path)
        if previews:
            sections.extend(["## Published Outputs", "", previews, ""])
    elif record.get("artifacts_info"):
        links = build_markdown_link_list(record["artifacts_info"], current_content_path)
        if links:
            sections.extend(["## Artifacts", "", links, ""])
    return "\n".join(section for section in sections if section is not None).strip()


def build_capture_fallback_markdown(record: dict[str, Any], current_content_path: str) -> str:
    sections: list[str] = []
    if record.get("summary"):
        sections.extend(["## Summary", "", record["summary"], ""])
    if record.get("Excerpt"):
        sections.extend(["## Excerpt", "", f'> "{record["Excerpt"]}"', ""])
    if first_text(record, "Why It Matters", "What Stuck"):
        sections.extend(["## Why It Matters", "", first_text(record, "Why It Matters", "What Stuck"), ""])
    if record.get("source_previews"):
        previews = render_preview_cards_markdown(record["source_previews"], current_content_path)
        if previews:
            sections.extend(["## Source Context", "", previews, ""])
    elif record.get("sources_info"):
        links = build_markdown_link_list(record["sources_info"], current_content_path)
        if links:
            sections.extend(["## Source Context", "", links, ""])
    if record.get("atom_previews"):
        previews = render_preview_cards_markdown(record["atom_previews"], current_content_path)
        if previews:
            sections.extend(["## Spawned Atoms", "", previews, ""])
    elif record.get("atoms_info"):
        links = build_markdown_link_list(record["atoms_info"], current_content_path)
        if links:
            sections.extend(["## Spawned Atoms", "", links, ""])
    if record.get("artifact_previews"):
        previews = render_preview_cards_markdown(record["artifact_previews"], current_content_path)
        if previews:
            sections.extend(["## Used In Artifacts", "", previews, ""])
    elif record.get("artifacts_info"):
        links = build_markdown_link_list(record["artifacts_info"], current_content_path)
        if links:
            sections.extend(["## Used In Artifacts", "", links, ""])
    return "\n".join(section for section in sections if section is not None).strip()


def build_atom_fallback_markdown(record: dict[str, Any], current_content_path: str) -> str:
    sections: list[str] = []
    if record.get("Definition"):
        sections.extend(["## Definition", "", record["Definition"], ""])
    if record.get("Source Quote"):
        sections.extend(["## Source Quote", "", f'> "{record["Source Quote"]}"', ""])
    if record.get("Because"):
        sections.extend(["## Because", "", record["Because"], ""])
    if record.get("Boundaries"):
        sections.extend(["## Boundaries", "", record["Boundaries"], ""])
    if record.get("capture_previews"):
        previews = render_preview_cards_markdown(record["capture_previews"], current_content_path)
        if previews:
            sections.extend(["## Capture Context", "", previews, ""])
    elif record.get("captures_info"):
        links = build_markdown_link_list(record["captures_info"], current_content_path)
        if links:
            sections.extend(["## Capture Context", "", links, ""])
    if record.get("source_previews"):
        previews = render_preview_cards_markdown(record["source_previews"], current_content_path)
        if previews:
            sections.extend(["## Source Grounding", "", previews, ""])
    elif record.get("sources_info"):
        links = build_markdown_link_list(record["sources_info"], current_content_path)
        if links:
            sections.extend(["## Source Context", "", links, ""])
    if record.get("related_atoms_info"):
        links = build_markdown_link_list(record["related_atoms_info"], current_content_path)
        if links:
            sections.extend(["## Related Atoms", "", links, ""])
    if record.get("artifact_previews"):
        previews = render_preview_cards_markdown(record["artifact_previews"], current_content_path)
        if previews:
            sections.extend(["## Where This Appears", "", previews, ""])
    elif record.get("artifacts_info"):
        links = build_markdown_link_list(record["artifacts_info"], current_content_path)
        if links:
            sections.extend(["## Used In Artifacts", "", links, ""])
    return "\n".join(section for section in sections if section is not None).strip()


def build_artifact_fallback_markdown(record: dict[str, Any], current_content_path: str) -> str:
    sections: list[str] = []
    if record.get("Chapter/Section"):
        sections.extend(["## Scope", "", record["Chapter/Section"], ""])
    if record.get("source_previews"):
        previews = render_preview_cards_markdown(record["source_previews"], current_content_path)
        if previews:
            sections.extend(["## Source Grounding", "", previews, ""])
    elif record.get("sources_info"):
        links = build_markdown_link_list(record["sources_info"], current_content_path)
        if links:
            sections.extend(["## Source Material", "", links, ""])
    if record.get("atom_previews"):
        previews = render_preview_cards_markdown(record["atom_previews"], current_content_path)
        if previews:
            sections.extend(["## Core Ideas In This Artifact", "", previews, ""])
    elif record.get("atoms_info"):
        links = build_markdown_link_list(record["atoms_info"], current_content_path)
        if links:
            sections.extend(["## Built From", "", links, ""])
    if record.get("capture_previews"):
        previews = render_preview_cards_markdown(record["capture_previews"], current_content_path)
        if previews:
            sections.extend(["## Supporting Captures", "", previews, ""])
    elif record.get("captures_info"):
        links = build_markdown_link_list(record["captures_info"], current_content_path)
        if links:
            sections.extend(["## Capture Context", "", links, ""])
    return "\n".join(section for section in sections if section is not None).strip()


def reset_content_directory() -> None:
    if CONTENT_DIR.exists():
        shutil.rmtree(CONTENT_DIR)

    CONTENT_DIR.mkdir(parents=True)
    for folder in ("sources", "captures", "atoms", "artifacts"):
        (CONTENT_DIR / folder).mkdir()


def build_content_indexes(context: dict[str, Any]) -> None:
    index_lines = [
        "# Content",
        "",
        "Generated markdown exports for local reading, editing, and reuse.",
        "",
        f"- Sources: {len(context['sources'])}",
        f"- Captures: {len(context['captures'])}",
        f"- Atoms: {len(context['atoms'])}",
        f"- Artifacts: {len(context['artifacts'])}",
        "",
        "## Sections",
        "",
        "- [Sources](./sources/README.md)",
        "- [Captures](./captures/README.md)",
        "- [Atoms](./atoms/README.md)",
        "- [Artifacts](./artifacts/README.md)",
        "",
    ]
    (CONTENT_DIR / "README.md").write_text("\n".join(index_lines), encoding="utf-8")

    for folder_name, title, records in (
        ("sources", "Sources", context["sources"]),
        ("captures", "Captures", context["captures"]),
        ("atoms", "Atoms", context["atoms"]),
        ("artifacts", "Artifacts", context["artifacts"]),
    ):
        lines = [f"# {title}", ""]
        for record in records:
            name = record.get("display_title") or record.get("Name") or record.get("Claim") or "Untitled"
            lines.append(f"- [{name}](./{Path(record['content_path']).name})")
        lines.append("")
        (CONTENT_DIR / folder_name / "README.md").write_text("\n".join(lines), encoding="utf-8")


def build_markdown_document(entry_kind: str, entry: dict[str, Any]) -> str:
    title = entry.get("display_title") or entry.get("Name") or entry.get("Claim") or "Untitled"
    current_content_path = entry.get("content_path", "")
    metadata: dict[str, Any] = {
        "kind": entry_kind,
        "id": (
            entry.get("Source ID")
            or entry.get("Capture ID")
            or entry.get("Atom ID")
            or entry.get("Artifact ID")
            or entry.get("id", "")
        ),
        "title": title,
        "generated": True,
        "detail_page": entry.get("detail_href", ""),
        "public_url": entry.get("public_url", ""),
        "notion_url": entry.get("notion_url", ""),
        "domains": entry.get("Domain", []),
        "created_time": entry.get("created_time", ""),
        "last_edited_time": entry.get("last_edited_time", ""),
    }

    if entry_kind == "source":
        metadata.update(
            {
                "type": entry.get("Type", ""),
                "author": entry.get("Author", ""),
                "status": entry.get("Status", ""),
                "progress": entry.get("progress_label", ""),
            }
        )
    elif entry_kind == "capture":
        metadata.update(
            {
                "type": entry.get("display_type", ""),
                "status": entry.get("display_status", ""),
                "summary": entry.get("summary", ""),
            }
        )
    elif entry_kind == "atom":
        metadata.update(
            {
                "type": entry.get("Type", ""),
                "confidence": entry.get("Confidence", ""),
                "reuse_count": entry.get("Reuse Count", 0) or 0,
            }
        )
    elif entry_kind == "artifact":
        metadata.update(
            {
                "format": entry.get("Format", ""),
                "status": entry.get("Status", ""),
                "points": entry.get("Points", 0) or 0,
                "date_shipped": entry.get("Date Shipped", ""),
            }
        )

    body = render_content_markdown(entry.get("content") or [])
    if not body:
        if entry_kind == "source":
            body = build_source_fallback_markdown(entry, current_content_path)
        elif entry_kind == "capture":
            body = build_capture_fallback_markdown(entry, current_content_path)
        elif entry_kind == "atom":
            body = build_atom_fallback_markdown(entry, current_content_path)
        else:
            body = build_artifact_fallback_markdown(entry, current_content_path)

    parts = [
        build_frontmatter(metadata),
        "",
        f"# {title}",
        "",
        body.strip(),
        "",
    ]
    return "\n".join(part for part in parts if part is not None).strip() + "\n"


def export_content_markdown(context: dict[str, Any]) -> None:
    reset_content_directory()
    build_content_indexes(context)

    for entry_kind, records in (
        ("source", context["sources"]),
        ("capture", context["captures"]),
        ("atom", context["atoms"]),
        ("artifact", context["artifacts"]),
    ):
        for entry in records:
            output_path = CONTENT_DIR / entry["content_path"]
            output_path.write_text(build_markdown_document(entry_kind, entry), encoding="utf-8")


def reset_dist_directory() -> None:
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)

    DIST_DIR.mkdir(parents=True)
    (DIST_DIR / "data").mkdir()


def copy_static_assets() -> None:
    if not STATIC_DIR.exists():
        return

    shutil.copytree(STATIC_DIR / "css", DIST_DIR / "css", dirs_exist_ok=True)
    shutil.copytree(STATIC_DIR / "js", DIST_DIR / "js", dirs_exist_ok=True)


def build_template_context() -> dict[str, Any]:
    site = get_site_config()
    sources = load_json(DATA_DIR / "sources.json", [])
    captures = load_json(DATA_DIR / "captures.json", [])
    atoms = load_json(DATA_DIR / "atoms.json", [])
    artifacts = load_json(DATA_DIR / "artifacts.json", [])
    graph = load_json(DATA_DIR / "graph.json", DEFAULT_GRAPH)
    default_stats_payload = default_stats(sources, captures, atoms, artifacts)
    loaded_stats = load_json(DATA_DIR / "stats.json", {}) or {}
    stats = {**default_stats_payload, **loaded_stats}
    stats["domains"] = loaded_stats.get("domains", default_stats_payload["domains"])

    payloads = {
        "sources": sources,
        "captures": captures,
        "atoms": atoms,
        "artifacts": artifacts,
        "graph": graph,
        "stats": stats,
        "search_index": build_search_index(captures, atoms, artifacts, sources),
    }

    for name, payload in payloads.items():
        write_json(DIST_DIR / "data" / f"{name}.json", payload)

    source_lookup = {source["id"]: source.get("Name", "Unknown") for source in sources}
    capture_lookup = {capture["id"]: capture_title(capture) for capture in captures}
    atom_lookup = {atom["id"]: atom.get("Claim", "Unknown") for atom in atoms}
    artifact_lookup = {artifact["id"]: artifact.get("Name", "Unknown") for artifact in artifacts}

    source_href_lookup = {source["id"]: build_detail_href("source", source) for source in sources}
    capture_href_lookup = {capture["id"]: build_detail_href("capture", capture) for capture in captures}
    atom_href_lookup = {atom["id"]: build_detail_href("atom", atom) for atom in atoms}
    artifact_href_lookup = {artifact["id"]: build_detail_href("artifact", artifact) for artifact in artifacts}
    source_content_lookup = {source["id"]: build_content_relpath("source", source) for source in sources}
    capture_content_lookup = {capture["id"]: build_content_relpath("capture", capture) for capture in captures}
    atom_content_lookup = {atom["id"]: build_content_relpath("atom", atom) for atom in atoms}
    artifact_content_lookup = {artifact["id"]: build_content_relpath("artifact", artifact) for artifact in artifacts}

    source_capture_ids: dict[str, list[str]] = defaultdict(list)
    atom_capture_ids: dict[str, list[str]] = defaultdict(list)
    artifact_capture_ids: dict[str, list[str]] = defaultdict(list)
    for capture in captures:
        capture_id = capture["id"]
        for source_id in capture_source_ids(capture):
            source_capture_ids[source_id].append(capture_id)
        for atom_id in capture_atom_ids(capture):
            atom_capture_ids[atom_id].append(capture_id)
        for artifact_id in capture_artifact_ids(capture):
            artifact_capture_ids[artifact_id].append(capture_id)

    enriched_sources = enrich_sources(
        sources,
        source_lookup,
        source_href_lookup,
        source_content_lookup,
        capture_lookup,
        capture_href_lookup,
        capture_content_lookup,
        source_capture_ids,
        atom_lookup,
        atom_href_lookup,
        atom_content_lookup,
        artifact_lookup,
        artifact_href_lookup,
        artifact_content_lookup,
    )
    enriched_captures = enrich_captures(
        captures,
        source_lookup,
        source_href_lookup,
        source_content_lookup,
        atom_lookup,
        atom_href_lookup,
        atom_content_lookup,
        artifact_lookup,
        artifact_href_lookup,
        artifact_content_lookup,
    )
    enriched_atoms = enrich_atoms(
        atoms,
        source_lookup,
        source_href_lookup,
        source_content_lookup,
        capture_lookup,
        capture_href_lookup,
        capture_content_lookup,
        atom_capture_ids,
        atom_lookup,
        atom_href_lookup,
        atom_content_lookup,
        artifact_lookup,
        artifact_href_lookup,
        artifact_content_lookup,
    )
    enriched_artifacts = enrich_artifacts(
        artifacts,
        source_lookup,
        source_href_lookup,
        source_content_lookup,
        capture_lookup,
        capture_href_lookup,
        capture_content_lookup,
        artifact_capture_ids,
        atom_lookup,
        atom_href_lookup,
        atom_content_lookup,
    )

    source_preview_lookup = {record["id"]: build_source_preview(record) for record in enriched_sources}
    capture_preview_lookup = {record["id"]: build_capture_preview(record) for record in enriched_captures}
    atom_preview_lookup = {record["id"]: build_atom_preview(record) for record in enriched_atoms}
    artifact_preview_lookup = {record["id"]: build_artifact_preview(record) for record in enriched_artifacts}

    for record in enriched_sources:
        capture_ids = source_capture_ids.get(record["id"], [])
        atom_ids = record.get("Atoms") or []
        artifact_ids = record.get("Artifacts") or []
        record["captures_preview"] = [capture_preview_lookup[item_id] for item_id in capture_ids if item_id in capture_preview_lookup]
        record["atom_previews"] = [atom_preview_lookup[item_id] for item_id in atom_ids if item_id in atom_preview_lookup]
        record["artifact_previews"] = [artifact_preview_lookup[item_id] for item_id in artifact_ids if item_id in artifact_preview_lookup]
        if not render_content_html(record.get("content") or []):
            record["content_html"] = build_source_fallback_html(record)

    for record in enriched_captures:
        source_ids = capture_source_ids(record)
        atom_ids = capture_atom_ids(record)
        artifact_ids = capture_artifact_ids(record)
        record["source_previews"] = [source_preview_lookup[item_id] for item_id in source_ids if item_id in source_preview_lookup]
        record["atom_previews"] = [atom_preview_lookup[item_id] for item_id in atom_ids if item_id in atom_preview_lookup]
        record["artifact_previews"] = [artifact_preview_lookup[item_id] for item_id in artifact_ids if item_id in artifact_preview_lookup]
        if not render_content_html(record.get("content") or []):
            record["content_html"] = build_capture_fallback_html(record)

    for record in enriched_atoms:
        source_ids = record.get("Source") or []
        capture_ids = atom_capture_ids.get(record["id"], [])
        artifact_ids = record.get("Used In Artifacts") or []
        record["source_previews"] = [source_preview_lookup[item_id] for item_id in source_ids if item_id in source_preview_lookup]
        record["capture_previews"] = [capture_preview_lookup[item_id] for item_id in capture_ids if item_id in capture_preview_lookup]
        record["artifact_previews"] = [artifact_preview_lookup[item_id] for item_id in artifact_ids if item_id in artifact_preview_lookup]
        record["related_atom_previews"] = [
            atom_preview_lookup[item_id]
            for item_id in (record.get("Related Atoms") or [])
            if item_id in atom_preview_lookup and item_id != record["id"]
        ]
        if not render_content_html(record.get("content") or []):
            record["content_html"] = build_atom_fallback_html(record)

    for record in enriched_artifacts:
        source_ids = record.get("Source") or []
        capture_ids = artifact_capture_ids.get(record["id"], [])
        atom_ids = record.get("Built From") or []
        record["source_previews"] = [source_preview_lookup[item_id] for item_id in source_ids if item_id in source_preview_lookup]
        record["capture_previews"] = [capture_preview_lookup[item_id] for item_id in capture_ids if item_id in capture_preview_lookup]
        record["atom_previews"] = [atom_preview_lookup[item_id] for item_id in atom_ids if item_id in atom_preview_lookup]
        if not render_content_html(record.get("content") or []):
            record["content_html"] = build_artifact_fallback_html(record)

    source_pipeline = build_source_pipeline(sources)
    capture_pipeline = build_capture_pipeline(captures)
    domain_summary = build_domain_summary(stats)
    active_reads = [source for source in enriched_sources if source.get("Status") in {"Reading", "Extracting"}][:3]
    latest_capture = enriched_captures[0] if enriched_captures else None
    graph_edges = graph.get("edges", [])

    return {
        "site_title": site.title,
        "site_author": site.author,
        "site_url": site.url,
        "site_description": site.description,
        "sources": enriched_sources,
        "captures": enriched_captures,
        "atoms": enriched_atoms,
        "artifacts": enriched_artifacts,
        "stats": stats,
        "source_pipeline": source_pipeline,
        "capture_pipeline": capture_pipeline,
        "domain_summary": domain_summary,
        "featured_atoms": enriched_atoms[:3],
        "latest_artifact": enriched_artifacts[0] if enriched_artifacts else None,
        "latest_source": enriched_sources[0] if enriched_sources else None,
        "latest_capture": latest_capture,
        "active_reads": active_reads,
        "graph_edge_count": len(graph_edges),
        "source_relation_count": sum(1 for edge in graph_edges if edge.get("type") == "related_source"),
        "last_synced_label": format_last_synced(stats.get("last_synced")),
        "now": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }


def render_pages(context: dict[str, Any]) -> None:
    environment = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))

    for template_name in ("index.html", "graph.html", "atoms.html", "captures.html"):
        html = environment.get_template(template_name).render(**context)
        output_path = DIST_DIR / template_name
        output_path.write_text(html, encoding="utf-8")

    detail_template = environment.get_template("detail.html")
    for entry_kind, records in (
        ("source", context["sources"]),
        ("capture", context["captures"]),
        ("atom", context["atoms"]),
        ("artifact", context["artifacts"]),
    ):
        for entry in records:
            html = detail_template.render(
                **context,
                entry=entry,
                entry_kind=entry_kind,
                page_title=f"{entry.get('display_title') or entry.get('Name') or entry.get('Claim') or 'Detail'} · {context['site_title']}",
            )
            (DIST_DIR / entry["detail_href"]).write_text(html, encoding="utf-8")

    fallback_html = environment.get_template("index.html").render(**context)
    (DIST_DIR / "404.html").write_text(fallback_html, encoding="utf-8")
    (DIST_DIR / ".nojekyll").write_text("", encoding="utf-8")


def main() -> int:
    print("Cognitive ETL - Building storefront")
    print("=" * 40)

    reset_dist_directory()
    copy_static_assets()
    print("  [ok] Static assets copied")

    context = build_template_context()
    render_pages(context)
    export_content_markdown(context)

    print(f"  [ok] Search index: {len(load_json(DIST_DIR / 'data' / 'search_index.json', []))} entries")
    print("  [ok] index.html")
    print("  [ok] graph.html")
    print("  [ok] captures.html")
    print("  [ok] atoms.html")
    print(f"  [ok] Markdown content exported to {CONTENT_DIR}")
    print("=" * 40)
    print(f"Built to {DIST_DIR}")
    print(
        f"  {len(context['sources'])} sources, "
        f"{len(context['captures'])} captures, "
        f"{len(context['atoms'])} atoms, "
        f"{len(context['artifacts'])} artifacts"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
