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

**DASHMONEY** — Conseiller patrimonial augmenté par l'IA, accessible à tous.

Objectif initial : remplacer un suivi Excel par un système structuré, déterministe, simulable.
Objectif actuel : devenir un **produit commercial** (SaaS) qui démocratise le conseil patrimonial grâce à l'IA.

Le produit se positionne sur 3 niveaux de valeur :
1. **Diagnostic** — Analyse factuelle de la situation patrimoniale (répartition, taux d'épargne, fonds d'urgence, concentration des risques). Pas de recommandation, un miroir intelligent.
2. **Éducation contextualisée** — Explique les concepts financiers en les reliant à la situation de l'utilisateur (ex. "votre fonds d'urgence couvre 1.8 mois, la recommandation courante est 3-6 mois"). Pas de "faites ça", mais "voici ce que votre situation signifie".
3. **Simulation** — L'utilisateur pose des hypothèses ("et si j'épargnais 500€/mois de plus ?") et l'IA montre les conséquences projetées. L'utilisateur décide, l'IA calcule.

Ce n'est PAS :
- un système de trading
- un moteur de recommandation d'achat/vente (activité régulée CIF/AMF)

**⚠️ Réglementation** : le wording de toute fonctionnalité IA doit rester dans le cadre analyse/éducation/simulation. Ne jamais générer de recommandation personnalisée d'investissement (achat/vente de produits financiers spécifiques) — c'est une activité régulée par l'AMF qui nécessite le statut CIF.

---

## Équipe

| Personne | Profil | Rôle sur DashMoney |
|---|---|---|
| Victor | Ingénieur méca, a construit tout le socle | Architecture backend + frontend + infrastructure |
| Pote IA | Dernière année école d'ingé IA | Prompt engineering, diagnostic IA, exploration RAG |
| Pote L3 | L3 informatique | Frontend, landing page, onboarding |

