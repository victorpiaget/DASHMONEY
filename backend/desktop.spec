# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec pour DashMoney Desktop (backend FastAPI bundlé).

Build :
    cd backend
    poetry run pyinstaller desktop.spec --noconfirm

Sortie :
    dist/dashmoney-backend/
        ├── dashmoney-backend.exe   ← le sidecar Tauri
        ├── _internal/
        │   ├── alembic.ini
        │   ├── migrations/...
        │   └── (toutes les libs Python)
        └── ...

Ne PAS tenter --onefile : extraction dans %TEMP% à chaque lancement, latence
de 3-5s, et casse l'usage en sidecar Tauri qui attend un .exe + ses ressources
en place.
"""
from PyInstaller.utils.hooks import collect_all, collect_submodules

# ── Hidden imports ────────────────────────────────────────────────────────
# Uvicorn résout dynamiquement workers/loops/protocols/lifespan via importlib :
# PyInstaller ne les voit pas dans le graphe statique, on les force.
_uvicorn_hidden = collect_submodules("uvicorn")

# SQLAlchemy charge ses dialectes via entry_points/lazy import.
_sqlalchemy_hidden = collect_submodules("sqlalchemy.dialects")

# bcrypt + passlib (au cas où passlib subsistait dans le code) : leurs backends
# sont chargés via stevedore-like discovery.
_bcrypt_hidden = collect_submodules("bcrypt")

# yfinance + pandas + numpy : import dynamique de scipy/pandas internals.
_yfinance_hidden = collect_submodules("yfinance")

# APScheduler résout aussi ses jobstores/triggers dynamiquement.
_apscheduler_hidden = collect_submodules("apscheduler")

hidden_imports = (
    _uvicorn_hidden
    + _sqlalchemy_hidden
    + _bcrypt_hidden
    + _yfinance_hidden
    + _apscheduler_hidden
    + [
        # Dialecte SQLite pur (déjà dans submodules mais on s'assure)
        "sqlalchemy.dialects.sqlite",
        # Drivers DB-API : sqlite3 est stdlib, mais psycopg peut être nécessaire
        # si l'utilisateur force une URL Postgres sur le binaire. Optionnel —
        # commenter pour réduire la taille si on est 100% SQLite.
        "psycopg",
        "psycopg.pq",
        # Email validators (utilisés par Pydantic EmailStr)
        "email_validator",
    ]
)

# ── Datas (fichiers non-Python à embarquer) ──────────────────────────────
# alembic.ini + migrations/ doivent être livrés à côté du binaire pour que
# `alembic stamp head` fonctionne au bootstrap d'une nouvelle SQLite (tâche #8).
datas = [
    ("alembic.ini", "."),
    ("migrations", "migrations"),
]

# yfinance embarque ses propres données (timezone, headers user-agent, etc.)
_yf_datas, _yf_binaries, _yf_hidden_extra = collect_all("yfinance")
datas += _yf_datas
hidden_imports += _yf_hidden_extra

# Idem pour pandas (dépendance de yfinance) — collect_all gère ses extensions C.
_pd_datas, _pd_binaries, _pd_hidden_extra = collect_all("pandas")
datas += _pd_datas
hidden_imports += _pd_hidden_extra

# ── Build config ──────────────────────────────────────────────────────────
block_cipher = None

a = Analysis(
    ["desktop_main.py"],
    pathex=[],
    binaries=_yf_binaries + _pd_binaries,
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # On exclut explicitement les libs lourdes non-utilisées en runtime
        "tkinter",
        "matplotlib",
        "IPython",
        "jupyter",
        "pytest",
        "alembic.testing",
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="dashmoney-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,         # UPX peut corrompre des .pyd, on évite pour MVP
    console=True,      # Console visible pour debug ; on passera False quand stable
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="dashmoney-backend",
)
