"""Construção experimental da C1, compartilhada pelos notebooks de AQG.

Preserva registros e suas origens; interpretação de domínio fica em outra etapa.
"""

from dataclasses import dataclass
from typing import Any, Literal

from src.cad.model import _matches


@dataclass(frozen=True)
class SourceRef:
    snapshot: str
    pointer: str

    @property
    def id(self) -> str:
        return f"{self.snapshot}#{self.pointer}"


@dataclass
class Record:
    source: SourceRef
    data: dict[str, Any]

    @property
    def id(self) -> str:
        return self.source.id


@dataclass
class Family:
    record: Record
    class_path: str | None
    kind: str | None


@dataclass(frozen=True)
class FamilyLink:
    status: Literal["resolved", "missing", "ambiguous"]
    candidates: tuple[str, ...]
    rule: str = "prefixo por segmento nos dois sentidos"


@dataclass
class Placement:
    record: Record
    kind: str | None
    family: FamilyLink | None  # Só PlacedFamily estabelece este vínculo.


@dataclass
class Site:
    record: Record
    inputs: list[Record]
    processed_info: list[Record]
    elements: list[Record]


@dataclass
class Solution:
    record: Record
    placements: dict[str, Placement]
    outputs: list[Record]
    annotations: list[Record]


@dataclass
class SemanticMemory:
    filename: str
    snapshot: str
    exporter_version: str | None
    root: Record
    site: Site
    families: dict[str, Family]
    solution: Solution
    program: list[Record]


MISSING = object()


REFERENCE_PATHS = {
    "/solution/road_network",
    "/site/analysis/inclination_groups",
    "/site/analysis/region_groups",
}


def child_path(parent: str, key: str | int) -> str:
    escaped = str(key).replace("~", "~0").replace("/", "~1")
    return f"{parent}/{escaped}"


def lookup(tree: Any, pointer: str) -> Any:
    value = tree
    for part in pointer.split("/")[1:] if pointer else []:
        key = part.replace("~1", "/").replace("~0", "~")
        if isinstance(value, dict):
            value = value.get(key, MISSING)
        elif isinstance(value, list) and key.isdigit() and int(key) < len(value):
            value = value[int(key)]
        else:
            return MISSING
    return value


def project_data(value: Any, snapshot: str, pointer: str = "") -> Any:
    geometry = pointer.endswith(("/geometry", "/faces"))
    annotation_line = pointer.startswith("/solution/annotations/") and pointer.endswith(
        "/line"
    )
    if isinstance(value, dict | list) and (
        geometry or annotation_line or pointer in REFERENCE_PATHS
    ):
        return SourceRef(snapshot, pointer)
    if isinstance(value, dict):
        return {
            key: project_data(item, snapshot, child_path(pointer, key))
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [
            project_data(item, snapshot, child_path(pointer, i))
            for i, item in enumerate(value)
        ]
    return value


def build_memory(project: dict, filename: str, snapshot: str) -> SemanticMemory:
    projected = project_data(project, snapshot)

    def record(pointer: str) -> Record:
        value = lookup(projected, pointer)
        if not isinstance(value, dict):
            raise ValueError(f"{filename}: esperado objeto em {pointer!r}")
        return Record(SourceRef(snapshot, pointer), value)

    def records(pointer: str) -> list[Record]:
        value = lookup(projected, pointer)
        if value is MISSING or value is None:
            return []  # O estado original permanece no registro pai.
        if not isinstance(value, list):
            raise ValueError(f"{filename}: esperada lista em {pointer}")
        return [record(child_path(pointer, i)) for i in range(len(value))]

    families = {}
    for item in records("/families"):
        properties = item.data.get("properties") or {}
        families[item.id] = Family(
            item, item.data.get("class_path"), properties.get("type")
        )

    placements = {}
    for item in records("/solution/placed_objects"):
        kind = item.data.get("type")
        link = None
        if kind == "PlacedFamily":
            hid = item.data.get("hid")
            candidates = tuple(
                fid
                for fid, family in families.items()
                if isinstance(hid, str)
                and hid
                and isinstance(family.class_path, str)
                and family.class_path
                and (
                    _matches(hid, family.class_path) or _matches(family.class_path, hid)
                )
            )
            status = (
                ("resolved" if len(candidates) == 1 else "ambiguous")
                if candidates
                else "missing"
            )
            link = FamilyLink(status, candidates)
        placements[item.id] = Placement(item, kind, link)

    return SemanticMemory(
        filename=filename,
        snapshot=snapshot,
        exporter_version=project.get("version"),
        root=record(""),
        site=Site(
            record("/site"),
            records("/site/inputs"),
            records("/site/processed_info"),
            records("/site/elements"),
        ),
        families=families,
        solution=Solution(
            record("/solution"),
            placements,
            records("/solution/outputs"),
            records("/solution/annotations"),
        ),
        program=records("/archprog"),
    )


def inspect_field(record: Record, *keys: str) -> dict:
    relative = ""
    for key in keys:
        relative = child_path(relative, key)
    value = lookup(record.data, relative)
    state = (
        "missing"
        if value is MISSING
        else "null"
        if value is None
        else "referenced"
        if isinstance(value, SourceRef)
        else "present"
    )
    return {
        "campo": "/".join(keys),
        "estado": state,
        "valor": None if value is MISSING else value,
        "origem": record.source.pointer + relative,
        "snapshot": record.source.snapshot,
    }


def restore(value: Any, project: dict, snapshot: str) -> Any:
    if isinstance(value, SourceRef):
        assert value.snapshot == snapshot
        original = lookup(project, value.pointer)
        assert original is not MISSING, value.pointer
        return original
    if isinstance(value, dict):
        return {key: restore(item, project, snapshot) for key, item in value.items()}
    if isinstance(value, list):
        return [restore(item, project, snapshot) for item in value]
    return value


def references(value: Any) -> list[SourceRef]:
    if isinstance(value, SourceRef):
        return [value]
    if isinstance(value, dict):
        return [ref for item in value.values() for ref in references(item)]
    if isinstance(value, list):
        return [ref for item in value for ref in references(item)]
    return []