Side project à 3, pas une activité principale (pour l'instant).

---

## Vision produit & monétisation

**Cible** : le plus large possible — tout particulier qui veut mieux comprendre et piloter son patrimoine.

**Modèle économique envisagé** : freemium
- Gratuit : suivi de base (comptes, transactions, dashboard patrimoine)
- Premium : diagnostic IA, éducation contextualisée, simulations, alertes intelligentes

**Concurrence FR** : Finary (agrégation auto + suivi), Bankin'/Linxo (agrégation bancaire), Portfolio Performance (open source desktop).
**Angle différenciant visé** : l'IA comme couche d'intelligence personnalisée (diagnostic, éducation, simulation) — ce que les concurrents ne font pas ou peu.

**Agrégation bancaire** : pas prioritaire pour le MVP. L'import CSV couvre les besoins des premiers utilisateurs. Agrégation via Bridge, Powens ou Plaid à envisager quand il y aura des utilisateurs payants et du revenu pour couvrir le coût (plusieurs centaines €/mois minimum).

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
- Tests d'intégration (**200 tests**, base PostgreSQL dédiée)
- **Authentification JWT sur toute l'API** — access token 15min, refresh token 30j avec rotation
- **Profile scoping complet** vérifié par `profile_access` à chaque requête
- Multi-user réel avec isolation stricte entre workspaces
- **Permissions granulaires** — rôles workspace OWNER/MEMBER/READ_ONLY → permissions profil ADMIN/WRITE/READ ; `get_write_context` sur tous les endpoints de mutation ; `PATCH /workspaces/{id}/members/{user_id}`
- **Page d'inscription** — RegisterPage.tsx avec auto-login, lien depuis LoginPage
- **Frontend complet** (React + Vite + Tailwind) — toutes les pages principales implémentées
- **APScheduler** — snapshots automatiques quotidiens (20h UTC) + catch-up au démarrage si jours manqués
- **Imports CSV** — Boursorama et Binance (fichiers officiels) + import bancaire auto-détecté (`POST /accounts/{id}/import-bank`)
- **Transferts d'actifs inter-portefeuilles** — `trade_type = TRANSFER` distingue les vrais trades des mouvements internes (pas de faux P&L)
- **Prix yfinance** — récupération automatique via `yfinance` + `GET /prices/latest-all` + historique
- **Courbe patrimoine empilée** sur le dashboard — aires par type (Courant/Épargne/Investissement/Autre/Portefeuilles) + onglet P&L Portefeuilles
- **Page d'analyse par portefeuille** — valorisation actuelle, P&L all-time, positions enrichies, benchmark auto-détecté
- **Bouton Virement sur AccountDetailPage** — modal coordonné compte source → compte destination via `POST /accounts/{id}/transfers`
- **Édition inline des actifs** — nom, type, ticker ET devise éditables dans InstrumentsPage
- **Système multi-devises complet** — 11 devises (EUR USD GBP CHF JPY CAD AUD SGD BTC ETH USDT) ; taux yfinance stockés en base (`exchange_rates`) ; refresh quotidien via scheduler ; `CurrencyContext` React avec `convert()` + `format()` ; sélecteur dans la sidebar ; préférence `localStorage` ; toutes les pages converties
- **Saisie multi-devise** — `CurrencyAmountInput` déployé sur transactions, virements, création de compte (solde d'ouverture), et trades (prix + frais). Conversion via `convertBetween()` du `CurrencyContext` avant envoi au backend
- **Dark mode complet** — `ThemeContext` + classe `.dark` sur `<html>` ; toggle dans sidebar et pages de sélection ; graphiques SVG thématisés ; overrides CSS globaux pour bg-white/bg-gray-50
- **Animations et transitions** — `page-enter` keyframes sur changement de route ; micro-animations hover/bouton
- **Import CSV bancaire** — `POST /accounts/{id}/import-bank` auto-détecte Boursorama compte, BNP, Crédit Agricole, LCL, SG, CIC, générique ; page `/import` avec drag & drop ; `import_victor` supprimé
- **CashflowPanel sur AccountAnalysisPage** — revenus par catégorie (vert) + dépenses par catégorie (rouge) avec drill-down sous-catégories des deux côtés ; barre de cash flow net ; budget engine expose `income_by_category` et `income_by_subcategory`
- **Axe Y des courbes à 0** — `BalanceChart` et `PatrimoineChart` partent de 0 ; l'aire remonte jusqu'à la ligne zéro
- **Environnement démo** — `dev-demo.ps1` + `backend/scripts/seed_demo.py` ; base `dashmoney_demo` isolée ; Léa Dupont (51 mois, PEA/CTO/Crypto) + Thomas Bernard (14 mois, CTO concentré NVDA) ; Thomas MEMBER/READ dans le workspace de Léa ; comptes demo : `lea@dashmoney.app` / `thomas@dashmoney.app` — `Demo1234!` ; backend port 8001, frontend port 5174

### Stratégie IA

**Phase 1 — Approche LLM via API** (court terme)
- Appel API LLM (OpenAI / Anthropic / Mistral) depuis le backend
- Endpoint type `POST /ai/diagnostic` : construit un prompt avec les données patrimoniales de l'utilisateur, appelle l'API, retourne l'analyse
- Prompt système très cadré : rôle analyste patrimonial, jamais de recommandation d'achat/vente, analyse factuelle uniquement
- Garde-fous obligatoires : vérification que le LLM ne hallucine pas de chiffres, disclaimer systématique
- Coût à l'usage (quelques centimes par appel)

**Phase 2 — RAG (Retrieval-Augmented Generation)** (moyen terme)
- Base de connaissances financières fiables : guides AMF, principes d'allocation, fiscalité PEA/AV/CTO, etc.
- Base vectorielle via **pgvector** (extension PostgreSQL — évite une infra séparée)
- Pipeline : embedding des documents → stockage vecteurs → retrieval des passages pertinents → injection dans le prompt LLM
- Réduit les hallucinations, ancre les réponses dans des sources vérifiables
- Sujet d'exploration pour le pote IA

**Phase 3 — Fine-tuning / modèle spécialisé** (long terme, pas prioritaire)
- Fine-tuning sur données financières françaises si le besoin se confirme
- Prématuré pour un side project — à garder en tête

### Roadmap produit

**Horizon 1 — Valider le marché (1-2 mois)**
- [ ] Landing page (promesse + screenshots démo + collecte emails)
- [ ] Distribution : Reddit r/vosfinances, forums finance, LinkedIn, X finance FR
- [ ] Consultation avocat fintech sur le cadre AMF/CIF (positionnement diagnostic/éducation/simulation)
- [ ] Appel commercial Bridge ou Powens (comprendre les conditions startup pour plus tard)

**Horizon 2 — MVP public (2-4 mois)**
- [ ] Onboarding simplifié : flow guidé en 3 étapes (inscription → import CSV → premier dashboard)
- [ ] Diagnostic patrimonial basique (engine pur, sans IA) : taux d'épargne, fonds d'urgence en mois, répartition, concentration
- [ ] Premier endpoint IA (appel API LLM) : analyse contextualisée du patrimoine
- [ ] Budget prévisionnel : enveloppes par catégorie, comparaison réel vs prévu
- [ ] Infrastructure monétisation : Stripe, plans free/premium, flag `is_premium`, limites par tier

**Horizon 3 — Croissance et différenciation (6-12 mois)**
- [ ] RAG avec pgvector + base de connaissances financières
- [ ] Objectifs d'épargne : définir un objectif, suivre la progression, alertes IA
- [ ] Projections patrimoine : simulation selon scénarios (rendement, épargne mensuelle, événements)
- [ ] Alertes intelligentes ("vos dépenses resto ont augmenté de 40% ce mois")
- [ ] Agrégation bancaire (Bridge / Powens / Plaid) quand les revenus le justifient

### Prochaines étapes techniques immédiates
- Budget prévisionnel (domain → engine → API → frontend)
- Onboarding flow simplifié (frontend React)
- Landing page (HTML/Tailwind, hébergement Vercel/Netlify)
- Premier endpoint IA diagnostic (backend, appel API LLM)

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

## Workflow : prompts pré-rédigés

Les tâches complexes sont décrites dans des **prompts pré-rédigés** dans le dossier `prompts/`.

Quand un fichier `prompts/*.md` est référencé :
1. **Lire le prompt en entier** avant de coder quoi que ce soit
2. **Suivre l'ordre d'implémentation** indiqué dans le prompt
3. **Lancer les tests** après chaque étape backend (`cd backend && poetry run pytest -q`)
4. **Ne pas improviser** de fonctionnalités non décrites dans le prompt
5. Si quelque chose est ambigu, demander plutôt que deviner

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
| `backend/app/api/routes/import_bank.py` | `POST /accounts/{id}/import-bank` — import bancaire auto-détecté |
| `backend/app/engine/budget.py` | `income/expense_totals_by_category/subcategory`, `monthly_totals_by_kind` |
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
