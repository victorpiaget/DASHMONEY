# DashMoney

Dashboard personnel de gestion patrimoniale.
Suivi de comptes bancaires, portefeuilles d'investissement, crypto, et évolution du patrimoine dans le temps.

---

## Prérequis

Installe ces outils avant de commencer :

| Outil | Version | Lien |
|---|---|---|
| Git | n'importe | https://git-scm.com/downloads |
| Python | 3.12+ | https://www.python.org/downloads |
| Poetry | 2.x | https://python-poetry.org/docs/#installation |
| Node.js | 18+ | https://nodejs.org |
| Docker Desktop | n'importe | https://www.docker.com/products/docker-desktop |

> **Windows** : assure-toi que Python et Node sont bien dans ton PATH (coche la case à l'installation).

---

## Installation

### 1. Cloner le repo

```bash
git clone https://github.com/victorpiaget/DASHMONEY.git
cd DASHMONEY
```

### 2. Installer les dépendances backend

```bash
cd backend
poetry install
cd ..
```

### 3. Installer les dépendances frontend

```bash
cd frontend
npm install
cd ..
```

### 4. Créer le conteneur PostgreSQL

```bash
docker run --name dashmoney-postgres \
  -e POSTGRES_USER=dashmoney \
  -e POSTGRES_PASSWORD=dashmoney \
  -e POSTGRES_DB=dashmoney \
  -p 5432:5432 \
  -d postgres:16
```

> Cette commande crée et démarre le conteneur. Les fois suivantes, `.\dev.ps1` ou `.\dev-demo.ps1` le redémarre automatiquement.

---

## Lancer le projet

### Option A — Mode démo (recommandé pour découvrir)

Lance tout en une commande depuis la racine du projet (PowerShell) :

```powershell
.\dev-demo.ps1
```

Cela :
- démarre PostgreSQL
- crée et peuple automatiquement une base de démo avec des données réalistes
- lance le backend sur `http://localhost:8001`
- lance le frontend sur `http://localhost:5174`

**Comptes de démonstration :**

| Utilisateur | Email | Mot de passe |
|---|---|---|
| Léa Dupont | lea@dashmoney.app | Demo1234! |
| Thomas Bernard | thomas@dashmoney.app | Demo1234! |

Ouvre `http://localhost:5174` dans ton navigateur et connecte-toi.

---

### Option B — Mode développement (base vierge)

```powershell
.\dev.ps1
```

- Backend : `http://localhost:8000`
- Frontend : `http://localhost:5173`

Crée ton compte via l'interface (`/register`).

---

## Structure du projet

```
backend/        → API Python (FastAPI + PostgreSQL)
frontend/       → Interface React (Vite + Tailwind)
infra/          → Config Docker / infra
dev.ps1         → Script de démarrage dev (Windows)
dev-demo.ps1    → Script de démarrage demo (Windows)
```

---

## Commandes utiles

### Backend (depuis `backend/`)

```bash
# Lancer les tests
poetry run pytest -q

# Appliquer les migrations manuellement
poetry run alembic upgrade head

# Lancer l'API seule
poetry run uvicorn app.api.main:app --reload
```

### Frontend (depuis `frontend/`)

```bash
npm run dev     # mode développement
npm run build   # build de production
```

---

## Problèmes fréquents

**"docker: command not found"**
→ Docker Desktop n'est pas lancé. Ouvre Docker Desktop et réessaie.

**"poetry: command not found"**
→ Ferme et réouvre ton terminal après l'installation de Poetry.

**Port 5432 déjà utilisé**
→ Tu as peut-être déjà PostgreSQL installé en local. Arrête-le ou change le port dans `dev.ps1`.

**Le frontend affiche une erreur réseau**
→ Vérifie que le backend tourne bien (`http://localhost:8000/docs` ou `8001/docs` en mode démo).
