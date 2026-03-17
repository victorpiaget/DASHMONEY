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

_DATE_FR_RE = re.compile(r"^\s*(\d{2})/(\d{2})/(\d{4})\s*$")


def _parse_date(value: str) -> dt.date:
    m = _DATE_FR_RE.match(value or "")
    if not m:
        raise ValueError(f"date invalide (attendu JJ/MM/AAAA) : '{value}'")
    return dt.date(int(m.group(3)), int(m.group(2)), int(m.group(1)))


def _parse_decimal(value: str, default: str = "0") -> Decimal:
    s = (value or "").strip().replace(",", ".").replace(" ", "")
    if not s:
        return Decimal(default)
    try:
        return Decimal(s)
    except InvalidOperation:
        raise ValueError(f"nombre invalide : '{value}'")


def _guess_kind(instrument_name: str) -> InstrumentKind:
    name = instrument_name.upper()
    if "ETF" in name or "UC." in name or "UCIT" in name or "ISHS" in name or "AMUNDI" in name:
        return InstrumentKind.ETF
    return InstrumentKind.STOCK


@router.post("/{portfolio_id}/import-boursorama")
async def import_boursorama(
    portfolio_id: UUID,
    file: UploadFile = File(...),
    ctx: RequestContext = Depends(get_write_context),
):
    # ── Vérifier que le portefeuille existe ───────────────────────────────────
    p_repo = get_portfolio_repo()
    try:
        portfolio = p_repo.get(portfolio_id, profile_id=ctx.profile_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="portfolio not found")

    filename = (file.filename or "").lower()
    if not (filename.endswith(".csv") or filename.endswith(".txt")):
        raise HTTPException(status_code=422, detail="Fichier invalide (attendu .csv)")

    # ── Lecture + décodage ────────────────────────────────────────────────────
    raw = await file.read()
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        raise HTTPException(status_code=422, detail="Impossible de décoder le fichier (UTF-8/cp1252/latin-1)")

    if not text.strip():
        raise HTTPException(status_code=422, detail="Fichier vide")

    # ── Parsing CSV ───────────────────────────────────────────────────────────
    reader = csv.DictReader(io.StringIO(text))

    # Colonnes attendues
    required = {"Date", "Type_Operation", "ISIN", "Quantite", "Prix_Unitaire", "Devise", "Numero_Ordre"}
    if reader.fieldnames is None:
        raise HTTPException(status_code=422, detail="Impossible de lire l'entête CSV")
    missing = required - set(reader.fieldnames)
    if missing:
        raise HTTPException(
            status_code=422,
            detail=f"Colonnes manquantes : {', '.join(sorted(missing))}. Ce fichier ne semble pas être un export Boursorama.",
        )

    # ── Pré-charger les instruments et trades existants ───────────────────────
    i_repo = get_instrument_repo()
    t_repo = get_trade_repo()
    acc_repo = get_account_repo()
    tx_repo = get_tx_repo()

    existing_instruments: dict[str, Instrument] = {i.symbol: i for i in i_repo.list()}
    existing_labels: set[str] = {
        t.label for t in t_repo.list(portfolio_id=portfolio_id, profile_id=ctx.profile_id)
        if t.label is not None
    }

    # ── Parcourir les lignes ──────────────────────────────────────────────────
    imported = 0
    skipped_dup = 0       # Numero_Ordre déjà présent dans les trades
    skipped_csv_dup = 0   # Même Numero_Ordre vu plusieurs fois dans le CSV
    created_instruments: list[str] = []
    errors: list[str] = []

    seen_orders: set[str] = set()

    rows = list(reader)
    for line_no, row in enumerate(rows, start=2):  # line 1 = header
        try:
            date_str     = (row.get("Date") or "").strip()
            type_op      = (row.get("Type_Operation") or "").strip()
            isin         = (row.get("ISIN") or "").strip().upper()
            instrument_name = (row.get("Instrument") or row.get("Nom_Complet") or isin).strip()
            qty_str      = (row.get("Quantite") or "").strip()
            price_str    = (row.get("Prix_Unitaire") or "").strip()
            fee1_str     = (row.get("Frais_Commission") or "").strip()
            fee2_str     = (row.get("Frais_TTF") or "").strip()
            montant_brut_str = (row.get("Montant_Brut") or "").strip()
            devise       = (row.get("Devise") or "EUR").strip().upper()
            numero_ordre = (row.get("Numero_Ordre") or "").strip()

            if not isin or not numero_ordre:
                raise ValueError("ISIN ou Numero_Ordre vide")

            # Déduplication intra-CSV (même ordre listé N fois)
            if numero_ordre in seen_orders:
                skipped_csv_dup += 1
                continue
            seen_orders.add(numero_ordre)

            # Déduplication avec trades existants
            if numero_ordre in existing_labels:
                skipped_dup += 1
                continue

            # Parsing des champs
            date  = _parse_date(date_str)
            qty   = _parse_decimal(qty_str)
            price = _parse_decimal(price_str)
            fee1  = _parse_decimal(fee1_str)
            fee2  = _parse_decimal(fee2_str)
            brut  = _parse_decimal(montant_brut_str) if montant_brut_str else qty * price

            # Boursorama bug : pour les ETF sans commission, Frais_TTF contient
            # parfois le Montant_Brut au lieu d'être vide → on l'ignore si
            # fee2 >= 50% du montant brut (clairement aberrant comme frais).
            if brut > 0 and fee2 >= brut * Decimal("0.5"):
                fee2 = Decimal("0")

            fees  = fee1 + fee2

            type_op_lower = type_op.lower()
            if "achat" in type_op_lower or "buy" in type_op_lower:
                side = TradeSide.BUY
            elif "vente" in type_op_lower or "sell" in type_op_lower or "cession" in type_op_lower:
                side = TradeSide.SELL
            else:
                raise ValueError(f"Type_Operation inconnu : '{type_op}'")

            # Vérifier la devise
            try:
                currency = Currency(devise)
            except Exception:
                raise ValueError(f"Devise inconnue : '{devise}'")

            if currency != portfolio.currency:
                raise ValueError(
                    f"Devise '{devise}' différente de la devise du portefeuille '{portfolio.currency.value}'"
                )

            # Créer ou mettre à jour l'instrument
            if isin not in existing_instruments:
                kind = _guess_kind(instrument_name)
                inst = Instrument(symbol=isin, kind=kind, currency=currency, name=instrument_name)
                try:
                    i_repo.add(inst)
                    existing_instruments[isin] = inst
                    created_instruments.append(isin)
                    logger.info("Import Boursorama : instrument créé %s (%s)", isin, kind.value)
                except ValueError:
                    existing_instruments[isin] = i_repo.get(isin)
            elif not existing_instruments[isin].name and instrument_name:
                # Mettre à jour le nom si l'instrument existait sans nom
                old = existing_instruments[isin]
                updated = Instrument(symbol=old.symbol, kind=old.kind, currency=old.currency, name=instrument_name)
                i_repo.update(isin, updated)
                existing_instruments[isin] = updated
                logger.info("Import Boursorama : nom mis à jour %s → %s", isin, instrument_name)

            inst = existing_instruments[isin]

            # Transaction miroir cash
            gross = qty * price
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
                label=f"{side.value} {isin} — {numero_ordre}",
            )
            tx_repo.add(tx, profile_id=ctx.profile_id)

            # Créer le trade
            trade = Trade.create(
                portfolio_id=portfolio.id, date=date, side=side,
                instrument_symbol=inst.symbol, quantity=qty, price=price, fees=fees,
                currency=currency, label=numero_ordre, linked_cash_tx_id=tx.id,
            )
            t_repo.add(trade, profile_id=ctx.profile_id)
            existing_labels.add(numero_ordre)
            imported += 1

        except Exception as e:
            msg = f"ligne {line_no} : {e}"
            errors.append(msg)
            logger.warning("Import Boursorama : %s", msg)

    return {
        "imported": imported,
        "skipped_duplicates": skipped_dup,
        "skipped_csv_duplicates": skipped_csv_dup,
        "created_instruments": created_instruments,
        "errors_count": len(errors),
        "errors_preview": errors[:20],
    }
