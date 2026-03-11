from __future__ import annotations

import csv
import datetime as dt
import io
import logging
import re

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException

from app.api.deps import get_account_repo, get_tx_repo, get_request_context
from app.domain.signed_money import SignedMoney
from app.domain.transaction import Transaction, TransactionKind
from app.identity.request_context import RequestContext

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/accounts", tags=["import"])


_DATE_FR_RE = re.compile(r"^\s*(\d{2})/(\d{2})/(\d{4})\s*$")


def parse_date_fr(value: str) -> dt.date:
    m = _DATE_FR_RE.match(value or "")
    if not m:
        raise ValueError(f"invalid FR date (expected DD/MM/YYYY): '{value}'")
    dd, mm, yyyy = int(m.group(1)), int(m.group(2)), int(m.group(3))
    return dt.date(yyyy, mm, dd)


def normalize_amount_fr(value: str) -> str:
    if value is None:
        raise ValueError("amount missing")
    s = value.strip()
    s = s.replace("€", "").replace("\u00a0", " ").strip()
    s = s.replace(" ", "")
    s = s.replace(",", ".")
    if s in ("", ".", "-", "+"):
        raise ValueError(f"invalid amount: '{value}'")
    return s


def map_type_to_kind(type_excel: str, amount_str: str):
    t = (type_excel or "").strip().lower()
    if "dépense" in t or "depense" in t:
        return TransactionKind.EXPENSE
    if "revenu" in t:
        return TransactionKind.INCOME
    if "invest" in t:
        return TransactionKind.INVESTMENT
    if "ajust" in t:
        return TransactionKind.ADJUSTMENT
    if amount_str.startswith("-"):
        return TransactionKind.EXPENSE
    return TransactionKind.INCOME


def looks_like_header(row: list[str]) -> bool:
    joined = " ".join((c or "").lower() for c in row)
    keywords = ["date", "type", "cat", "montant", "amount"]
    return sum(k in joined for k in keywords) >= 2


def sniff_delimiter(text: str) -> str:
    candidates = ["\t", ";", ","]
    counts = {d: text.count(d) for d in candidates}
    return max(counts, key=counts.get)


@router.post("/{account_id}/import-victor")
async def import_victor(
    account_id: str,
    file: UploadFile = File(...),
    ctx: RequestContext = Depends(get_request_context),
):
    try:
        acc = get_account_repo().get_account(account_id, profile_id=ctx.profile_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Account not found")

    filename = (file.filename or "").lower()
    if not (filename.endswith(".csv") or filename.endswith(".txt") or filename.endswith(".tsv")):
        raise HTTPException(status_code=422, detail="Invalid file type (expected .csv/.txt/.tsv)")

    try:
        raw = await file.read()
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Cannot read upload: {type(e).__name__}: {e}")

    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
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
        if not row or all((c or "").strip() == "" for c in row):
            continue

        if line_no == 1 and looks_like_header(row):
            continue

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
            amount = SignedMoney.from_str(amount_norm, acc.currency)
            seq = tx_repo.next_sequence(acc.id, date, profile_id=ctx.profile_id)

            tx = Transaction.create(
                account_id=acc.id, date=date, sequence=seq, amount=amount,
                kind=kind, category=category, subcategory=subcategory, label=None,
            )

            tx_repo.add(tx, profile_id=ctx.profile_id)
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
