from __future__ import annotations

import csv
import datetime as dt
import io
import logging

from fastapi import APIRouter, UploadFile, File, HTTPException

from app.api.deps import get_account_repo, get_tx_repo
from app.domain.signed_money import SignedMoney
from app.domain.transaction import Transaction, TransactionKind

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/accounts", tags=["import"])


@router.post("/{account_id}/import-transactions-csv")
async def import_transactions_csv(account_id: str, file: UploadFile = File(...)):
    """
    Import CSV strict (en-têtes attendus).
    Écrit dans transactions.jsonl via le repo JSONL.
    """
    try:
        acc = get_account_repo().get_account(account_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Account not found")

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=422, detail="Invalid file type (expected .csv)")

    try:
        content = await file.read()
        text = content.decode("utf-8-sig")  # support BOM Excel
    except Exception:
        raise HTTPException(status_code=422, detail="Cannot read CSV file")

    reader = csv.DictReader(io.StringIO(text))
    expected = {"date", "kind", "amount", "category", "subcategory", "label"}
    if reader.fieldnames is None:
        raise HTTPException(status_code=422, detail="CSV has no header row")

    # on tolère l'absence de subcategory/label mais on veut au minimum ces 4-là
    required = {"date", "kind", "amount", "category"}
    if not required.issubset(set(reader.fieldnames)):
        raise HTTPException(status_code=422, detail=f"CSV missing required headers: {sorted(required)}")

    tx_repo = get_tx_repo()

    imported = 0
    errors: list[str] = []

    for idx, row in enumerate(reader, start=2):  # ligne 1 = header
        try:
            date = dt.date.fromisoformat((row.get("date") or "").strip())
            kind = TransactionKind((row.get("kind") or "").strip())
            amount = SignedMoney.from_str((row.get("amount") or "").strip(), acc.currency)
            category = (row.get("category") or "").strip()
            if not category:
                raise ValueError("category empty")

            subcategory = (row.get("subcategory") or "").strip() or None
            label = (row.get("label") or "").strip() or None

            seq = tx_repo.next_sequence(acc.id, date)

            tx = Transaction.create(
                account_id=acc.id,
                date=date,
                sequence=seq,
                amount=amount,
                kind=kind,
                category=category,
                subcategory=subcategory,
                label=label,
            )

            tx_repo.add(tx)
            imported += 1

        except Exception as e:
            # B : message générique pour client, mais on veut un retour utilisable ici (import)
            # On renvoie un résumé d'erreurs (non sensible)
            msg = f"line {idx}: {e}"
            errors.append(msg)
            logger.exception("CSV import error %s", msg)

    return {
        "imported": imported,
        "errors_count": len(errors),
        "errors_preview": errors[:20],  # limite pour pas spammer
    }
