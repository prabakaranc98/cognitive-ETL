from __future__ import annotations

import json
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from cognitive_etl.config import DATA_DIR, DIST_DIR, STATIC_DIR, TEMPLATE_DIR, get_site_config

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


def build_search_index(
    atoms: list[dict[str, Any]],
    artifacts: list[dict[str, Any]],
    sources: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    index: list[dict[str, Any]] = []

    for atom in atoms:
        index.append(
            {
                "type": "atom",
                "id": atom.get("Atom ID", atom.get("id", "")),
                "title": atom.get("Claim", ""),
                "body": atom.get("Definition", ""),
                "domain": atom.get("Domain", []),
                "tags": [atom.get("Type", ""), atom.get("Confidence", "")],
                "href": atom.get("url", ""),
            }
        )

    for artifact in artifacts:
        index.append(
            {
                "type": "artifact",
                "id": artifact.get("Artifact ID", artifact.get("id", "")),
                "title": artifact.get("Name", ""),
                "body": artifact.get("Chapter/Section", ""),
                "domain": artifact.get("Domain", []),
                "tags": [artifact.get("Format", ""), artifact.get("Status", "")],
                "href": artifact.get("Artifact URL") or artifact.get("url", ""),
            }
        )

    for source in sources:
        index.append(
            {
                "type": "source",
                "id": source.get("Source ID", source.get("id", "")),
                "title": source.get("Name", ""),
                "body": source.get("Key Takeaway", ""),
                "domain": source.get("Domain", []),
                "tags": [source.get("Type", ""), source.get("Author", "")],
                "href": source.get("Source URL") or source.get("url", ""),
            }
        )

    return index


def default_stats(
    sources: list[dict[str, Any]],
    atoms: list[dict[str, Any]],
    artifacts: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "total_sources": len(sources),
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


def enrich_sources(sources: list[dict[str, Any]], source_lookup: dict[str, str], source_url_lookup: dict[str, str]) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    related_source_map = build_related_source_map(sources)

    for source in sorted(sources, key=lambda item: parse_datetime(item.get("created_time")), reverse=True):
        record = dict(source)
        processed = int(record.get("Chapters Processed") or 0)
        total = int(record.get("Total Chapters") or 0)
        related_ids = sorted(related_source_map.get(record["id"], set()), key=lambda item: source_lookup.get(item, item))

        record["notion_url"] = record.get("url", "")
        record["external_url"] = record.get("Source URL") or record.get("url", "")
        record["progress_label"] = f"{processed}/{total} ch." if total else "No chapter target"
        record["progress_ratio"] = processed / total if total else 0
        record["atom_count"] = len(record.get("Atoms") or [])
        record["artifact_count"] = len(record.get("Artifacts") or [])
        record["related_source_count"] = len(related_ids)
        record["related_sources_info"] = [
            {
                "name": source_lookup.get(related_id, related_id),
                "url": source_url_lookup.get(related_id, ""),
            }
            for related_id in related_ids
        ]
        enriched.append(record)

    return enriched


def enrich_atoms(atoms: list[dict[str, Any]], source_lookup: dict[str, str], artifact_lookup: dict[str, str]) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []

    for atom in sorted(atoms, key=lambda item: parse_datetime(item.get("created_time")), reverse=True):
        record = dict(atom)
        source_ids = record.get("Source") or []
        related_ids = record.get("Related Atoms") or []
        artifact_ids = record.get("Used In Artifacts") or []
        confidence = str(record.get("Confidence") or "")

        record["notion_url"] = record.get("url", "")
        record["source_names"] = [source_lookup.get(source_id, source_id) for source_id in source_ids]
        record["source_summary"] = ", ".join(record["source_names"]) if record["source_names"] else "No source linked"
        record["related_count"] = len(related_ids)
        record["artifact_count"] = len(artifact_ids)
        record["artifact_names"] = [artifact_lookup.get(artifact_id, artifact_id) for artifact_id in artifact_ids]
        record["confidence_score"] = int(confidence[0]) if confidence[:1].isdigit() else 0
        enriched.append(record)

    return enriched


def enrich_artifacts(artifacts: list[dict[str, Any]], source_lookup: dict[str, str], atom_lookup: dict[str, str]) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []

    for artifact in sorted(
        artifacts,
        key=lambda item: parse_datetime(item.get("Date Shipped") or item.get("created_time")),
        reverse=True,
    ):
        record = dict(artifact)
        source_ids = record.get("Source") or []
        atom_ids = record.get("Built From") or []

        record["notion_url"] = record.get("url", "")
        record["external_url"] = record.get("Artifact URL") or record.get("url", "")
        record["source_names"] = [source_lookup.get(source_id, source_id) for source_id in source_ids]
        record["atom_names"] = [atom_lookup.get(atom_id, atom_id) for atom_id in atom_ids]
        record["source_summary"] = ", ".join(record["source_names"]) if record["source_names"] else "No source linked"
        record["built_from_count"] = len(atom_ids)
        enriched.append(record)

    return enriched


def build_source_pipeline(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    counts = Counter((source.get("Status") or "Queue") for source in sources)
    order = ("Queue", "Reading", "Extracting", "Done")
    return [{"label": status, "count": counts.get(status, 0)} for status in order]


def build_domain_summary(stats: dict[str, Any]) -> list[dict[str, Any]]:
    domains = stats.get("domains", {}) or {}
    return [
        {"name": name, "count": count}
        for name, count in sorted(domains.items(), key=lambda item: (-item[1], item[0]))
    ]


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
    atoms = load_json(DATA_DIR / "atoms.json", [])
    artifacts = load_json(DATA_DIR / "artifacts.json", [])
    graph = load_json(DATA_DIR / "graph.json", DEFAULT_GRAPH)
    stats = load_json(DATA_DIR / "stats.json", {}) or default_stats(sources, atoms, artifacts)

    payloads = {
        "sources": sources,
        "atoms": atoms,
        "artifacts": artifacts,
        "graph": graph,
        "stats": stats,
        "search_index": build_search_index(atoms, artifacts, sources),
    }

    for name, payload in payloads.items():
        write_json(DIST_DIR / "data" / f"{name}.json", payload)

    source_lookup = {source["id"]: source.get("Name", "Unknown") for source in sources}
    atom_lookup = {atom["id"]: atom.get("Claim", "Unknown") for atom in atoms}
    artifact_lookup = {artifact["id"]: artifact.get("Name", "Unknown") for artifact in artifacts}

    source_url_lookup = {source["id"]: source.get("url", "") for source in sources}
    enriched_sources = enrich_sources(sources, source_lookup, source_url_lookup)
    enriched_atoms = enrich_atoms(atoms, source_lookup, artifact_lookup)
    enriched_artifacts = enrich_artifacts(artifacts, source_lookup, atom_lookup)
    source_pipeline = build_source_pipeline(sources)
    domain_summary = build_domain_summary(stats)
    active_reads = [source for source in enriched_sources if source.get("Status") in {"Reading", "Extracting"}][:3]
    graph_edges = graph.get("edges", [])

    return {
        "site_title": site.title,
        "site_author": site.author,
        "site_url": site.url,
        "site_description": site.description,
        "sources": enriched_sources,
        "atoms": enriched_atoms,
        "artifacts": enriched_artifacts,
        "stats": stats,
        "source_pipeline": source_pipeline,
        "domain_summary": domain_summary,
        "featured_atoms": enriched_atoms[:3],
        "latest_artifact": enriched_artifacts[0] if enriched_artifacts else None,
        "latest_source": enriched_sources[0] if enriched_sources else None,
        "active_reads": active_reads,
        "graph_edge_count": len(graph_edges),
        "source_relation_count": sum(1 for edge in graph_edges if edge.get("type") == "related_source"),
        "last_synced_label": format_last_synced(stats.get("last_synced")),
        "now": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }


def render_pages(context: dict[str, Any]) -> None:
    environment = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))

    for template_name in ("index.html", "graph.html", "atoms.html"):
        html = environment.get_template(template_name).render(**context)
        output_path = DIST_DIR / template_name
        output_path.write_text(html, encoding="utf-8")

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

    print(f"  [ok] Search index: {len(load_json(DIST_DIR / 'data' / 'search_index.json', []))} entries")
    print("  [ok] index.html")
    print("  [ok] graph.html")
    print("  [ok] atoms.html")
    print("=" * 40)
    print(f"Built to {DIST_DIR}")
    print(
        f"  {len(context['sources'])} sources, "
        f"{len(context['atoms'])} atoms, "
        f"{len(context['artifacts'])} artifacts"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
