from dataclasses import dataclass
from pathlib import Path
from typing import Literal

Classification = Literal["normal", "unknown", "shiny_candidate"]


@dataclass(frozen=True)
class EncounterResult:
    classification: Classification
    directory: Path
