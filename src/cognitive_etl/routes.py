from __future__ import annotations

import re
from typing import Any


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "item"


def build_detail_href(kind: str, record: dict[str, Any]) -> str:
    identifier_map = {
        "source": record.get("Source ID") or record.get("id", ""),
        "capture": record.get("Capture ID") or record.get("id", ""),
        "atom": record.get("Atom ID") or record.get("id", ""),
        "artifact": record.get("Artifact ID") or record.get("id", ""),
    }
    identifier = safe_slug(str(identifier_map.get(kind, record.get("id", ""))))
    return f"{kind}-{identifier}.html"


def build_content_filename(kind: str, record: dict[str, Any]) -> str:
    identifier_map = {
        "source": record.get("Source ID") or record.get("id", ""),
        "capture": record.get("Capture ID") or record.get("id", ""),
        "atom": record.get("Atom ID") or record.get("id", ""),
        "artifact": record.get("Artifact ID") or record.get("id", ""),
    }
    title_map = {
        "source": record.get("Name", ""),
        "capture": record.get("Name", "") or record.get("Title", "") or record.get("Capture", ""),
        "atom": record.get("Claim", ""),
        "artifact": record.get("Name", ""),
    }
    identifier = safe_slug(str(identifier_map.get(kind, record.get("id", ""))))
    title = safe_slug(str(title_map.get(kind, "")))

    if title and title != identifier:
        return f"{identifier}-{title}.md"
    return f"{identifier}.md"


def build_content_relpath(kind: str, record: dict[str, Any]) -> str:
    folder_map = {
        "source": "sources",
        "capture": "captures",
        "atom": "atoms",
        "artifact": "artifacts",
    }
    folder = folder_map.get(kind, "notes")
    return f"{folder}/{build_content_filename(kind, record)}"
