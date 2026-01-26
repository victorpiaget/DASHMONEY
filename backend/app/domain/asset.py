# dataclasses : permet de créer des classes "données" très facilement
# frozen=True => objet IMMUTABLE (on ne peut pas modifier ses champs après création)
from dataclasses import dataclass

# Enum : permet de définir un ensemble fini de valeurs autorisées
from enum import Enum

# UUID : type d'identifiant unique
# uuid4() : fonction qui génère un UUID aléatoire (très pratique pour ID stable)
from uuid import UUID, uuid4

# On réutilise Money (déjà créé) : valeur monétaire sûre (>=0 et devise valide)
from app.domain.money import Money


# 1) Catégorie d'actif : on limite volontairement aux 3 catégories V1
# On hérite de "str" pour que ça se sérialise facilement (ex: JSON plus tard)
class AssetCategory(str, Enum):
    # FINANCIER : comptes, livrets, bourse, crypto...
    FINANCIAL = "FINANCIAL"

    # IMMOBILIER : résidence principale, locatif, terrain...
    REAL_ESTATE = "REAL_ESTATE"

    # BIEN PHYSIQUE : voiture, moto, bateau, objets de valeur...
    PHYSICAL = "PHYSICAL"


# 2) Asset : représentation générique d'un actif
# frozen=True => empêche de faire a.name = "..." après création (sécurité)
@dataclass(frozen=True)
class Asset:
    # id : identifiant unique (permet de différencier deux actifs semblables)
    id: UUID

    # name : nom lisible humain ("Livret A", "Appartement Nice", etc.)
    name: str

    # category : une des 3 valeurs AssetCategory (pas une string libre)
    category: AssetCategory

    # value : la valeur monétaire (Money) => pas un float brut
    value: Money

    # Factory method : méthode de classe qui crée un Asset avec un UUID auto
    # Pourquoi ? pour reveal:
    # - tu n'as pas à gérer uuid4() dans tout ton code
    # - création uniforme dans tout le projet
    @classmethod
    def create(cls, name: str, category: AssetCategory, value: Money) -> "Asset":
        return cls(
            id=uuid4(),       # génère un ID unique automatiquement
            name=name,
            category=category,
            value=value,
        )

    # __post_init__ est exécutée automatiquement après la création de la dataclass
    # C'est l'endroit parfait pour vérifier les règles métier ("invariants")
    def __post_init__(self) -> None:
        # 1) Le nom ne doit pas être vide ou juste des espaces
        if not self.name or not self.name.strip():
            raise ValueError("Asset name cannot be empty")

        # 2) La catégorie doit être un AssetCategory (sinon risque de strings invalides)
        if not isinstance(self.category, AssetCategory):
            raise ValueError("Invalid asset category")

        # 3) La valeur doit être un Money (sinon risque de float, ou structure non valide)
        if not isinstance(self.value, Money):
            raise ValueError("Invalid money value")
