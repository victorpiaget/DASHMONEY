export interface Category {
  name: string
  subcategories: string[]
}

const STORAGE_KEY = 'dashmoney_categories'

const DEFAULTS: Category[] = [
  {
    name: 'Logement & charges fixes',
    subcategories: ['Loyer', 'Eau', 'Électricité', 'Internet', 'Assurance habitation', 'Travaux', 'Ameublement', 'Crédit imo'],
  },
  {
    name: 'Vie quotidienne',
    subcategories: ['Alimentation', 'Produits ménagers & hygiène', 'Santé & pharmacie', 'Abonnements', 'Electronique', 'Soins personnels'],
  },
  {
    name: 'Transport & mobilité',
    subcategories: ['Carburant', 'Transports en commun', 'Assurance auto/moto', 'Entretien & réparations', 'Parking', 'Péage', 'Achat', 'Amendes'],
  },
  {
    name: 'Études & travail',
    subcategories: ['Matériel pro', 'Frais scolarité', 'Outils pro', 'Déplacements travail', 'Repas'],
  },
  {
    name: 'Vie sociale & loisirs',
    subcategories: ['Restaurants', 'Loisirs', 'Voyages', 'Sorties culturelles', 'Sport', 'Bar', 'Plaisir', 'Paris sportifs'],
  },
  {
    name: 'Cadeaux & solidarité',
    subcategories: ['Cadeaux', 'Dons', 'Avance -'],
  },
  {
    name: 'Épargne & investissements',
    subcategories: ['PEA', 'CRYPTO', 'SECURITE', 'Épargne projet', 'CARPIMKO', 'CAF'],
  },
  {
    name: 'Revenus',
    subcategories: ['Salaire', 'Bourses', 'Revenus exceptionnels', 'Remboursements reçus', 'CARPIMKO', 'CAF'],
  },
  {
    name: 'Autre',
    subcategories: ['Non trié', 'Ajustement', 'Frais bancaire', 'Transfert interne', 'Assurance CA'],
  },
]

export function loadCategories(): Category[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return DEFAULTS
    return JSON.parse(raw) as Category[]
  } catch {
    return DEFAULTS
  }
}

export function saveCategories(categories: Category[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(categories))
}
