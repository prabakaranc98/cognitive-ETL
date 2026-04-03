from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import requests

from cognitive_etl.config import DATA_DIR, NotionConfig, get_notion_config
from cognitive_etl.routes import build_detail_href


class NotionClient:
    def __init__(self, config: NotionConfig) -> None:
        self.config = config
        self.session = requests.Session()
        self.session.headers.update(config.headers)

    def query_database(self, database_id: str) -> list[dict[str, Any]]:
        pages: list[dict[str, Any]] = []
        has_more = True
        start_cursor: str | None = None

        while has_more:
            payload: dict[str, Any] = {"page_size": 100}
            if start_cursor:
                payload["start_cursor"] = start_cursor

            response = self.session.post(
                f"{self.config.base_url}/databases/{database_id}/query",
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            pages.extend(data["results"])
            has_more = data.get("has_more", False)
            start_cursor = data.get("next_cursor")

        return pages

    def list_block_children(self, block_id: str) -> list[dict[str, Any]]:
        blocks: list[dict[str, Any]] = []
        has_more = True
        start_cursor: str | None = None

        while has_more:
            params: dict[str, Any] = {"page_size": 100}
            if start_cursor:
                params["start_cursor"] = start_cursor

            response = self.session.get(
                f"{self.config.base_url}/blocks/{block_id}/children",
                params=params,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()

            blocks.extend(data["results"])
            has_more = data.get("has_more", False)
            start_cursor = data.get("next_cursor")

        return blocks


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def extract_property(prop: dict[str, Any]) -> Any:
    prop_type = prop.get("type")

    if prop_type == "title":
        return "".join(item.get("plain_text", "") for item in prop.get("title", []))
    if prop_type == "rich_text":
        return "".join(item.get("plain_text", "") for item in prop.get("rich_text", []))
    if prop_type == "number":
        return prop.get("number")
    if prop_type == "select":
        selected = prop.get("select")
        return selected["name"] if selected else None
    if prop_type == "multi_select":
        return [item["name"] for item in prop.get("multi_select", [])]
    if prop_type == "date":
        date_payload = prop.get("date")
        return date_payload["start"] if date_payload else None
    if prop_type == "url":
        return prop.get("url")
    if prop_type == "checkbox":
        return prop.get("checkbox", False)
    if prop_type == "relation":
        return [item["id"] for item in prop.get("relation", [])]
    if prop_type == "unique_id":
        unique_id = prop.get("unique_id", {})
        prefix = unique_id.get("prefix", "")
        number = unique_id.get("number", 0)
        return f"{prefix}-{number}" if prefix else str(number)
    if prop_type == "formula":
        formula = prop.get("formula", {})
        formula_type = formula.get("type")
        return formula.get(formula_type)
    if prop_type == "rollup":
        rollup = prop.get("rollup", {})
        rollup_type = rollup.get("type")
        return rollup.get(rollup_type)

    return None


def parse_page(page: dict[str, Any]) -> dict[str, Any]:
    parsed: dict[str, Any] = {
        "id": page["id"],
        "url": page.get("url", ""),
        "created_time": page.get("created_time", ""),
        "last_edited_time": page.get("last_edited_time", ""),
    }

    for key, prop in page.get("properties", {}).items():
        parsed[key] = extract_property(prop)

    return parsed


def extract_rich_text_plain(rich_text: list[dict[str, Any]]) -> str:
    return "".join(item.get("plain_text", "") for item in rich_text)


def extract_file_url(payload: dict[str, Any]) -> str:
    file_type = payload.get("type")
    if file_type in {"external", "file"}:
        return payload.get(file_type, {}).get("url", "")
    return ""


def normalize_block(block: dict[str, Any], children: list[dict[str, Any]]) -> dict[str, Any] | None:
    block_type = block.get("type")
    payload = block.get(block_type, {})
    normalized: dict[str, Any] = {"type": block_type}

    rich_text = payload.get("rich_text", [])
    text = extract_rich_text_plain(rich_text)
    if text:
        normalized["text"] = text

    if block_type == "to_do":
        normalized["checked"] = payload.get("checked", False)
    if block_type == "code":
        normalized["language"] = payload.get("language", "")
    if block_type == "callout":
        icon = payload.get("icon", {})
        if icon.get("type") == "emoji":
            normalized["icon"] = icon.get("emoji", "")
    if block_type in {"bookmark", "embed", "link_preview"}:
        normalized["url"] = payload.get("url", "")
    if block_type in {"image", "file", "pdf", "video", "audio"}:
        normalized["url"] = extract_file_url(payload)
        caption = extract_rich_text_plain(payload.get("caption", []))
        if caption:
            normalized["caption"] = caption

    if children:
        normalized["children"] = children

    if block_type == "divider":
        return normalized

    if any(key in normalized for key in ("text", "url", "children", "caption")):
        return normalized

    return None


def fetch_page_content(client: NotionClient, block_id: str, depth: int = 0, max_depth: int = 4) -> list[dict[str, Any]]:
    if depth > max_depth:
        return []

    children: list[dict[str, Any]] = []
    for block in client.list_block_children(block_id):
        nested_children = fetch_page_content(client, block["id"], depth + 1, max_depth) if block.get("has_children") else []
        normalized = normalize_block(block, nested_children)
        if normalized:
            children.append(normalized)

    return children


def flatten_content_text(blocks: list[dict[str, Any]]) -> str:
    parts: list[str] = []

    for block in blocks:
        text = block.get("text")
        if text:
            parts.append(text)
        caption = block.get("caption")
        if caption:
            parts.append(caption)
        nested = block.get("children") or []
        if nested:
            parts.append(flatten_content_text(nested))

    return "\n".join(part for part in parts if part).strip()


def sync_database(client: NotionClient, name: str, database_id: str) -> list[dict[str, Any]]:
    print(f"  [sync] {name}")
    pages = client.query_database(database_id)
    records: list[dict[str, Any]] = []

    for page in pages:
        record = parse_page(page)
        content = fetch_page_content(client, page["id"])
        record["content"] = content
        record["content_plain"] = flatten_content_text(content)
        records.append(record)

    print(f"    [ok] {len(records)} records")
    return records


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


def resolve_relations(
    sources: list[dict[str, Any]],
    atoms: list[dict[str, Any]],
    artifacts: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    source_lookup = {source["id"]: source.get("Name", "Unknown") for source in sources}
    atom_lookup = {atom["id"]: atom.get("Claim", "Unknown") for atom in atoms}
    artifact_lookup = {artifact["id"]: artifact.get("Name", "Unknown") for artifact in artifacts}
    related_source_map = build_related_source_map(sources)

    for source in sources:
        related_ids = sorted(related_source_map.get(source["id"], set()), key=lambda item: source_lookup.get(item, item))
        source["_related_source_names"] = [source_lookup.get(source_id, source_id) for source_id in related_ids]

    for atom in atoms:
        source_ids = atom.get("Source", []) or []
        related_ids = atom.get("Related Atoms", []) or []
        artifact_ids = atom.get("Used In Artifacts", []) or []

        atom["_source_names"] = [source_lookup.get(source_id, source_id) for source_id in source_ids]
        atom["_related_claims"] = [atom_lookup.get(atom_id, atom_id) for atom_id in related_ids]
        atom["_artifact_names"] = [artifact_lookup.get(artifact_id, artifact_id) for artifact_id in artifact_ids]

    for artifact in artifacts:
        built_from_ids = artifact.get("Built From", []) or []
        source_ids = artifact.get("Source", []) or []
        artifact["_atom_claims"] = [atom_lookup.get(atom_id, atom_id) for atom_id in built_from_ids]
        artifact["_source_names"] = [source_lookup.get(source_id, source_id) for source_id in source_ids]

    edges: list[dict[str, Any]] = []
    seen_source_edges: set[tuple[str, str]] = set()
    for source in sources:
        source_name = source_lookup.get(source["id"], source["id"])
        for related_id in related_source_map.get(source["id"], set()):
            related_name = source_lookup.get(related_id, related_id)
            edge_key = tuple(sorted((source_name, related_name)))
            if source_name == related_name or edge_key in seen_source_edges:
                continue
            seen_source_edges.add(edge_key)
            edges.append(
                {
                    "source": source_name,
                    "target": related_name,
                    "type": "related_source",
                }
            )

    for atom in atoms:
        atom_id = atom.get("Atom ID", atom["id"])

        for source_id in atom.get("Source", []) or []:
            edges.append(
                {
                    "source": atom_id,
                    "target": source_lookup.get(source_id, source_id),
                    "type": "from_source",
                }
            )

        for related_id in atom.get("Related Atoms", []) or []:
            related_atom_id = next(
                (candidate.get("Atom ID", candidate["id"]) for candidate in atoms if candidate["id"] == related_id),
                related_id,
            )
            edges.append(
                {
                    "source": atom_id,
                    "target": related_atom_id,
                    "type": "related",
                }
            )

    nodes: list[dict[str, Any]] = []
    for atom in atoms:
        nodes.append(
            {
                "id": atom.get("Atom ID", atom["id"]),
                "label": atom.get("Claim", "?"),
                "url": atom.get("url", ""),
                "type": "atom",
                "domain": atom.get("Domain", []),
                "confidence": atom.get("Confidence"),
                "atom_type": atom.get("Type"),
                "reuse_count": atom.get("Reuse Count", 0) or 0,
            }
        )

    for source in sources:
        nodes.append(
            {
                "id": source.get("Name", source["id"]),
                "label": source.get("Name", "?"),
                "url": source.get("Source URL") or source.get("url", ""),
                "type": "source",
                "source_type": source.get("Type"),
                "domain": source.get("Domain", []),
            }
        )

    return {"nodes": nodes, "edges": edges}


def build_stats(
    sources: list[dict[str, Any]],
    atoms: list[dict[str, Any]],
    artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    total_points = sum(artifact.get("Points", 0) or 0 for artifact in artifacts)
    total_reuse = sum(atom.get("Reuse Count", 0) or 0 for atom in atoms)
    shipped_artifacts = [artifact for artifact in artifacts if artifact.get("Status") == "Shipped"]

    domains: dict[str, int] = {}
    for atom in atoms:
        for domain in atom.get("Domain", []) or []:
            domains[domain] = domains.get(domain, 0) + 1

    return {
        "total_sources": len(sources),
        "total_atoms": len(atoms),
        "total_artifacts": len(artifacts),
        "shipped_artifacts": len(shipped_artifacts),
        "total_points": total_points,
        "total_reuse": total_reuse,
        "domains": domains,
        "last_synced": utc_timestamp(),
    }


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, default=str)


def sync_notion(target: str | None = None) -> int:
    config = get_notion_config()
    if not config.api_key:
        print("Missing NOTION_API_KEY. Copy .env.example to .env and fill in your values.")
        return 1

    if target and target not in config.database_ids:
        valid_targets = ", ".join(sorted(config.database_ids))
        print(f"Unsupported database '{target}'. Choose one of: {valid_targets}")
        return 1

    client = NotionClient(config)

    print("Cognitive ETL - Notion sync")
    print("=" * 40)

    results: dict[str, list[dict[str, Any]]] = {}
    for name, database_id in config.database_ids.items():
        if target and name != target:
            continue
        if not database_id:
            print(f"  [skip] {name}: database ID not set")
            continue
        results[name] = sync_database(client, name, database_id)

    for name, payload in results.items():
        output_path = DATA_DIR / f"{name}.json"
        write_json(output_path, payload)
        print(f"  [write] {output_path}")

    if all(name in results for name in ("sources", "atoms", "artifacts")):
        graph = resolve_relations(results["sources"], results["atoms"], results["artifacts"])
        write_json(DATA_DIR / "graph.json", graph)
        print(f"  [write] {DATA_DIR / 'graph.json'}")

        stats = build_stats(results["sources"], results["atoms"], results["artifacts"])
        write_json(DATA_DIR / "stats.json", stats)
        print(f"  [write] {DATA_DIR / 'stats.json'}")

    print("=" * 40)
    print("Sync complete.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sync Cognitive ETL data from Notion.")
    parser.add_argument(
        "--db",
        choices=("sources", "atoms", "artifacts"),
        help="Sync only a single database.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return sync_notion(target=args.db)


if __name__ == "__main__":
    raise SystemExit(main())
