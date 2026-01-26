from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    data_dir: Path


def get_settings() -> Settings:
    # 1) env var
    env = os.getenv("DASHMONEY_DATA_DIR")
    if env and env.strip():
        p = Path(env).expanduser()
    else:
        # 2) default: backend/data
        # app/settings.py -> app/ -> backend/
        p = Path(__file__).resolve().parents[2] / "data"

    # Le dossier data peut être créé automatiquement (ça ne viole pas le "strict")
    p.mkdir(parents=True, exist_ok=True)
    return Settings(data_dir=p)
