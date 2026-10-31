"""The public data sources listed in data/sources.yaml (spec section 4)."""

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, HttpUrl

Role = Literal["dev", "test", "stretch", "context", "knowledge", "reference"]


class Source(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    role: Role
    kind: Literal["file", "landing_page", "web_page"]  # web_page: saved as text, cited as page 1
    url: HttpUrl
    evidence: bool = False  # manufacturer literature indexed as product documents for evidence search
    notes: str | None = None


class DuplicateSourceError(ValueError):
    pass


class _UniqueKeyLoader(yaml.SafeLoader):
    """SafeLoader that refuses duplicate keys; plain PyYAML silently keeps the last one."""


def _construct_unique_mapping(loader: _UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False) -> dict[Any, Any]:
    seen = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise DuplicateSourceError(f"duplicate key in sources file: {key!r}")
        seen.add(key)
    return loader.construct_mapping(node, deep=deep)


_UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_unique_mapping)


def load_sources(path: Path) -> list[Source]:
    data = yaml.load(path.read_text(encoding="utf-8"), Loader=_UniqueKeyLoader)
    return [Source(id=source_id, **entry) for source_id, entry in data["sources"].items()]
