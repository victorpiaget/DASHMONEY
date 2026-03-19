from __future__ import annotations

import csv
import datetime as dt
import io
import logging
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Optional

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException

from app.api.deps import get_account_repo, get_tx_repo, get_write_context
from app.domain.signed_money import SignedMoney
from app.domain.transaction import Transaction, TransactionKind
from app.identity.request_context import RequestContext

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/accounts", tags=["import"])

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

@dataclass
class ParsedRow:
    date: dt.date
    label: str
    amount: Decimal          # signed, in account currency
    category: str
    subcategory: Optional[str] = None


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

_DATE_DMY = re.compile(r"^(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})$")
_DATE_YMD = re.compile(r"^(\d{4})[/\-\.](\d{1,2})[/\-\.](\d{1,2})$")


def _parse_date(value: str) -> dt.date:
    s = (value or "").strip()
    m = _DATE_DMY.match(s)
    if m:
        return dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    m = _DATE_YMD.match(s)
    if m:
        return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    raise ValueError(f"date non reconnue : '{value}'")


def _parse_amount(value: str) -> Decimal:
    s = (value or "").strip()
    s = s.replace("\u00a0", "").replace(" ", "").replace("\u202f", "")
    s = s.replace("€", "").replace("EUR", "").strip()
    s = s.replace(",", ".")
    if not s or s in ("-", "+", "."):
        raise ValueError(f"montant vide : '{value}'")
    try:
        return Decimal(s)
    except InvalidOperation:
        raise ValueError(f"montant invalide : '{value}'")


def _normalize_headers(raw: list[str]) -> list[str]:
    return [h.strip().strip('"').lower() for h in (raw or [])]


def _sniff_delimiter(text: str) -> str:
    for delim in (";", "\t", ","):
        if text.count(delim) > text.count(",") if delim != "," else True:
            pass
    counts = {d: text[:2000].count(d) for d in (";", "\t", ",")}
    return max(counts, key=counts.get)


def _decode(raw: bytes) -> str:
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    raise ValueError("Impossible de décoder le fichier (essayé utf-8, cp1252, latin-1)")


# ---------------------------------------------------------------------------
# Format detection + parsers
# ---------------------------------------------------------------------------

def _detect_format(headers: list[str]) -> str:
    """Retourne le nom du format détecté à partir des headers normalisés."""
    h = set(headers)

    # Boursorama compte courant
    if "dateop" in h or ("dateval" in h and any("label" in x for x in h)):
        return "boursorama_compte"

    # BNP Paribas — "libellé" + "montant (€)" ou "montant"
    if any("libellé" in x or "libelle" in x for x in h):
        if any("débit" in x or "debit" in x for x in h) and any("crédit" in x or "credit" in x for x in h):
            return "debit_credit"  # LCL / BNP / CA avec colonnes séparées
        return "bnp"

    # Crédit Agricole — "date d'opération" ou "date operation"
    if any("opération" in x or "operation" in x for x in h):
        if any("débit" in x or "debit" in x for x in h) and any("crédit" in x or "credit" in x for x in h):
            return "debit_credit"
        return "credit_agricole"

    # LCL / CIC — colonnes débit + crédit séparées
    if any("débit" in x or "debit" in x for x in h) and any("crédit" in x or "credit" in x for x in h):
        return "debit_credit"

    # Société Générale — "nature" + "sens"
    if "sens" in h and any("nature" in x for x in h):
        return "societe_generale"

    # CIC / Crédit Mutuel — "solde après opération"
    if any("solde" in x for x in h) and any("libellé" in x or "libelle" in x or "label" in x for x in h):
        return "cic"

    # Générique : au moins une colonne date + une colonne montant
    return "generic"


def _col(headers: list[str], *candidates: str) -> Optional[int]:
    """Trouve l'index de la première colonne dont le header contient un des candidats."""
    for candidate in candidates:
        for i, h in enumerate(headers):
            if candidate in h:
                return i
    return None


