from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator


class UtcDateTime(TypeDecorator):
    """
    DateTime portable Postgres ↔ SQLite avec invariant : tzinfo=UTC.

    Postgres stocke nativement la timezone (DateTime(timezone=True)).
    SQLite stocke les datetimes en TEXT sans timezone, et les renvoie naïfs.
    Ce TypeDecorator rattache UTC en lecture (process_result_value) et,
    par sécurité, normalise toute valeur écrite vers UTC (process_bind_param).

    Les couches domaine (Transaction, PricePoint, RefreshToken, etc.)
    valident `tzinfo is not None` ; ce TypeDecorator garantit l'invariant
    au niveau persistance plutôt que dans chaque mapper `_to_domain`.
    """

    impl = DateTime
    cache_ok = True

    def __init__(self, *args, **kwargs) -> None:
        # On force timezone=True côté Postgres ; SQLite l'ignore mais on garde
        # la cohérence sémantique.
        kwargs["timezone"] = True
        super().__init__(*args, **kwargs)

    def process_bind_param(self, value, dialect):  # noqa: ANN001
        if value is None:
            return None
        if not isinstance(value, dt.datetime):
            return value
        # Naïf → on suppose UTC (ne devrait pas arriver si le code amont
        # respecte l'invariant, mais on évite de propager une donnée corrompue).
        if value.tzinfo is None:
            return value.replace(tzinfo=dt.timezone.utc)
        # Aware non-UTC → on convertit pour garder une représentation cohérente.
        return value.astimezone(dt.timezone.utc)

    def process_result_value(self, value, dialect):  # noqa: ANN001
        if value is None:
            return None
        if not isinstance(value, dt.datetime):
            return value
        if value.tzinfo is None:
            # SQLite renvoie naïf → on rattache UTC.
            return value.replace(tzinfo=dt.timezone.utc)
        return value
