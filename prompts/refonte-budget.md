# Refonte complète de la page Budget prévisionnel

## Contexte

La page Budget actuelle (`BudgetPage.tsx`) est fonctionnelle mais très basique : 3 KPI cards, 2 tableaux (revenus/dépenses) avec édition inline des enveloppes, et c'est tout. Pas de graphiques, pas d'historique, pas de récurrence, UX d'ajout de budget peu intuitive.

On veut une refonte **full-stack** : backend + frontend.

---

## Fichiers existants à connaître

Lis ces fichiers **avant** de commencer :

| Fichier | Rôle |
|---|---|
| `backend/app/domain/budget_envelope.py` | Domain object `BudgetEnvelope` (frozen dataclass) |
| `backend/app/engine/budget.py` | Calculs purs : `budget_vs_actual()`, `budget_synthesis()`, agrégations par catégorie |
| `backend/app/api/routes/budget_envelopes.py` | Routes CRUD enveloppes + `GET /budget/comparison` |
| `backend/app/api/schemas/budget_envelopes.py` | Schémas Pydantic (request/response) |
| `backend/app/repositories/sql_budget_envelope_repository.py` | Repo SQL + modèle `BudgetEnvelopeRow` |
| `backend/tests/test_budget_envelopes.py` | Tests unitaires engine + tests intégration API |
| `frontend/src/pages/BudgetPage.tsx` | Composant React (448 lignes, tout dans un seul fichier) |
| `frontend/src/lib/budgetApi.ts` | Client API budget (listEnvelopes, upsert, delete, comparison) |
| `frontend/src/hooks/useBudget.ts` | React Query hooks |

---

## PARTIE 1 — Backend

### 1.1 Nouveau endpoint : `GET /budget/history`