def _parse_boursorama_compte(reader: csv.DictReader, headers: list[str]) -> list[ParsedRow]:
    rows: list[ParsedRow] = []
    for raw in reader:
        norm = {k.strip().strip('"').lower(): (v or "").strip() for k, v in raw.items()}
        date_val = norm.get("dateop") or norm.get("dateval") or norm.get("date", "")
        label_val = norm.get("label") or norm.get("libellé") or norm.get("libelle") or ""
        amount_val = norm.get("amount") or norm.get("montant") or ""
        category_val = norm.get("category") or norm.get("catégorie") or norm.get("categorie") or "Import"
        if not date_val or not amount_val:
            continue
        rows.append(ParsedRow(
            date=_parse_date(date_val),
            label=label_val,
            amount=_parse_amount(amount_val),
            category=category_val or "Import",
        ))
    return rows


def _parse_bnp(reader: csv.DictReader, headers: list[str]) -> list[ParsedRow]:
    rows: list[ParsedRow] = []
    for raw in reader:
        norm = {k.strip().strip('"').lower(): (v or "").strip() for k, v in raw.items()}
        date_val = next((norm[k] for k in norm if "date" in k), "")
        label_val = next((norm[k] for k in norm if "libellé" in k or "libelle" in k or "label" in k), "")
        amount_val = next((norm[k] for k in norm if "montant" in k), "")
        if not date_val or not amount_val:
            continue
        rows.append(ParsedRow(
            date=_parse_date(date_val),
            label=label_val,
            amount=_parse_amount(amount_val),
            category="Import",
        ))
    return rows


def _parse_debit_credit(reader: csv.DictReader, headers: list[str]) -> list[ParsedRow]:
    """Formats avec colonnes Débit et Crédit séparées (LCL, CA, etc.)."""
    rows: list[ParsedRow] = []
    for raw in reader:
        norm = {k.strip().strip('"').lower(): (v or "").strip() for k, v in raw.items()}
        date_val = next((norm[k] for k in norm if "date" in k and "valeur" not in k), "")
        label_val = next((norm[k] for k in norm if any(x in k for x in ("libellé", "libelle", "label", "opération", "operation", "nature"))), "")
        debit_val = next((norm[k] for k in norm if "débit" in k or "debit" in k), "")
        credit_val = next((norm[k] for k in norm if "crédit" in k or "credit" in k), "")
        if not date_val:
            continue
        debit = _parse_amount(debit_val) if debit_val else Decimal("0")
        credit = _parse_amount(credit_val) if credit_val else Decimal("0")
        if debit == 0 and credit == 0:
            continue
        amount = credit - debit if credit > 0 else -abs(debit)
        rows.append(ParsedRow(
            date=_parse_date(date_val),
            label=label_val,
            amount=amount,
            category="Import",
        ))
    return rows


def _parse_societe_generale(reader: csv.DictReader, headers: list[str]) -> list[ParsedRow]:
    rows: list[ParsedRow] = []
    for raw in reader:
        norm = {k.strip().strip('"').lower(): (v or "").strip() for k, v in raw.items()}
        date_val = next((norm[k] for k in norm if "date" in k), "")
        nature_val = next((norm[k] for k in norm if "nature" in k), "")
        sens_val = norm.get("sens", "").upper()
        amount_val = next((norm[k] for k in norm if "montant" in k), "")
        if not date_val or not amount_val:
            continue
        amt = abs(_parse_amount(amount_val))
        if sens_val in ("D", "DÉBIT", "DEBIT"):
            amt = -amt
        rows.append(ParsedRow(
            date=_parse_date(date_val),
            label=nature_val,
            amount=amt,
            category="Import",
        ))
    return rows


def _parse_cic(reader: csv.DictReader, headers: list[str]) -> list[ParsedRow]:
    """CIC / Crédit Mutuel — montant signé + colonne solde."""
    return _parse_bnp(reader, headers)  # même structure de base


