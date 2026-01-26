# dataclasses : pour définir des objets "données" simplement
# frozen=True : rend l'objet immuable (sécurité métier)
from dataclasses import dataclass

# UUID : identifiant unique pour distinguer les dettes
# uuid4 : génération automatique d'un identifiant
from uuid import UUID, uuid4

# Money : valeur monétaire sûre (>= 0, devise valide)
from app.domain.money import Money


# Liability représente une dette / un passif
@dataclass(frozen=True)
class Liability:
    # id : identifiant unique de la dette
    id: UUID

    # name : nom lisible ("Crédit immobilier", "Prêt étudiant", etc.)
    name: str

    # balance : montant restant dû (Money >= 0)
    balance: Money

    # Factory method pour créer une Liability avec ID automatique
    @classmethod
    def create(cls, name: str, balance: Money) -> "Liability":
        return cls(
            id=uuid4(),   # génère un UUID unique
            name=name,
            balance=balance,
        )

    # Vérification des invariants métier
    def __post_init__(self) -> None:
        # 1) Le nom doit être non vide
        if not self.name or not self.name.strip():
            raise ValueError("Liability name cannot be empty")

        # 2) Le solde doit être un Money
        if not isinstance(self.balance, Money):
            raise ValueError("Liability balance must be a Money instance")
