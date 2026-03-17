from __future__ import annotations

import csv
import datetime as dt
import io
import logging
import re
from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from uuid import UUID

from app.api.deps import (
    get_portfolio_repo, get_instrument_repo, get_trade_repo,
    get_account_repo, get_tx_repo, get_request_context, get_write_context,
)
from app.domain.instrument import Instrument, InstrumentKind
from app.domain.money import Currency, Money
from app.domain.signed_money import SignedMoney
from app.domain.trade import Trade, TradeSide
from app.domain.transaction import Transaction, TransactionKind
from app.identity.request_context import RequestContext

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/portfolios", tags=["import"])

_AMOUNT_RE = re.compile(r"^([\d.]+)([A-Z]+)$")


def _parse_decimal(value: str, default: str = "0") -> Decimal:
    s = (value or "").strip().replace(",", ".").replace(" ", "")
    if not s:
        return Decimal(default)
    try:
        return Decimal(s)
    except InvalidOperation:
        raise ValueError(f"nombre invalide : '{value}'")


def _parse_amount_with_currency(value: str) -> tuple[Decimal, str]:
    """Parse '12.63919EUR' → (Decimal('12.63919'), 'EUR')"""
    m = _AMOUNT_RE.match((value or "").strip())
    if not m:
        raise ValueError(f"format montant invalide : '{value}'")
    return Decimal(m.group(1)), m.group(2).upper()


def _parse_qty_with_symbol(value: str) -> tuple[Decimal, str]:
    """Parse '0.023BNB' → (Decimal('0.023'), 'BNB')"""
    m = _AMOUNT_RE.match((value or "").strip())
    if not m:
        raise ValueError(f"format quantité invalide : '{value}'")
    return Decimal(m.group(1)), m.group(2).upper()


def _extract_base(pair: str, quote: str) -> str:
    """'BNBEUR', 'EUR' → 'BNB'"""
    p = pair.strip().upper()
    q = quote.strip().upper()
    if p.endswith(q):
        return p[: -len(q)]
    # Fallback : essayer les quotes courantes
    for fallback in ("USDT", "BUSD", "EUR", "USD", "BTC", "ETH", "BNB"):
        if p.endswith(fallback):
            return p[: -len(fallback)]
    return p