def _parse_generic(reader: csv.DictReader, headers: list[str]) -> list[ParsedRow]:
    """Fallback générique : détecte les colonnes par heuristique."""
    rows: list[ParsedRow] = []
    date_key = next((h for h in headers if "date" in h and "valeur" not in h), None)
    amount_key = next((h for h in headers if any(x in h for x in ("montant", "amount", "solde"))), None)
    label_key = next((h for h in headers if any(x in h for x in ("libellé", "libelle", "label", "opération", "operation"))), None)

    if not date_key or not amount_key:
        raise ValueError("Impossible de détecter les colonnes date/montant dans ce CSV")

    for raw in reader:
        norm = {k.strip().strip('"').lower(): (v or "").strip() for k, v in raw.items()}
        date_val = norm.get(date_key, "")
        amount_val = norm.get(amount_key, "")
        label_val = norm.get(label_key, "") if label_key else ""
        if not date_val or not amount_val:
            continue
        try:
            rows.append(ParsedRow(
                date=_parse_date(date_val),
                label=label_val,
                amount=_parse_amount(amount_val),
                category="Import",
            ))
        except ValueError:
            continue
    return rows


PARSERS = {
    "boursorama_compte": _parse_boursorama_compte,
    "bnp": _parse_bnp,
    "debit_credit": _parse_debit_credit,
    "credit_agricole": _parse_debit_credit,
    "societe_generale": _parse_societe_generale,
    "cic": _parse_cic,
    "generic": _parse_generic,
}

FORMAT_LABELS = {
    "boursorama_compte": "Boursorama (compte courant)",
    "bnp": "BNP Paribas",
    "debit_credit": "Format débit/crédit (LCL, Crédit Agricole…)",
    "credit_agricole": "Crédit Agricole",
    "societe_generale": "Société Générale",
    "cic": "CIC / Crédit Mutuel",
    "generic": "Format générique",
}


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post("/{account_id}/import-bank")
async def import_bank(
    account_id: str,
    file: UploadFile = File(...),
    ctx: RequestContext = Depends(get_write_context),
):
    """
    Import automatique d'un relevé bancaire CSV.
    Détecte le format (Boursorama, BNP, Crédit Agricole, LCL, SG, CIC, générique)
    et importe les transactions dans le compte spécifié.
    """
    try:
        acc = get_account_repo().get_account(account_id, profile_id=ctx.profile_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Account not found")

    filename = (file.filename or "").lower()
    if not (filename.endswith(".csv") or filename.endswith(".txt") or filename.endswith(".tsv")):
        raise HTTPException(status_code=422, detail="Type de fichier invalide (attendu .csv)")

    try:
        raw = await file.read()
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Lecture impossible : {e}")

    try:
        text = _decode(raw)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if not text.strip():
        raise HTTPException(status_code=422, detail="Fichier vide")

    delim = _sniff_delimiter(text)
    reader = csv.DictReader(io.StringIO(text), delimiter=delim)

    if not reader.fieldnames:
        raise HTTPException(status_code=422, detail="Le CSV n'a pas de ligne d'en-tête")

    headers = _normalize_headers(list(reader.fieldnames))
    fmt = _detect_format(headers)
    parser = PARSERS.get(fmt, _parse_generic)

    try:
        parsed_rows = parser(reader, headers)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    tx_repo = get_tx_repo()
    imported = 0
    skipped_zero = 0
    errors: list[str] = []

    for idx, pr in enumerate(parsed_rows, start=1):
        try:
            if pr.amount == 0:
                skipped_zero += 1
                continue

            kind = TransactionKind.INCOME if pr.amount > 0 else TransactionKind.EXPENSE
            amount = SignedMoney.from_str(str(pr.amount), acc.currency)

            seq = tx_repo.next_sequence(acc.id, pr.date, profile_id=ctx.profile_id)
            tx = Transaction.create(
                account_id=acc.id,
                date=pr.date,
                sequence=seq,
                amount=amount,
                kind=kind,
                category=pr.category or "Import",
                subcategory=pr.subcategory,
                label=pr.label or None,
            )
            tx_repo.add(tx, profile_id=ctx.profile_id)
            imported += 1

        except Exception as e:
            errors.append(f"ligne {idx}: {e}")
            logger.warning("import_bank error row %d: %s", idx, e)

    return {
        "format_detected": fmt,
        "format_label": FORMAT_LABELS.get(fmt, fmt),
        "imported": imported,
        "skipped_zero": skipped_zero,
        "errors_count": len(errors),
        "errors_preview": errors[:20],
    }
