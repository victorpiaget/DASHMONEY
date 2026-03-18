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
$env:DASHMONEY_SECRET_KEY="<clé-secrète-32-octets-minimum>"
```

---

## Authentification JWT

Toute l'API est protégée par JWT (`Authorization: Bearer <token>`).

- `POST /auth/register` → crée un utilisateur
- `POST /auth/login` → retourne `{access_token (15min), refresh_token (30j)}`
- `POST /auth/refresh` → rotation : révoque l'ancien, émet un nouveau pair
- `POST /auth/logout` → révoque le refresh token

**Refresh tokens** : stockés hashés (SHA-256) en base dans la table `refresh_tokens`. Si un token révoqué est réutilisé → tous les tokens de l'user sont révoqués (détection de vol).

**`DASHMONEY_SECRET_KEY`** : variable d'environnement obligatoire pour signer les JWT. Lève `RuntimeError` au démarrage si absente.

---

## Multi-tenant : règle de scoping

Chaque ressource appartient à un `profile_id`.

- Chaque requête est authentifiée → `get_request_context` vérifie que l'user a accès au profil demandé
- Si `profile_id` est absent du query param → `resolve_profile_id()` retourne `DEFAULT_PROFILE_ID`
- La vérification se fait via la table `profile_access` (méthode `has_profile_access`)
- Tous les endpoints CRUD utilisent `ctx: RequestContext = Depends(get_request_context)`

**Règle d'or** : un endpoint ne peut jamais lire/modifier/supprimer une ressource d'un autre profil.
Un user ne peut accéder qu'aux profils pour lesquels il a une entrée dans `profile_access`.

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
- Toujours utiliser `ctx: RequestContext = Depends(get_request_context)` sur les endpoints qui touchent des ressources
- `profile_id` vient du query param (optionnel) — **jamais** du body
- Utiliser `Decimal` (jamais `float`) pour les montants
- Montants sérialisés en `str` dans les réponses JSON (évite les erreurs de précision)

### Schémas Pydantic
- `profile_id` dans les réponses = oui (retourner l'appartenance explicitement)
- `profile_id` dans le domain object = non (c'est une donnée de persistance, pas métier)
  → Le `profile_id` est ajouté dans le mapper `_account_to_response()`, lu depuis la DB

---

## État actuel du projet (mars 2026)

### Ce qui est stable
- Domain objects (Account, Transaction, Trade, Portfolio, User, RefreshToken, etc.)
- Engine de calcul (balance, timeseries, net worth)
- Repositories SQL avec Alembic
- Système identity/profils (Workspace → Profile) + authentification JWT complète
- Tests d'intégration (**153 tests**, base PostgreSQL dédiée)
- **Authentification JWT sur toute l'API** — access token 15min, refresh token 30j avec rotation
- **Profile scoping complet** vérifié par `profile_access` à chaque requête
- Multi-user réel avec isolation stricte entre workspaces
- **Permissions granulaires** — rôles workspace OWNER/MEMBER/READ_ONLY → permissions profil ADMIN/WRITE/READ ; `get_write_context` sur tous les endpoints de mutation ; `PATCH /workspaces/{id}/members/{user_id}`
- **Page d'inscription** — RegisterPage.tsx avec auto-login, lien depuis LoginPage
- **Frontend complet** (React + Vite + Tailwind) — toutes les pages principales implémentées
- **APScheduler** — snapshots automatiques quotidiens (20h UTC) + catch-up au démarrage si jours manqués
- **Imports CSV** — Boursorama et Binance (fichiers officiels), format perso Victor
- **Transferts d'actifs inter-portefeuilles** — `trade_type = TRANSFER` distingue les vrais trades des mouvements internes (pas de faux P&L)
- **Prix yfinance** — récupération automatique via `yfinance` + `GET /prices/latest-all` + historique
- **Courbe P&L globale** sur le dashboard (valeur totale vs net investi dans le temps)
- **Page d'analyse par portefeuille** — valorisation actuelle, P&L all-time, positions enrichies, benchmark auto-détecté
- **Bouton Virement sur AccountDetailPage** — modal coordonné compte source → compte destination via `POST /accounts/{id}/transfers`
- **Édition inline des actifs** — nom, type, ticker ET devise éditables dans InstrumentsPage
- **Système multi-devises complet** — 11 devises (EUR USD GBP CHF JPY CAD AUD SGD BTC ETH USDT) ; taux yfinance stockés en base (`exchange_rates`) ; refresh quotidien via scheduler ; `CurrencyContext` React avec `convert()` + `format()` ; sélecteur dans la sidebar ; préférence `localStorage` ; toutes les pages converties

### Prochaines étapes identifiées
- Nouvelles fonctionnalités métier (budget prévisionnel, objectifs, etc.)
- **TODO : Import CSV banque automatique** — parser les formats exportés par les applis bancaires (BNP, Crédit Agricole, Boursorama, etc.) sans configuration manuelle. L'endpoint `import-victor` gère le format perso de Victor (8 colonnes). Il faudra un système de détection automatique du format + mapping configurable.
- **TODO : Système de devises — saisie multi-devise** — quand l'user saisit un montant dans un formulaire (transaction, trade, compte), permettre de choisir la devise de saisie et convertir automatiquement vers la devise native avant envoi au backend.

### Décisions de design arrêtées
- `profile_id` est retourné dans toutes les réponses API de type AccountResponse (explicite)
- `profile_id` n'est PAS dans les domain objects (séparation domaine / persistance)
- Le `profile_id` dans les réponses est passé explicitement au mapper `_account_to_response(account, *, profile_id: str)`
- `RequestContext(user_id, profile_id)` est l'unique point d'entrée du contexte dans les routes
- `resolve_profile_id()` est appelé dans `get_request_context` (pas dans les repos)
- `_to_row(obj, profile_id: str)` reçoit `profile_id` en paramètre explicite — pas de `DEFAULT_PROFILE_ID` hardcodé dans les mappers
- `SqlTransactionRepository` est indépendant de `AccountRepository` — pas de dépendance injectée
- Toutes les interfaces repo utilisent `Protocol` (plus de ABC)
- `update()` est présent dans toutes les interfaces Protocol (AccountRepository, PortfolioRepository)
- Refresh tokens : stockés hashés (SHA-256), rotation systématique, révocation en cascade sur réutilisation
- `passlib` retiré — on utilise `bcrypt` directement pour le hachage des mots de passe
- `trade_type: TradeType` (TRADE | TRANSFER) sur le domaine Trade — les transferts inter-portefeuilles n'entrent pas dans le calcul du P&L ni du coût d'acquisition
- Les snapshots sont calculés automatiquement via `auto_snapshot_service` (positions × prix yfinance)
- Le scheduler rattrape les jours manqués au démarrage (thread daemon)

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
| `backend/app/api/deps.py` | Injection de dépendances + `get_current_user` + `get_request_context` |
| `backend/app/api/routes/auth.py` | `POST /auth/login|register|refresh|logout` |
| `backend/app/api/routes/snapshots.py` | `GET /snapshots/pnl-curve`, auto-snapshot, backfill |
| `backend/app/api/routes/prices.py` | `GET /prices/latest-all`, historique, mise à jour manuelle |
| `backend/app/api/routes/asset_transfers.py` | Transferts d'actifs inter-portefeuilles (trade_type=TRANSFER) |
| `backend/app/api/scheduler.py` | APScheduler — snapshots quotidiens + catch-up au démarrage |
| `backend/app/services/auto_snapshot_service.py` | Calcul snapshot = positions × prix yfinance |
| `backend/app/services/update_prices_service.py` | Récupération prix via yfinance |
| `backend/app/providers/yfinance_provider.py` | Wrapper yfinance |
| `backend/app/domain/trade.py` | Trade domain + enum TradeType (TRADE / TRANSFER) |
| `backend/app/identity/auth.py` | JWT + bcrypt + refresh token helpers |
| `backend/app/identity/request_context.py` | `RequestContext(user_id, profile_id)` |
| `backend/app/identity/defaults.py` | IDs par défaut (user1, user2, profils, workspaces) |
| `backend/app/identity/profile_scope.py` | `resolve_profile_id()` |
| `backend/app/repositories/sql_identity_models.py` | Modèles SQLAlchemy (User, Workspace, Profile, RefreshToken…) |
| `backend/app/db.py` | Config SQLAlchemy (engine, session) |
| `backend/app/db_base.py` | `Base` déclarative SQLAlchemy |
| `backend/tests/conftest.py` | Fixtures pytest (seed user1+user2, auth_headers, client) |
| `backend/migrations/` | Migrations Alembic |
| `frontend/src/pages/DashboardPage.tsx` | Dashboard — patrimoine net + courbe P&L globale + comptes |
| `frontend/src/pages/PortfolioAnalysisPage.tsx` | Analyse portefeuille — valorisation, P&L, positions, benchmark |
| `frontend/src/lib/portfoliosApi.ts` | Client API portfolios/trades/prix/snapshots |
| `frontend/src/hooks/usePortfolios.ts` | React Query hooks (trades, positions, snapshots, prix, P&L) |
