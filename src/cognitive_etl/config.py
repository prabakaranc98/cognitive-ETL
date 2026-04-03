from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT_DIR / "src"


def resolve_path(env_var: str, default: Path) -> Path:
    value = os.getenv(env_var)
    return Path(value).expanduser() if value else default


DATA_DIR = resolve_path("COGNITIVE_ETL_DATA_DIR", ROOT_DIR / "data")
DIST_DIR = resolve_path("COGNITIVE_ETL_DIST_DIR", ROOT_DIR / "dist")
CONTENT_DIR = resolve_path("COGNITIVE_ETL_CONTENT_DIR", ROOT_DIR / "content")
TEMPLATE_DIR = SRC_DIR / "templates"
STATIC_DIR = SRC_DIR / "static"
ENV_FILE = ROOT_DIR / ".env"


def load_environment() -> None:
    load_dotenv(ENV_FILE)


@dataclass(frozen=True)
class SiteConfig:
    title: str
    author: str
    url: str
    description: str


@dataclass(frozen=True)
class NotionConfig:
    api_key: str | None
    version: str
    base_url: str
    database_ids: dict[str, str | None]

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Notion-Version": self.version,
            "Content-Type": "application/json",
        }


def get_site_config() -> SiteConfig:
    load_environment()
    return SiteConfig(
        title=os.getenv("SITE_TITLE", "Cognitive ETL"),
        author=os.getenv("SITE_AUTHOR", "Prabakaran Chandran"),
        url=os.getenv("SITE_URL", ""),
        description=os.getenv("SITE_DESCRIPTION", "A knowledge graph that compounds."),
    )


def get_notion_config() -> NotionConfig:
    load_environment()
    return NotionConfig(
        api_key=os.getenv("NOTION_API_KEY"),
        version="2022-06-28",
        base_url="https://api.notion.com/v1",
        database_ids={
            "sources": os.getenv("SOURCES_DB_ID"),
            "captures": os.getenv("CAPTURES_DB_ID"),
            "atoms": os.getenv("ATOMS_DB_ID"),
            "artifacts": os.getenv("ARTIFACTS_DB_ID"),
        },
    )
