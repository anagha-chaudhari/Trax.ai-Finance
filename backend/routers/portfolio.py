from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import yfinance as yf

from models.database import get_db_session, User, Portfolio
from models.schemas import PortfolioAddRequest, PortfolioResponse
from utils.security import get_current_user

router = APIRouter()


def get_current_price(ticker: str) -> float | None:
    try:
        info = yf.Ticker(ticker).info
        return info.get("currentPrice") or info.get("regularMarketPrice")
    except Exception:
        return None

@router.post("/", response_model=PortfolioResponse, status_code=201)
def add_holding(
    request: PortfolioAddRequest,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
):
    # Check if user already has this ticker update quantity instead of duplicate
    existing = (
        db_session.query(Portfolio)
        .filter(Portfolio.user_id == current_user.id, Portfolio.ticker == request.ticker.upper())
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{request.ticker.upper()} already in portfolio. Delete it first to re-add.",
        )

    holding = Portfolio(
        user_id=current_user.id,
        ticker=request.ticker.upper(),
        quantity=request.quantity,
        buy_price=request.buy_price,
    )

    db_session.add(holding)
    db_session.commit()
    db_session.refresh(holding)
    return holding

@router.get("/")
def get_portfolio(
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
):
    holdings = (
        db_session.query(Portfolio)
        .filter(Portfolio.user_id == current_user.id)
        .order_by(Portfolio.added_at.desc())
        .all()
    )

    if not holdings:
        return {"holdings": [], "summary": {"total_invested": 0, "current_value": 0, "total_pnl": 0}}

    enriched = []
    total_invested = 0.0
    current_value = 0.0

    for holding in holdings:
        current_price = get_current_price(holding.ticker)

        invested = holding.buy_price * holding.quantity
        total_invested += invested

        if current_price:
            value = current_price * holding.quantity
            pnl = value - invested
            pnl_pct = ((current_price - holding.buy_price) / holding.buy_price) * 100
            current_value += value
        else:
            value = pnl = pnl_pct = None

        enriched.append({
            "id": holding.id,
            "ticker": holding.ticker,
            "quantity": holding.quantity,
            "buy_price": holding.buy_price,
            "current_price": current_price,
            "current_value": round(value, 2) if value else None,
            "pnl": round(pnl, 2) if pnl is not None else None,
            "pnl_percent": round(pnl_pct, 2) if pnl_pct is not None else None,
            "added_at": holding.added_at.isoformat(),
        })

    total_pnl = current_value - total_invested

    return {
        "holdings": enriched,
        "summary": {
            "total_invested": round(total_invested, 2),
            "current_value": round(current_value, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_percent": round((total_pnl / total_invested) * 100, 2) if total_invested else 0,
        },
    }

@router.delete("/{holding_id}", status_code=204)
def delete_holding(
    holding_id: int,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session),
):
    holding = (
        db_session.query(Portfolio)
        .filter(Portfolio.id == holding_id, Portfolio.user_id == current_user.id)
        .first()
    )

    if not holding:
        raise HTTPException(status_code=404, detail="Holding not found")

    # user_id check above ensures users can only delete their OWN holdings
    db_session.delete(holding)
    db_session.commit()