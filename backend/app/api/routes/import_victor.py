from __future__ import annotations

import csv
import datetime as dt
import io
import logging
import re
from typing import Optional

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.api.deps import get_account_repo, get_tx_repo
from app.domain.signed_money import SignedMoney
from app.domain.transaction import Transaction, TransactionKind

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/accounts", tags=["import"])


# ---------- Parsing helpers (format Victor) ----------

_DATE_FR_RE = re.compile(r"^\s*(\d{2})/(\d{2})/(\d{4})\s*$")


def parse_date_fr(value: str) -> dt.date:
    m = _DATE_FR_RE.match(value or "")
    if not m:
        raise ValueError(f"invalid FR date (expected DD/MM/YYYY): '{value}'")
    dd, mm, yyyy = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return dt.date(yyyy, mm, dd)


def normalize_amount_fr(value: str) -> str:
    """
    Convertit "-75,16 €" -> "-75.16"
    Convertit "145,40 €" -> "145.40"
    Convertit "-0,99" -> "-0.99"
    """
    if value is None:
        raise ValueError("amount missing")

    s = value.strip()

    # enlever euro + espaces insécables/espaces
    s = s.replace("€", "").replace("\u00a0", " ").strip()

    # enlever espaces au milieu (ex: "1 234,56")
    s = s.replace(" ", "")

    # virgule -> point
    s = s.replace(",", ".")

    # sanity
    if s in ("", ".", "-", "+"):
        raise ValueError(f"invalid amount: '{value}'")

    return s


def map_type_to_kind(type_excel: str, amount_str: str):
    """
    Mapping Victor -> TransactionKind.
    On utilise surtout le libellé, mais on peut aussi fallback sur le signe.
    """
    t = (type_excel or "").strip().lower()

    if "dépense" in t or "depense" in t:
        return TransactionKind.EXPENSE
    if "revenu" in t:
        return TransactionKind.INCOME
    if "invest" in t:
        return TransactionKind.INVESTMENT
    if "ajust" in t:
        return TransactionKind.ADJUSTMENT

    # fallback : signe du montant
    if amount_str.startswith("-"):
        return TransactionKind.EXPENSE
    return TransactionKind.INCOME


def looks_like_header(row: list[str]) -> bool:
    """
    Détecte une éventuelle ligne header du genre:
    Date | Type | Catégorie | Sous-catégorie | Montant
    """
    joined = " ".join((c or "").lower() for c in row)
    keywords = ["date", "type", "cat", "montant", "amount"]
    return sum(k in joined for k in keywords) >= 2


def sniff_delimiter(text: str) -> str:
    """
    Détecte tab / ; / , (dans cet ordre de préférence).
    """
    candidates = ["\t", ";", ","]
    counts = {d: text.count(d) for d in candidates}
    # choisir le délimiteur le plus fréquent
    best = max(counts, key=counts.get)
    return best


# ---------- Route ----------

@router.post("/{account_id}/import-victor")
async def import_victor(account_id: str, file: UploadFile = File(...)):
    """
    Import Excel Victor -> transactions.jsonl
    Format attendu (5 colonnes):
      date_fr, type_excel, category, subcategory, amount_fr

    Stratégie "pratique":
    - on importe les lignes valides
    - on renvoie un résumé d'erreurs (preview)
    """
    try:
        acc = get_account_repo().get_account(account_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Account not found")

    # on accepte csv/txt (Excel export)
    filename = (file.filename or "").lower()
    if not (filename.endswith(".csv") or filename.endswith(".txt") or filename.endswith(".tsv")):
        # on peut quand même accepter, mais gardons strict
        raise HTTPException(status_code=422, detail="Invalid file type (expected .csv/.txt/.tsv)")

    try:
        raw = await file.read()
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Cannot read upload: {type(e).__name__}: {e}")

    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError as e:
        # fallback fréquent sur Windows/Excel FR
        try:
            text = raw.decode("cp1252")
        except UnicodeDecodeError:
            raise HTTPException(
                status_code=422,
                detail=f"Decode error (utf-8/cp1252). Export CSV UTF-8 depuis Excel. First bytes: {raw[:20]!r}"
            )


    if not text.strip():
        raise HTTPException(status_code=422, detail="Empty file")

    delim = sniff_delimiter(text)
    reader = csv.reader(io.StringIO(text), delimiter=delim)

    tx_repo = get_tx_repo()
    imported = 0
    errors: list[str] = []

    for line_no, row in enumerate(reader, start=1):
        # sauter lignes vides
        if not row or all((c or "").strip() == "" for c in row):
            continue

        # si header détecté en première ligne -> skip
        if line_no == 1 and looks_like_header(row):
            continue

        # nettoyer cellules
        cells = [c.strip() for c in row]

        try:
            if len(cells) < 5:
                raise ValueError(f"expected 5 columns, got {len(cells)}")

            date_fr = cells[0]
            type_excel = cells[1]
            category = cells[2].strip()
            subcategory = cells[3].strip() or None
            amount_fr = cells[4]

            if not category:
                raise ValueError("category empty")

            date = parse_date_fr(date_fr)
            amount_norm = normalize_amount_fr(amount_fr)
            kind = map_type_to_kind(type_excel, amount_norm)

            # devise implicite = devise du compte
            amount = SignedMoney.from_str(amount_norm, acc.currency)

            # sequence auto (par date)
            seq = tx_repo.next_sequence(acc.id, date)

            tx = Transaction.create(
                account_id=acc.id,
                date=date,
                sequence=seq,
                amount=amount,
                kind=kind,
                category=category,
                subcategory=subcategory,
                label=None,
            )

            tx_repo.add(tx)
            imported += 1

        except Exception as e:
            msg = f"line {line_no}: {e}"
            errors.append(msg)
            logger.exception("Victor import error: %s", msg)

    return {
        "imported": imported,
        "errors_count": len(errors),
        "errors_preview": errors[:30],
        "delimiter_used": "\\t" if delim == "\\t" else delim,
    }
