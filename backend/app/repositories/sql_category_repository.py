from __future__ import annotations

import uuid

from sqlalchemy import String, UniqueConstraint, ForeignKey, select
from sqlalchemy.orm import Mapped, mapped_column

from app.db import init_db, new_session
from app.db_base import Base
from app.domain.category import CategoryNature
from app.identity.profile_scope import resolve_profile_id
from app.repositories.sql_identity_models import ProfileRow  # noqa: F401

_DEFAULTS: list[tuple[str, list[str]]] = [
    ("Logement & charges fixes", ["Loyer", "Eau", "Électricité", "Internet", "Assurance habitation", "Travaux", "Ameublement", "Crédit imo"]),
    ("Vie quotidienne", ["Alimentation", "Produits ménagers & hygiène", "Santé & pharmacie", "Abonnements", "Electronique", "Soins personnels"]),
    ("Transport & mobilité", ["Carburant", "Transports en commun", "Assurance auto/moto", "Entretien & réparations", "Parking", "Péage", "Achat", "Amendes"]),
    ("Études & travail", ["Matériel pro", "Frais scolarité", "Outils pro", "Déplacements travail", "Repas"]),
    ("Vie sociale & loisirs", ["Restaurants", "Loisirs", "Voyages", "Sorties culturelles", "Sport", "Bar", "Plaisir", "Paris sportifs"]),
    ("Cadeaux & solidarité", ["Cadeaux", "Dons", "Avance -"]),
    ("Épargne & investissements", ["PEA", "CRYPTO", "SECURITE", "Épargne projet", "CARPIMKO", "CAF"]),
    ("Revenus", ["Salaire", "Bourses", "Revenus exceptionnels", "Remboursements reçus", "CARPIMKO", "CAF"]),
    ("Autre", ["Non trié", "Ajustement", "Frais bancaire", "Transfert interne", "Assurance CA"]),
]

_DEFAULT_NATURES: dict[str, CategoryNature] = {
    "Logement & charges fixes": CategoryNature.NEED,
    "Vie quotidienne": CategoryNature.NEED,
    "Transport & mobilité": CategoryNature.NEED,
    "Études & travail": CategoryNature.NEED,
    "Vie sociale & loisirs": CategoryNature.WANT,
    "Cadeaux & solidarité": CategoryNature.WANT,
    "Épargne & investissements": CategoryNature.SAVING,
    # Catégorie historique issue des imports de Victor.
    "INVEST": CategoryNature.SAVING,
}