**But** : retourner la synthèse budget pour les N derniers mois (pour alimenter un graphique d'évolution).

```
GET /budget/history?months=6
```

**Réponse** :
```json
{
  "months": [
    {
      "month": "2025-10",
      "income_actual": "2800.00",
      "expense_actual": "-2100.00",
      "net_actual": "700.00",
      "income_planned": "3000.00",
      "expense_planned": "2500.00"
    },
    ...
  ],
  "currency": "EUR",
  "profile_id": "..."
}
```

**Implémentation** :
- Dans `budget_envelopes.py` (routes), ajouter l'endpoint
- Calculer `date_from` = premier jour du mois `N` mois en arrière, `date_to` = dernier jour du mois courant
- Pour chaque mois dans la plage : filtrer les transactions de ce mois, appeler `budget_vs_actual` + `budget_synthesis`
- Les enveloppes sont les mêmes pour tous les mois (pas de notion de "mois" sur les enveloppes actuellement — c'est le comportement voulu pour l'instant)
- Schéma Pydantic dans `budget_envelopes.py` (schemas)

### 1.2 Nouveau endpoint : `GET /budget/categories`

**But** : retourner les catégories et sous-catégories déjà utilisées dans les transactions (pour l'auto-complétion dans le formulaire d'ajout d'enveloppe).

```
GET /budget/categories
```

**Réponse** :
```json
{
  "income": [
    { "category": "Revenus", "subcategories": ["Salaire", "Prime"] }
  ],
  "expense": [
    { "category": "Vie quotidienne", "subcategories": ["Courses", "Restaurant"] },
    { "category": "Logement", "subcategories": ["Loyer", "Charges"] }
  ]
}
```

**Implémentation** :
- Requête SQL `SELECT DISTINCT category, subcategory, kind FROM transactions WHERE profile_id = :pid`
- Grouper par kind → category → subcategories
- Utiliser le `tx_repo` existant ou faire une query directe

### 1.3 Nouveau endpoint : `POST /budget/envelopes/copy-month`

**But** : copier les enveloppes d'un mois source. Comme les enveloppes actuelles n'ont pas de champ `month`, cet endpoint copie simplement les enveloppes existantes si le mois cible n'en a pas. En pratique : c'est un "réinitialiser" — mais on anticipe le futur où les enveloppes seront mensuelles.

**Pour l'instant, approche simplifiée** : l'endpoint n'est pas strictement nécessaire car les enveloppes sont globales. On le skip et on le fera quand on ajoutera le champ `month` aux enveloppes. **Ne pas implémenter cet endpoint pour l'instant.**

### 1.4 Tests

Ajouter dans `test_budget_envelopes.py` :
- Test `GET /budget/history` — nominal avec transactions sur 3 mois
- Test `GET /budget/history` — mois vide (pas de transactions)
- Test `GET /budget/categories` — nominal
- Test `GET /budget/categories` — profil sans transactions

---

## PARTIE 2 — Frontend

### 2.1 Architecture des composants

Découper `BudgetPage.tsx` (448 lignes en un seul fichier) en composants réutilisables :

```
frontend/src/pages/BudgetPage.tsx          → Composant principal (layout + state)
frontend/src/components/budget/
  BudgetKpiCards.tsx         → Les 3 KPI cards (revenus, dépenses, solde net)
  BudgetExpenseDonut.tsx     → Camembert répartition des dépenses
  BudgetBarChart.tsx         → Bar chart horizontal prévu vs réel par catégorie
  BudgetHistoryChart.tsx     → Sparkline / courbe d'évolution sur N mois
  BudgetCategoryTable.tsx    → Tableau catégories avec édition inline (refactoré)
  BudgetEmptyState.tsx       → State quand aucune enveloppe n'est configurée
  EditableAmount.tsx         → Composant d'édition inline (existant, à extraire)
  AddEnvelopeForm.tsx        → Formulaire d'ajout rapide avec auto-complétion
```

### 2.2 Nouveaux hooks et API

**`budgetApi.ts`** — ajouter :
```typescript
history: (months?: number): Promise<BudgetHistoryResponse> =>
  api.get('/budget/history', { params: { months: months ?? 6 } }).then(r => r.data),

categories: (): Promise<BudgetCategoriesResponse> =>
  api.get('/budget/categories').then(r => r.data),
```

**`useBudget.ts`** — ajouter :
```typescript
export function useBudgetHistory(months = 6) { ... }
export function useBudgetCategories() { ... }
```

### 2.3 Nouveau layout de la page

Voici le layout cible, de haut en bas :

```
┌─────────────────────────────────────────────────────┐
│  Header : "Budget prévisionnel" + sélecteur mois    │
│  (même qu'actuellement, mais avec bouton            │
│  "Mois courant" pour revenir vite au mois actuel)   │
├─────────────────────────────────────────────────────┤
│  KPI Cards (3 colonnes)                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│  │ Revenus  │ │ Dépenses │ │ Solde net│            │
│  │ 2 800 €  │ │ 2 100 €  │ │ +700 €   │            │
│  │ vs prévu │ │ vs prévu │ │ vs prévu │            │
│  │ +5% ↑    │ │ -12% ↓   │ │          │            │
│  └──────────┘ └──────────┘ └──────────┘            │
├─────────────────────────────────────────────────────┤
│  Zone graphiques (2 colonnes)                       │
│  ┌────────────────────┐ ┌────────────────────┐      │
│  │ Donut répartition  │ │ Évolution 6 mois   │      │
│  │ des dépenses       │ │ (barres empilées   │      │
│  │                    │ │  revenus/dépenses)  │      │
│  └────────────────────┘ └────────────────────┘      │
├─────────────────────────────────────────────────────┤
│  Bar chart horizontal : prévu vs réel               │
│  (toutes catégories de dépenses, une barre par      │
│   catégorie, gris = prévu, couleur = réel,          │
│   rouge si dépassement)                             │
├─────────────────────────────────────────────────────┤
│  Tableau Revenus (existant amélioré)                │
│  + formulaire inline d'ajout en bas                 │
├─────────────────────────────────────────────────────┤
│  Tableau Dépenses (existant amélioré)               │
│  + formulaire inline d'ajout en bas                 │
└─────────────────────────────────────────────────────┘
```

### 2.4 Détail des composants

#### `BudgetKpiCards.tsx`
- 3 cards : Revenus, Dépenses, Solde net
- Chaque card montre : montant réel, montant prévu (si > 0), pourcentage, et **delta vs mois précédent** (petit texte vert/rouge, ex: "+120€ vs fév")
- Pour le delta vs mois précédent : utiliser `useBudgetComparison(prevMonth)` en plus du mois courant (ou bien le calculer depuis `useBudgetHistory`)

#### `BudgetExpenseDonut.tsx`
- Utiliser **recharts** (`PieChart` / `Pie`) — déjà disponible dans le projet
- Données : catégories de dépenses avec `|actual|` comme valeur
- Couleurs : palette de 8-10 couleurs distinctes
- Légende à droite du donut
- Si aucune dépense : afficher un placeholder gris "Aucune dépense ce mois"

#### `BudgetBarChart.tsx`
- Bar chart horizontal avec **recharts** (`BarChart` layout="vertical")
- Une barre par catégorie de dépense
- Deux barres superposées : gris clair = prévu, couleur = réel
- Si réel > prévu : la partie excédentaire en rouge
- Tri par |actual| décroissant

#### `BudgetHistoryChart.tsx`
- Bar chart groupé (revenus vs dépenses) + ligne pour le solde net
- Axe X = mois (labels "Oct", "Nov", "Déc", etc.)
- Utiliser `useBudgetHistory(6)`
- Recharts `ComposedChart` avec `Bar` + `Line`

#### `BudgetCategoryTable.tsx`
Refactoring du `CategorySection` existant avec ces améliorations :
- Les sous-catégories sont affichées directement (pas besoin de cliquer pour déplier) — mais repliables si on veut
- **Colonne delta** : afficher le montant d'écart (ex: "-50€" ou "+120€") avec couleur
- Le bouton "+ budget" est remplacé par un **dash grisé avec le texte "Définir"** plus visible
- Alertes visuelles : badge rouge "Dépassé" si > 100%, badge orange "Attention" si > 80%

#### `AddEnvelopeForm.tsx`
- Formulaire inline en bas de chaque tableau (revenus / dépenses)
- Champs : catégorie (input avec auto-complétion via `useBudgetCategories`), sous-catégorie (optionnel, auto-complétion), montant
- Bouton "Ajouter"
- L'auto-complétion propose les catégories déjà utilisées dans les transactions

#### `BudgetEmptyState.tsx`
- Affiché si `comparisons.length === 0` ET aucune enveloppe
- Illustration simple (icône SVG), texte : "Configurez votre budget mensuel"
- Sous-texte : "Définissez des enveloppes pour suivre vos dépenses et revenus"
- Bouton CTA : "Commencer" qui ouvre/focus le `AddEnvelopeForm`

### 2.5 Styles et design

- Conserver le dark mode existant (classes `dark:`)
- Utiliser Tailwind pour tout le styling
- Animations : conserver `page-transition` existant
- Charts : utiliser les couleurs du thème (recharts supporte les variables CSS ou les couleurs hardcodées — utiliser des couleurs cohérentes avec le reste de l'app)
- Palette suggérée pour le donut : `['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6', '#f97316']`
- Responsive : les 2 graphiques côte à côte passent en stack sur mobile (`grid-cols-1 lg:grid-cols-2`)

---

## PARTIE 3 — Ordre d'implémentation

Suivre cet ordre **strictement** :

1. **Backend : endpoint `GET /budget/history`** — schema + route + engine helper si besoin + tests
2. **Backend : endpoint `GET /budget/categories`** — schema + route + tests
3. **Frontend : extraction des composants** — découper `BudgetPage.tsx` sans changer le comportement (refactor pur)
4. **Frontend : nouveaux hooks** — `useBudgetHistory`, `useBudgetCategories` + `budgetApi.ts`
5. **Frontend : `BudgetKpiCards`** — améliorer avec delta vs mois précédent
6. **Frontend : `BudgetExpenseDonut`** — nouveau composant recharts
7. **Frontend : `BudgetHistoryChart`** — nouveau composant recharts
8. **Frontend : `BudgetBarChart`** — nouveau composant recharts
9. **Frontend : `AddEnvelopeForm`** — formulaire avec auto-complétion
10. **Frontend : `BudgetEmptyState`** — empty state
11. **Frontend : assemblage final** — nouveau layout dans `BudgetPage.tsx`
12. **Tests** — vérifier que les tests backend passent (`poetry run pytest -q` depuis `backend/`)

**À chaque étape**, lancer les tests backend pour vérifier qu'il n'y a pas de régression :
```bash
cd backend && poetry run pytest -q
```

---

## Contraintes et rappels

- **Pas de `float`** pour les montants — `Decimal` côté backend, `string` dans les API
- **Recharts** est déjà installé côté frontend — ne pas ajouter d'autre lib de charts
- **Profile scoping** : tous les nouveaux endpoints doivent utiliser `ctx: RequestContext = Depends(get_request_context)`
- **Conventions** : suivre exactement les patterns existants (voir CLAUDE.md du projet)
- **Ne pas casser les tests existants** — les 200+ tests doivent continuer à passer
- **Dark mode** : tous les composants doivent supporter `dark:` classes
- **Montants sérialisés en `str`** dans les réponses JSON
- **Français** pour tout le texte UI visible
