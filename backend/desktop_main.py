"""
Entry point de la version desktop de DashMoney.

Lancé soit directement (`poetry run python desktop_main.py`) soit via le binaire
PyInstaller (`dashmoney-backend.exe`). Dans les deux cas, on s'assure que :
    - DASHMONEY_MODE = "desktop" (par défaut)
    - DASHMONEY_DATABASE_URL pointe sur ~/.dashmoney/data.db si rien n'est fourni
      (résolu par app.db._default_desktop_database_url())
    - DASHMONEY_SECRET_KEY est persisté dans ~/.dashmoney/.secret_key pour que
      les tokens JWT survivent aux redémarrages.

Tauri (tâche suivante) lancera ce binaire en sidecar et lui passera un port
dynamique via une variable d'env DASHMONEY_PORT.
"""
from __future__ import annotations

import os
import secrets
import sys
from pathlib import Path


def _data_dir() -> Path:
    # Aligné avec app.db.default_desktop_data_dir : %APPDATA%/DashMoney sur
    # Windows, ~/Library/Application Support/DashMoney sur macOS, etc.
    # On délègue à app.db pour avoir une seule source de vérité — et pour
    # bénéficier de la migration automatique depuis ~/.dashmoney/ qui se
    # déclenche dès que `migrate_legacy_data_dir` est appelée par le
    # lifespan FastAPI (qui appelle get_database_url → migration auto).
    from app.db import default_desktop_data_dir
    return default_desktop_data_dir()


def _ensure_secret_key() -> None:
    if os.environ.get("DASHMONEY_SECRET_KEY"):
        return
    key_path = _data_dir() / ".secret_key"
    if not key_path.exists():
        key_path.write_text(secrets.token_urlsafe(48), encoding="utf-8")
        # Sur Windows, pas de chmod 600 portable ; on s'appuie sur les ACL
        # par défaut du profil utilisateur (le fichier est dans %USERPROFILE%).
    os.environ["DASHMONEY_SECRET_KEY"] = key_path.read_text(encoding="utf-8").strip()


def _setup_env() -> None:
    os.environ.setdefault("DASHMONEY_MODE", "desktop")
    # Migration AVANT _ensure_secret_key : sinon on générerait un nouveau
    # .secret_key dans le nouveau dossier et la migration ferait un no-op
    # parce que le fichier existerait déjà côté cible. L'ordre garantit que
    # l'ancien .secret_key est récupéré et que les JWT restent valides.
    from app.db import migrate_legacy_data_dir
    migrate_legacy_data_dir()
    _ensure_secret_key()


def _resolve_port() -> int:
    raw = os.environ.get("DASHMONEY_PORT", "").strip()
    if not raw:
        return 8000
    try:
        return int(raw)
    except ValueError:
        print(f"⚠️  DASHMONEY_PORT={raw!r} invalide, fallback sur 8000.", file=sys.stderr)
        return 8000


def main() -> int:
    _setup_env()

    # Import EXPLICITE de l'application FastAPI (et non passage en string à
    # uvicorn). Raison : PyInstaller analyse statiquement le graphe d'imports
    # et ne suit pas les strings ; passer "app.api.main:app" en argument
    # produit un bundle sans le module `app`. L'import direct force la
    # collecte de tout le graphe app.* au moment du build.
    from app.api.main import app as fastapi_app

    import uvicorn

    port = _resolve_port()
    print(f"[dashmoney-desktop] mode={os.environ['DASHMONEY_MODE']} port={port}", flush=True)

    uvicorn.run(
        fastapi_app,
        host="127.0.0.1",
        port=port,
        log_level="info",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
