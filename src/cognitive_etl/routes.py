from __future__ import annotations

import re
from typing import Any


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "item"


def build_detail_href(kind: str, record: dict[str, Any]) -> str:
    identifier_map = {
        "source": record.get("Source ID") or record.get("id", ""),
        "atom": record.get("Atom ID") or record.get("id", ""),
        "artifact": record.get("Artifact ID") or record.get("id", ""),
    }
    identifier = safe_slug(str(identifier_map.get(kind, record.get("id", ""))))
    return f"{kind}-{identifier}.html"
