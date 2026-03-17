from __future__ import annotations

import csv
import datetime as dt
import io
import logging

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException

from app.api.deps import get_account_repo, get_tx_repo, get_request_context, get_write_context
from app.domain.signed_money import SignedMoney
from app.domain.transaction import Transaction, TransactionKind
from app.identity.request_context import RequestContext

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/accounts", tags=["import"])


@router.post("/{account_id}/import-transactions-csv")
async def import_transactions_csv(
    account_id: str,
    file: UploadFile = File(...),
    ctx: RequestContext = Depends(get_write_context),
):
    try:
        acc = get_account_repo().get_account(account_id, profile_id=ctx.profile_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Account not found")

    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=422, detail="Invalid file type (expected .csv)")

    try:
        content = await file.read()
        text = content.decode("utf-8-sig")
    except Exception:
        raise HTTPException(status_code=422, detail="Cannot read CSV file")

    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        raise HTTPException(status_code=422, detail="CSV has no header row")

    required = {"date", "kind", "amount", "category"}
    if not required.issubset(set(reader.fieldnames)):
        raise HTTPException(status_code=422, detail=f"CSV missing required headers: {sorted(required)}")

    tx_repo = get_tx_repo()
    imported = 0
    errors: list[str] = []

    for idx, row in enumerate(reader, start=2):
        try:
            date = dt.date.fromisoformat((row.get("date") or "").strip())
            kind = TransactionKind((row.get("kind") or "").strip())
            amount = SignedMoney.from_str((row.get("amount") or "").strip(), acc.currency)
            category = (row.get("category") or "").strip()
            if not category:
                raise ValueError("category empty")

            subcategory = (row.get("subcategory") or "").strip() or None
            label = (row.get("label") or "").strip() or None

            seq = tx_repo.next_sequence(acc.id, date, profile_id=ctx.profile_id)

            tx = Transaction.create(
                account_id=acc.id, date=date, sequence=seq, amount=amount,
                kind=kind, category=category, subcategory=subcategory, label=label,
            )

            tx_repo.add(tx, profile_id=ctx.profile_id)
            imported += 1

        except Exception as e:
            msg = f"line {idx}: {e}"
            errors.append(msg)
            logger.exception("CSV import error %s", msg)

    return {
        "imported": imported,
        "errors_count": len(errors),
        "errors_preview": errors[:20],
    }
