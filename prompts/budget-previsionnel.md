# Prompt Claude Code — Budget Prévisionnel

## Contexte

Implémente la fonctionnalité **budget prévisionnel** dans DASHMONEY. L'utilisateur doit pouvoir définir des enveloppes de budget mensuelles (revenus et dépenses) par catégorie et sous-catégorie, puis comparer le réel au prévu pour un mois donné.

Lis le CLAUDE.md à la racine du projet avant de commencer. Respecte toutes les conventions décrites.

---

## Décisions de design (non négociables)

1. **Granularité** : catégorie ET sous-catégorie. L'utilisateur peut budgéter au niveau catégorie seul, ou descendre aux sous-catégories.
2. **Temporalité** : mensuel fixe. Un montant par enveloppe, identique chaque mois. Pas de budget variable par mois pour le MVP.
3. **Scope** : niveau profil (pas par compte). Le budget agrège les transactions de tous les comptes du profil.
4. **Revenus** : on budgète aussi les revenus, pas seulement les dépenses.
5. **Règle catégorie/sous-catégorie** : si des sous-catégories sont budgétées, le montant de la catégorie parente = somme des sous-catégories (lecture seule côté UI). Si aucune sous-catégorie n'est budgétée, le montant s'applique à la catégorie entière.

---

## Étape 1 — Domain object

Crée `backend/app/domain/budget_envelope.py` :

```python
@dataclass(frozen=True)
class BudgetEnvelope:
    id: UUID
    category: str              # nom de la catégorie (doit matcher une catégorie existante)
    subcategory: str | None    # None = budget au niveau catégorie entière
    kind: TransactionKind      # INCOME ou EXPENSE (pas TRANSFER)
    amount: Money              # montant mensuel prévu (toujours positif, non signé)
```

