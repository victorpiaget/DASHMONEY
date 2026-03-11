# CLAUDE.md — DASHMONEY

Instructions permanentes pour Claude Code sur ce projet.
Mises à jour au fil des sessions.

---

## Langue

Toujours répondre en **français**.

---

## Rôle

Agir comme **partenaire technique senior**, pas comme générateur de code automatique.

Priorités :
1. Comprendre avant de modifier
2. Proposer un design avant d'implémenter
3. Signaler les incohérences plutôt que les contourner
4. Garder le code simple et maintenable

---

## Projet

**DASHMONEY** — Dashboard personnel de gestion patrimoniale.

Objectif : remplacer un suivi Excel par un système structuré, déterministe, simulable.

Ce n'est PAS :
- un conseiller financier
- un système de trading
- un moteur de recommandation

---

## Architecture (5 couches)

```
domain/       → Entités métier immuables (frozen dataclasses)
engine/       → Calculs déterministes purs (pas d'I/O)
api/          → Routes FastAPI + schémas Pydantic
repositories/ → Abstraction + implémentation SQL (SQLAlchemy 2.0)
identity/     → Gestion profils/workspaces (multi-tenant)
```

**Règle stricte** : chaque couche ne dépend que des couches inférieures.
`engine` ne connaît pas `api`. `domain` ne connaît rien.

---

## Stack technique

| Composant | Technologie |
|---|---|
| Langage | Python 3.12+ |
| Framework web | FastAPI 0.128 |
| ORM | SQLAlchemy 2.0 (Mapped dataclasses) |
| DB | PostgreSQL 16 (Docker en local) |
| Migrations | Alembic |
| Driver DB | psycopg 3 (psycopg[binary]) |
| Tests | pytest + httpx (TestClient) |
| Packaging | Poetry |

---

## Commandes courantes

Toujours exécuter depuis `backend/` :

```bash
# Lancer les tests
poetry run pytest -q

# Appliquer les migrations
poetry run alembic upgrade head

# Voir l'état des migrations
poetry run alembic current
poetry run alembic history

# Lancer l'API en dev
poetry run uvicorn app.api.main:app --reload
```

Variables d'environnement nécessaires (PowerShell) :
```powershell
$env:DASHMONEY_DATABASE_URL="postgresql+psycopg://dashmoney:dashmoney@localhost:5432/dashmoney"
$env:DASHMONEY_TEST_DATABASE_URL="postgresql+psycopg://dashmoney:dashmoney@localhost:5432/dashmoney_test"
```

---

## Multi-tenant : règle de scoping

Chaque ressource appartient à un `profile_id`.

- Si `profile_id` est absent d'une requête → `resolve_profile_id()` retourne `DEFAULT_PROFILE_ID`
- `DEFAULT_PROFILE_ID` est défini dans `identity/defaults.py`
- Tous les endpoints CRUD doivent respecter ce scoping (read + write + delete)

**Règle d'or** : un endpoint ne peut jamais lire/modifier/supprimer une ressource d'un autre profil.

---

## Conventions de code

### Domain objects
- `frozen=True, slots=True` obligatoire
- Validation dans `__post_init__`
- Pas de logique métier (juste structure + invariants)
- Pas de `profile_id` dans les entités domain → c'est une préoccupation de persistance

### Repositories
- Interface (`Protocol`) dans `account_repository.py`, implémentation SQL dans `sql_account_repository.py`
- Toutes les interfaces sont des `Protocol` (pas ABC)
- Toujours accepter `profile_id: str | None = None` sur les méthodes publiques, y compris `update()`
- Utiliser `resolve_profile_id()` en interne
- `_to_row(obj, profile_id: str)` : `profile_id` passé explicitement, jamais hardcodé

### Routes API
- Toujours exposer `profile_id: str | None = Query(default=None)` sur les endpoints qui touchent des ressources
- Utiliser `Decimal` (jamais `float`) pour les montants
- Montants sérialisés en `str` dans les réponses JSON (évite les erreurs de précision)

### Schémas Pydantic
- `profile_id` dans les réponses = oui (retourner l'appartenance explicitement)
- `profile_id` dans le domain object = non (c'est une donnée de persistance, pas métier)
  → Le `profile_id` est ajouté dans le mapper `_account_to_response()`, lu depuis la DB

---

## État actuel du projet (mars 2026)

### Ce qui est stable
- Domain objects (Account, Transaction, Trade, Portfolio, etc.)
- Engine de calcul (balance, timeseries, net worth)
- Repositories SQL avec Alembic
- Système identity/profils (Workspace → Profile)
- Tests d'intégration (**114 tests**, base PostgreSQL dédiée)
- **Profile scoping complet sur toute l'API** (accounts, transactions, net worth, portfolios, trades, imports, budgets)
- `on_event` migré vers `lifespan` FastAPI

### Prochaines étapes identifiées
- Frontend (à définir)
- Nouvelles fonctionnalités métier (budget prévisionnel, objectifs, etc.)

### Décisions de design arrêtées
- `profile_id` est retourné dans toutes les réponses API de type AccountResponse (explicite)
- `profile_id` n'est PAS dans les domain objects (séparation domaine / persistance)
- Le `profile_id` dans les réponses est passé explicitement au mapper `_account_to_response(account, *, profile_id: str)`
- `resolve_profile_id()` est appelé au niveau de la route (pas dans le repo) — pattern uniforme sur toute l'API
- `_to_row(obj, profile_id: str)` reçoit `profile_id` en paramètre explicite — pas de `DEFAULT_PROFILE_ID` hardcodé dans les mappers
- `SqlTransactionRepository` est indépendant de `AccountRepository` — pas de dépendance injectée
- Toutes les interfaces repo utilisent `Protocol` (plus de ABC)
- `update()` est présent dans toutes les interfaces Protocol (AccountRepository, PortfolioRepository)

---

## Ce que Claude NE doit PAS faire

- Générer de gros fichiers sans avoir d'abord proposé le design
- Modifier un fichier sans l'avoir lu
- Introduire de nouvelles abstractions sans justification
- Bypasser les hooks git ou les validations
- Pousser du code sur le remote sans confirmation explicite
- Ajouter des commentaires, docstrings ou type hints sur du code non modifié
- Créer des fichiers README ou markdown non demandés

---

## Fichiers clés à connaître

| Fichier | Rôle |
|---|---|
| `backend/app/api/main.py` | Point d'entrée FastAPI, enregistrement des routers |
| `backend/app/api/deps.py` | Injection de dépendances (repos via `lru_cache`) |
| `backend/app/identity/defaults.py` | IDs par défaut (DEFAULT_PROFILE_ID, etc.) |
| `backend/app/identity/profile_scope.py` | `resolve_profile_id()` |
| `backend/app/db.py` | Config SQLAlchemy (engine, session) |
| `backend/app/db_base.py` | `Base` déclarative SQLAlchemy |
| `backend/tests/conftest.py` | Fixtures pytest (drop/create tables + seed identité) |
| `backend/migrations/` | Migrations Alembic |