@router.post("/{portfolio_id}/import-binance")
async def import_binance(
    portfolio_id: UUID,
    file: UploadFile = File(...),
    ctx: RequestContext = Depends(get_write_context),
):
    # ── Vérifier que le portefeuille existe ──────────────────────────────────
    p_repo = get_portfolio_repo()
    try:
        portfolio = p_repo.get(portfolio_id, profile_id=ctx.profile_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="portfolio not found")

    filename = (file.filename or "").lower()
    if not (filename.endswith(".csv") or filename.endswith(".txt")):
        raise HTTPException(status_code=422, detail="Fichier invalide (attendu .csv)")

    # ── Lecture + décodage ───────────────────────────────────────────────────
    raw = await file.read()
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise HTTPException(status_code=422, detail="Impossible de décoder le fichier")

    if not text.strip():
        raise HTTPException(status_code=422, detail="Fichier vide")

    # ── Parsing CSV ──────────────────────────────────────────────────────────
    reader = csv.DictReader(io.StringIO(text))

    required = {"Date(UTC)", "OrderNo", "Pair", "Side", "Executed", "Average Price", "Trading total"}
    if reader.fieldnames is None:
        raise HTTPException(status_code=422, detail="Impossible de lire l'entête CSV")

    # Normaliser les noms de colonnes (strip BOM résiduel, espaces)
    clean_fields = {f.strip().lstrip("\ufeff") for f in reader.fieldnames}
    missing = required - clean_fields
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Colonnes manquantes : {', '.join(sorted(missing))}. Ce fichier ne semble pas être un export Binance.",
        )

    # ── Pré-charger instruments et trades existants ──────────────────────────
    i_repo = get_instrument_repo()
    t_repo = get_trade_repo()
    acc_repo = get_account_repo()
    tx_repo = get_tx_repo()

    existing_instruments: dict[str, Instrument] = {i.symbol: i for i in i_repo.list()}
    existing_labels: set[str] = {
        t.label for t in t_repo.list(portfolio_id=portfolio_id, profile_id=ctx.profile_id)
        if t.label is not None
    }

    # ── Parcourir les lignes ─────────────────────────────────────────────────
    imported = 0
    skipped_dup = 0
    skipped_csv_dup = 0
    skipped_not_filled = 0
    created_instruments: list[str] = []
    errors: list[str] = []
    seen_orders: set[str] = set()

    rows = list(reader)
    for line_no, raw_row in enumerate(rows, start=2):
        # Normaliser les clés (BOM + espaces)
        row = {k.strip().lstrip("\ufeff"): v for k, v in raw_row.items()}
        try:
            order_no  = (row.get("OrderNo") or "").strip()
            status    = (row.get("Status") or "").strip().upper()
            pair      = (row.get("Pair") or "").strip().upper()
            side_raw  = (row.get("Side") or "").strip().upper()
            date_raw  = (row.get("Date(UTC)") or "").strip()
            executed  = (row.get("Executed") or "").strip()
            avg_price = (row.get("Average Price") or "").strip()
            total_str = (row.get("Trading total") or "").strip()

            if not order_no:
                raise ValueError("OrderNo vide")

            # Seulement les ordres exécutés
            if status and status != "FILLED":
                skipped_not_filled += 1
                continue

            # Déduplication intra-CSV
            if order_no in seen_orders:
                skipped_csv_dup += 1
                continue
            seen_orders.add(order_no)

            # Déduplication avec trades existants
            if order_no in existing_labels:
                skipped_dup += 1
                continue

            # Date : "2026-03-09 21:02:35" → date seule
            date_part = date_raw.split(" ")[0] if " " in date_raw else date_raw
            try:
                date = dt.date.fromisoformat(date_part)
            except ValueError:
                raise ValueError(f"Date invalide : '{date_raw}'")

            # Side
            if side_raw == "BUY":
                side = TradeSide.BUY
            elif side_raw == "SELL":
                side = TradeSide.SELL
            else:
                raise ValueError(f"Side inconnu : '{side_raw}'")

            # Quantité + symbole de l'actif
            qty, base_symbol = _parse_qty_with_symbol(executed)

            # Prix
            price = _parse_decimal(avg_price)
            if price <= 0:
                raise ValueError(f"Prix invalide : '{avg_price}'")

            # Montant total + devise de cotation
            gross, quote_currency_str = _parse_amount_with_currency(total_str)

            # Vérifier la devise du portefeuille
            try:
                currency = Currency(quote_currency_str)
            except Exception:
                raise ValueError(f"Devise inconnue : '{quote_currency_str}'")

            if currency != portfolio.currency:
                raise ValueError(
                    f"Devise '{quote_currency_str}' ≠ devise du portefeuille '{portfolio.currency.value}'"
                )

            # Créer ou mettre à jour l'instrument (toujours CRYPTO pour Binance)
            if base_symbol not in existing_instruments:
                inst = Instrument(symbol=base_symbol, kind=InstrumentKind.CRYPTO, currency=currency, name=base_symbol)
                try:
                    i_repo.add(inst)
                    existing_instruments[base_symbol] = inst
                    created_instruments.append(base_symbol)
                    logger.info("Import Binance : instrument créé %s", base_symbol)
                except ValueError:
                    existing_instruments[base_symbol] = i_repo.get(base_symbol)

            inst = existing_instruments[base_symbol]

            # Transaction miroir cash (pas de frais dans l'export Binance)
            fees = Decimal("0")
            net_amount = -(gross + fees) if side == TradeSide.BUY else (gross - fees)
            cash_amount = SignedMoney(amount=net_amount, currency=currency)

            try:
                acc = acc_repo.get_account(portfolio.cash_account_id, profile_id=ctx.profile_id)
            except KeyError:
                raise ValueError("Compte passerelle introuvable pour ce portefeuille")

            seq = tx_repo.next_sequence(acc.id, date, profile_id=ctx.profile_id)
            tx_kind = TransactionKind.INCOME if net_amount > 0 else TransactionKind.EXPENSE
            tx = Transaction.create(
                account_id=acc.id, date=date, sequence=seq, amount=cash_amount,
                kind=tx_kind, category="INVEST", subcategory=None,
                label=f"{side.value} {base_symbol} — {order_no}",
            )
            tx_repo.add(tx, profile_id=ctx.profile_id)

            trade = Trade.create(
                portfolio_id=portfolio.id, date=date, side=side,
                instrument_symbol=inst.symbol, quantity=qty, price=price, fees=fees,
                currency=currency, label=order_no, linked_cash_tx_id=tx.id,
            )
            t_repo.add(trade, profile_id=ctx.profile_id)
            existing_labels.add(order_no)
            imported += 1

        except Exception as e:
            msg = f"ligne {line_no} : {e}"
            errors.append(msg)
            logger.warning("Import Binance : %s", msg)

    return {
        "imported": imported,
        "skipped_duplicates": skipped_dup,
        "skipped_csv_duplicates": skipped_csv_dup,
        "skipped_not_filled": skipped_not_filled,
        "created_instruments": created_instruments,
        "errors_count": len(errors),
        "errors_preview": errors[:20],
        "note": "Les frais Binance ne sont pas inclus dans cet export CSV — ils ont été mis à 0.",
    }