Conventions à respecter :
- `frozen=True` (pas besoin de `slots=True` si ça pose problème avec l'héritage)
- Factory `@staticmethod create(...)` avec validation :
  - `kind` ne peut être que `INCOME` ou `EXPENSE` (jamais `TRANSFER`)
  - `amount` doit être strictement positif
  - `category` ne doit pas être vide
  - `subcategory` si présent ne doit pas être vide
- Pas de `profile_id` dans le domain object (convention projet)
- Utilise `Money` (pas `SignedMoney`) car le montant prévu est toujours positif

---

## Étape 2 — Repository

### Interface Protocol

Crée `backend/app/repositories/budget_envelope_repository.py` :

```python
class BudgetEnvelopeRepository(Protocol):
    def list(self, *, profile_id: str | None = None) -> list[BudgetEnvelope]: ...
    def upsert(self, envelope: BudgetEnvelope, *, profile_id: str | None = None) -> BudgetEnvelope: ...
    def delete(self, envelope_id: str, *, profile_id: str | None = None) -> bool: ...
    def delete_by_category(self, category: str, subcategory: str | None = None, kind: TransactionKind | None = None, *, profile_id: str | None = None) -> int: ...
```

Notes :
- `upsert` : si une enveloppe existe déjà pour (profile_id, category, subcategory, kind), on met à jour le montant. Sinon on crée. C'est crucial pour l'édition inline côté frontend.
- `delete_by_category` : utile pour supprimer toutes les enveloppes d'une catégorie d'un coup.

### Implémentation SQL

Crée `backend/app/repositories/sql_budget_envelope_repository.py` :

Table `budget_envelopes` :
- `id` : String(36), PK
- `profile_id` : String(36), FK → profiles.id (ondelete CASCADE), index
- `category` : String(128), not null
- `subcategory` : String(128), nullable
- `kind` : String(16), not null (valeurs : "INCOME", "EXPENSE")
- `amount` : Numeric(precision=15, scale=2), not null
- `currency` : String(8), not null

Contrainte unique : `(profile_id, category, subcategory, kind)` — une seule enveloppe par combinaison. Attention : `subcategory` peut être NULL, et en PostgreSQL `NULL != NULL` dans les contraintes unique. Utilise un index unique partiel ou `COALESCE(subcategory, '')` dans la contrainte.

Pattern à suivre : regarde `sql_category_repository.py` pour le style (init_db, new_session, resolve_profile_id).

### Migration Alembic

Crée la migration pour la table `budget_envelopes`. Suis le format existant dans `backend/migrations/versions/`.

---

## Étape 3 — Engine

Ajoute les fonctions de comparaison dans `backend/app/engine/budget.py` (ou un nouveau fichier `budget_forecast.py` si tu préfères séparer) :

```python
@dataclass(frozen=True)
class BudgetComparison:
    category: str
    subcategory: str | None
    kind: TransactionKind       # INCOME ou EXPENSE
    planned: Money              # montant prévu
    actual: SignedMoney         # montant réel (signé)
    delta: SignedMoney          # actual - planned (positif = dépassement dépense / sur-revenu)
    percent: Decimal            # pourcentage consommé (actual / planned * 100), 0 si planned = 0

@dataclass(frozen=True)
class BudgetSynthesis:
    total_income_planned: Money
    total_income_actual: SignedMoney
    total_expense_planned: Money
    total_expense_actual: SignedMoney  # négatif (convention existante)
    net_planned: SignedMoney           # income_planned - expense_planned
    net_actual: SignedMoney            # income_actual + expense_actual (expense est négatif)

def budget_vs_actual(
    envelopes: list[BudgetEnvelope],
    transactions: list[Transaction],
    *,
    currency: Currency,
) -> list[BudgetComparison]:
    """Compare les enveloppes au réel. Filtre les transactions par kind (INCOME/EXPENSE, pas TRANSFER)."""
    ...

def budget_synthesis(
    comparisons: list[BudgetComparison],
    *,
    currency: Currency,
) -> BudgetSynthesis:
    """Agrège les comparaisons en totaux."""
    ...
```

Logique importante pour `budget_vs_actual` :
- Pour chaque enveloppe, trouver les transactions qui matchent (category + subcategory si définie + kind).
- Pour les catégories sans enveloppe mais avec des transactions → inclure avec `planned = 0` (dépense non budgétée).
- Pour les enveloppes sans transaction → inclure avec `actual = 0`.
- Le `delta` pour les dépenses : `abs(actual) - planned` (positif = dépassement). Pour les revenus : `actual - planned` (positif = sur-performance).
- Le `percent` : `abs(actual) / planned * 100`. Si planned = 0, mettre 100 si actual != 0, sinon 0.
- Tri : par kind (INCOME d'abord), puis par `abs(actual)` décroissant.

---

## Étape 4 — API

### Endpoint CRUD enveloppes

Crée `backend/app/api/routes/budget_envelopes.py` :

```
GET    /budget/envelopes                → list toutes les enveloppes du profil
PUT    /budget/envelopes                → upsert une enveloppe (body: category, subcategory?, kind, amount)
DELETE /budget/envelopes/{envelope_id}  → supprime une enveloppe
```

Le PUT (pas POST) est intentionnel : l'édition inline envoie toujours la même requête que la création. Si l'enveloppe existe → update du montant. Sinon → création. Le frontend n'a pas besoin de savoir si c'est une création ou une modification.

### Endpoint comparaison budget

```
GET /budget/comparison?month=2026-03  → comparaison réel vs prévu pour le mois
```

Ce endpoint doit :
1. Récupérer les enveloppes du profil
2. Récupérer TOUTES les transactions du profil (tous les comptes) pour le mois donné
3. Convertir si nécessaire dans la devise de référence du profil (ou EUR par défaut)
4. Appeler `budget_vs_actual()` et `budget_synthesis()`
5. Retourner le résultat

Pour récupérer les transactions de tous les comptes : itérer sur les comptes du profil et agréger les transactions. Le repo transaction a `list(account_id=..., profile_id=...)`.

### Schémas Pydantic

Crée `backend/app/api/schemas/budget_envelopes.py` :

```python
class BudgetEnvelopeRequest(BaseModel):
    category: str
    subcategory: str | None = None
    kind: str                    # "INCOME" ou "EXPENSE"
    amount: str                  # Decimal en string, ex: "500.00"

class BudgetEnvelopeResponse(BaseModel):
    id: str
    category: str
    subcategory: str | None
    kind: str
    amount: str
    currency: str
    profile_id: str

class BudgetComparisonResponse(BaseModel):
    category: str
    subcategory: str | None
    kind: str
    planned: str
    actual: str
    delta: str
    percent: str

class BudgetSynthesisResponse(BaseModel):
    total_income_planned: str
    total_income_actual: str
    total_expense_planned: str
    total_expense_actual: str
    net_planned: str
    net_actual: str

class BudgetComparisonFullResponse(BaseModel):
    month: str                              # "2026-03"
    currency: str
    synthesis: BudgetSynthesisResponse
    comparisons: list[BudgetComparisonResponse]
    profile_id: str
```

Convention : tous les montants en `str`.

### Registration

Ajoute le router dans `backend/app/api/main.py` :
```python
from app.api.routes.budget_envelopes import router as budget_envelopes_router
app.include_router(budget_envelopes_router)
```

Ajoute la factory dans `backend/app/api/deps.py` :
```python
@lru_cache
def get_budget_envelope_repo():
    return SqlBudgetEnvelopeRepository()
```

---

## Étape 5 — Tests

Crée `backend/tests/test_budget_envelopes.py` avec des tests d'intégration :

### Tests engine (unitaires)
- `budget_vs_actual` avec enveloppes et transactions matchées
- `budget_vs_actual` avec transactions sans enveloppe (non budgétées)
- `budget_vs_actual` avec enveloppe sans transaction (0% consommé)
- `budget_vs_actual` avec sous-catégories
- `budget_synthesis` avec cas nominal

### Tests API (intégration)
- `PUT /budget/envelopes` → crée une enveloppe, vérifie 200
- `PUT /budget/envelopes` même catégorie → upsert, vérifie que le montant est mis à jour
- `GET /budget/envelopes` → liste les enveloppes du profil
- `DELETE /budget/envelopes/{id}` → supprime
- `GET /budget/comparison?month=2026-03` → retourne la comparaison avec des transactions existantes
- Test d'isolation multi-tenant : user2 ne voit pas les enveloppes de user1

Utilise les fixtures existantes dans `conftest.py` (auth_headers, client, user1, user2).

---

## Étape 6 — Frontend

### API Client

Crée `frontend/src/lib/budgetApi.ts` :

```typescript
export interface BudgetEnvelope {
  id: string
  category: string
  subcategory: string | null
  kind: string
  amount: string
  currency: string
  profile_id: string
}

export interface BudgetComparison {
  category: string
  subcategory: string | null
  kind: string
  planned: string
  actual: string
  delta: string
  percent: string
}

export interface BudgetSynthesis {
  total_income_planned: string
  total_income_actual: string
  total_expense_planned: string
  total_expense_actual: string
  net_planned: string
  net_actual: string
}

export interface BudgetComparisonFull {
  month: string
  currency: string
  synthesis: BudgetSynthesis
  comparisons: BudgetComparison[]
  profile_id: string
}

export const budgetApi = {
  listEnvelopes: (): Promise<BudgetEnvelope[]> =>
    api.get<BudgetEnvelope[]>('/budget/envelopes').then(r => r.data),

  upsertEnvelope: (data: {
    category: string
    subcategory?: string | null
    kind: string
    amount: string
  }): Promise<BudgetEnvelope> =>
    api.put<BudgetEnvelope>('/budget/envelopes', data).then(r => r.data),

  deleteEnvelope: (id: string): Promise<void> =>
    api.delete(`/budget/envelopes/${id}`).then(() => undefined),

  comparison: (month: string): Promise<BudgetComparisonFull> =>
    api.get<BudgetComparisonFull>('/budget/comparison', { params: { month } }).then(r => r.data),
}
```

### Hooks React

Crée `frontend/src/hooks/useBudget.ts` :

```typescript
export function useBudgetEnvelopes() {
  return useQuery({ queryKey: ['budget-envelopes'], queryFn: budgetApi.listEnvelopes })
}

export function useBudgetComparison(month: string) {
  return useQuery({
    queryKey: ['budget-comparison', month],
    queryFn: () => budgetApi.comparison(month),
    enabled: !!month,
  })
}

export function useUpsertEnvelope() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: budgetApi.upsertEnvelope,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['budget-envelopes'] })
      qc.invalidateQueries({ queryKey: ['budget-comparison'] })
    },
  })
}

export function useDeleteEnvelope() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: budgetApi.deleteEnvelope,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['budget-envelopes'] })
      qc.invalidateQueries({ queryKey: ['budget-comparison'] })
    },
  })
}
```

### Page Budget

Crée `frontend/src/pages/BudgetPage.tsx` :

**Structure de la page :**

```
┌─────────────────────────────────────────────────────┐
│  Budget prévisionnel          < Mars 2026 >         │
├─────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │ Revenus  │  │ Dépenses │  │  Solde   │          │
│  │ 3200/3500│  │ 2800/3000│  │ +400/+500│          │
│  │  91%     │  │  93%     │  │          │          │
│  └──────────┘  └──────────┘  └──────────┘          │
├─────────────────────────────────────────────────────┤
│  Revenus                                            │
│  ┌─────────────────────────────────────────────┐    │
│  │ ▸ Revenus       3200 / 3500  ████████░░ 91% │    │
│  │   Salaire       3000 / 3000  ██████████ 100%│    │
│  │   Freelance      200 / 500   ████░░░░░░  40%│    │
│  └─────────────────────────────────────────────┘    │
├─────────────────────────────────────────────────────┤
│  Dépenses                                           │
│  ┌─────────────────────────────────────────────┐    │
│  │ ▸ Logement       900 / 900   ██████████ 100%│    │
│  │   Loyer          850 / 850   ██████████ 100%│    │
│  │   Électricité     50 / 50    ██████████ 100%│    │
│  │ ▸ Vie quotid.    680 / 600   ██████████ 113%│    │
│  │   Courses        420 / 400   ██████████ 105%│    │
│  │   Restaurant     260 / 200   ██████████ 130%│    │
│  │ ▾ Transport      210 / 250   ████████░░  84%│    │
│  │   (non budgété)  Santé       45 / -     -   │    │
│  └─────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
```

**Comportement :**

1. **Sélecteur de mois** : `< Mars 2026 >` avec flèches gauche/droite. Par défaut le mois en cours. Format envoyé à l'API : `"2026-03"`.

2. **Cartes synthèse** : 3 cartes en haut avec revenus (réel/prévu + %), dépenses (réel/prévu + %), solde net (réel/prévu). Couleurs : vert pour les revenus, rouge pour les dépenses, bleu/gris pour le solde.

3. **Tableau catégories** (un pour revenus, un pour dépenses) :
   - Chaque ligne catégorie est dépliable (chevron ▸/▾) pour voir les sous-catégories
   - Colonnes : nom, réel, prévu (éditable inline), barre de progression, pourcentage
   - Le montant "prévu" est cliquable → devient un input → on tape le montant → blur ou Entrée → appel `PUT /budget/envelopes`
   - Si la catégorie a des sous-catégories budgétées, son montant prévu est la somme (affiché en gris, non éditable)
   - Catégories sans enveloppe et sans transaction : ne pas afficher
   - Catégories sans enveloppe mais avec des transactions : afficher avec prévu = "—" et un bouton "+" pour ajouter une enveloppe

4. **Barres de progression** :
   - Dépenses : vert < 80%, orange 80-100%, rouge > 100%
   - Revenus : rouge < 80%, orange 80-100%, vert > 100% (inversé)

5. **Suppression** : icône poubelle au survol du montant prévu → appel `DELETE /budget/envelopes/{id}`

### Intégration navigation

- Ajoute `{ to: '/budget', label: 'Budget', icon: '⊞' }` dans `NAV_ITEMS` de `AppLayout.tsx`, entre "Catégories" et "Actifs"
- Ajoute `<Route path="/budget" element={<BudgetPage />} />` dans `App.tsx`

### Style

- Utilise les mêmes patterns Tailwind que les autres pages (regarde `AccountAnalysisPage.tsx` pour le style des cartes KPI et du layout)
- Supporte le dark mode (`dark:` classes)
- Supporte `useCurrency()` pour le formatage des montants et la conversion
- Animation `page-enter` sur le montage (classe CSS existante)

---

## Ordre d'implémentation

Implémente dans cet ordre strict :

1. Domain object `BudgetEnvelope`
2. Migration Alembic (table `budget_envelopes`)
3. Repository Protocol + implémentation SQL
4. Engine functions (`budget_vs_actual`, `budget_synthesis`)
5. Schémas Pydantic
6. Routes API (CRUD + comparison)
7. Dependency injection (`deps.py` + `main.py`)
8. Tests engine (unitaires)
9. Tests API (intégration)
10. **Exécute les tests (`poetry run pytest -q`) et corrige jusqu'à ce que tout passe**
11. Frontend : API client + hooks
12. Frontend : BudgetPage + composants
13. Frontend : navigation (sidebar + router)

**Ne passe pas à l'étape suivante si la précédente ne compile pas ou si les tests échouent.**

---

## Contraintes à respecter

- Lis le CLAUDE.md et respecte toutes les conventions
- Lis chaque fichier existant avant de le modifier
- Montants en `Decimal` backend, `string` dans les réponses API
- `profile_id` jamais dans le body des requêtes, toujours via query param + `RequestContext`
- `get_write_context` sur tous les endpoints de mutation (PUT, DELETE)
- `get_request_context` sur les endpoints de lecture (GET)
- Pas de `float` nulle part
- Pas de nouvelles abstractions non justifiées
- Pas de commentaires/docstrings sur du code non modifié