class CategoryRow(Base):
    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("profile_id", "name", name="uq_categories_profile_name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    profile_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    nature: Mapped[str | None] = mapped_column(String(16), nullable=True)


class SubcategoryRow(Base):
    __tablename__ = "subcategories"
    __table_args__ = (
        UniqueConstraint("category_id", "name", name="uq_subcategories_category_name"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    category_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("categories.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)


class SqlCategoryRepository:

    def __init__(self) -> None:
        init_db()

    # ------------------------------------------------------------------ #
    # Read                                                                 #
    # ------------------------------------------------------------------ #

    def list(self, *, profile_id: str | None = None) -> list[dict]:
        """Return all categories with their subcategories for the profile.

        Auto-seeds defaults on first call if the profile has no categories yet.
        """
        pid = resolve_profile_id(profile_id)
        with new_session() as s:
            cats = s.execute(
                select(CategoryRow)
                .where(CategoryRow.profile_id == pid)
                .order_by(CategoryRow.name.asc())
            ).scalars().all()

            if not cats:
                cats = self._seed_defaults(s, pid)

            result = []
            for cat in cats:
                subs = s.execute(
                    select(SubcategoryRow)
                    .where(SubcategoryRow.category_id == cat.id)
                    .order_by(SubcategoryRow.name.asc())
                ).scalars().all()
                result.append({
                    "id": cat.id,
                    "name": cat.name,
                    "nature": cat.nature,
                    "subcategories": [{"id": sub.id, "name": sub.name} for sub in subs],
                })

            return result

    def list_natures(self, *, profile_id: str | None = None) -> dict[str, str | None]:
        """Mapping {category_name: nature} pour un profil. NULL conservé."""
        pid = resolve_profile_id(profile_id)
        with new_session() as s:
            cats = s.execute(
                select(CategoryRow.name, CategoryRow.nature)
                .where(CategoryRow.profile_id == pid)
            ).all()
            result: dict[str, str | None] = {
                name: nature.value for name, nature in _DEFAULT_NATURES.items()
            }
            result.update({row.name: row.nature for row in cats})
            return result

    # ------------------------------------------------------------------ #
    # Categories                                                           #
    # ------------------------------------------------------------------ #

    def add_category(self, name: str, *, profile_id: str | None = None) -> dict:
        pid = resolve_profile_id(profile_id)
        trimmed = name.strip()
        if not trimmed:
            raise ValueError("name cannot be empty")

        with new_session() as s:
            existing = s.execute(
                select(CategoryRow)
                .where(CategoryRow.profile_id == pid, CategoryRow.name == trimmed)
            ).scalar_one_or_none()
            if existing is not None:
                raise ValueError(f"Category '{trimmed}' already exists")

            row = CategoryRow(id=str(uuid.uuid4()), profile_id=pid, name=trimmed)
            s.add(row)
            s.commit()
            s.refresh(row)
            return {"id": row.id, "name": row.name, "nature": row.nature, "subcategories": []}

    def update_category(
        self,
        category_id: str,
        *,
        name: str | None = None,
        nature: CategoryNature | None = None,
        clear_nature: bool = False,
        profile_id: str | None = None,
    ) -> dict:
        """Met à jour le nom et/ou la nature d'une catégorie.

        - `name=None` ne touche pas au nom (omis).
        - `nature=None` + `clear_nature=False` ne touche pas à la nature.
        - `clear_nature=True` force la nature à NULL (catégorie "Non classée").
        """
        pid = resolve_profile_id(profile_id)
        with new_session() as s:
            row = s.get(CategoryRow, category_id)
            if row is None or row.profile_id != pid:
                raise KeyError(f"Category '{category_id}' not found")

            if name is not None:
                trimmed = name.strip()
                if not trimmed:
                    raise ValueError("name cannot be empty")
                if trimmed != row.name:
                    duplicate = s.execute(
                        select(CategoryRow)
                        .where(
                            CategoryRow.profile_id == pid,
                            CategoryRow.name == trimmed,
                            CategoryRow.id != row.id,
                        )
                    ).scalar_one_or_none()
                    if duplicate is not None:
                        raise ValueError(f"Category '{trimmed}' already exists")
                row.name = trimmed

            if clear_nature:
                row.nature = None
            elif nature is not None:
                row.nature = nature.value

            s.commit()
            s.refresh(row)

            subs = s.execute(
                select(SubcategoryRow)
                .where(SubcategoryRow.category_id == row.id)
                .order_by(SubcategoryRow.name.asc())
            ).scalars().all()

            return {
                "id": row.id,
                "name": row.name,
                "nature": row.nature,
                "subcategories": [{"id": sub.id, "name": sub.name} for sub in subs],
            }

    def delete_category(self, category_id: str, *, profile_id: str | None = None) -> bool:
        pid = resolve_profile_id(profile_id)
        with new_session() as s:
            row = s.get(CategoryRow, category_id)
            if row is None or row.profile_id != pid:
                return False
            s.delete(row)
            s.commit()
            return True

    # ------------------------------------------------------------------ #
    # Subcategories                                                        #
    # ------------------------------------------------------------------ #

    def add_subcategory(self, category_id: str, name: str, *, profile_id: str | None = None) -> dict:
        pid = resolve_profile_id(profile_id)
        trimmed = name.strip()
        if not trimmed:
            raise ValueError("name cannot be empty")

        with new_session() as s:
            cat = s.get(CategoryRow, category_id)
            if cat is None or cat.profile_id != pid:
                raise KeyError(f"Category '{category_id}' not found")

            existing = s.execute(
                select(SubcategoryRow)
                .where(SubcategoryRow.category_id == category_id, SubcategoryRow.name == trimmed)
            ).scalar_one_or_none()
            if existing is not None:
                raise ValueError(f"Subcategory '{trimmed}' already exists in this category")

            row = SubcategoryRow(id=str(uuid.uuid4()), category_id=category_id, name=trimmed)
            s.add(row)
            s.commit()
            s.refresh(row)
            return {"id": row.id, "name": row.name}

    def delete_subcategory(self, subcategory_id: str, *, profile_id: str | None = None) -> bool:
        pid = resolve_profile_id(profile_id)
        with new_session() as s:
            sub = s.get(SubcategoryRow, subcategory_id)
            if sub is None:
                return False
            # Vérifier l'ownership via la catégorie parente
            cat = s.get(CategoryRow, sub.category_id)
            if cat is None or cat.profile_id != pid:
                return False
            s.delete(sub)
            s.commit()
            return True

    # ------------------------------------------------------------------ #
    # Private                                                              #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _seed_defaults(s, profile_id: str) -> list[CategoryRow]:
        cats = []
        for cat_name, sub_names in _DEFAULTS:
            default_nature = _DEFAULT_NATURES.get(cat_name)
            cat = CategoryRow(
                id=str(uuid.uuid4()),
                profile_id=profile_id,
                name=cat_name,
                nature=default_nature.value if default_nature is not None else None,
            )
            s.add(cat)
            s.flush()
            for sub_name in sub_names:
                s.add(SubcategoryRow(id=str(uuid.uuid4()), category_id=cat.id, name=sub_name))
            cats.append(cat)
        s.commit()
        return cats
