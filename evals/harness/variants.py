"""The variants under comparison: what each one shows the model and with which tools.

All of them get the same task and the same answer protocol, and those that edit use
the same edit and history tools. What changes is the view of the state and, in the
baseline, the read tools (D10 in PRD-queries).
"""

from dataclasses import dataclass
from pathlib import Path

from evals.benchmark.historico import ROOT
from evals.harness.session import HISTORY, View
from src.cad.model import describe_model, load_aqg

APP_INSTRUCTIONS = (
    ROOT / "src" / "ai_modules" / "agents" / "cad_agent" / "instructions.md"
)
EDIT_GROUPS = ["calculo", "edicao", HISTORY]

ID_CONVENTION = """## Ids das tools

As tools endereçam elementos pela posição no AQG, contando de 0: `p<i>` é o item i \
de `solution.placed_objects` e `s<i>` é o item i de `site.elements`."""


@dataclass(frozen=True)
class Variant:
    instructions: str  # the variant's policy, placed before the shared protocol
    view: View  # state -> the text the model reads instead of the AQG
    read_groups: list[str]  # tool groups for the read tasks
    edits: bool  # runs the edit and history tasks


def app_summary(state: str) -> str:
    """The summary the app's agent reads."""
    path = ROOT / state
    return describe_model(load_aqg(path.read_bytes(), path.name))


def raw_aqg(state: str) -> str:
    return (ROOT / state).read_text()


VARIANTS = {
    # This repo's assistant as it is: instructions, summary and the 16 tools.
    "baseline": Variant(
        APP_INSTRUCTIONS.read_text(), app_summary, ["linha_de_base"], edits=False
    ),
    # The whole file, as recorded; only fits the smaller AQGs.
    "raw_aqg": Variant(ID_CONVENTION, raw_aqg, ["calculo"], edits=True),
}


def initial_versions(case: dict) -> list[str]:
    """The versions at the start of the case: the edit history or the original AQG."""
    if "historico" in case:
        return list(case["historico"])
    return [str(Path("data") / "aqg" / case["arquivo"])]
