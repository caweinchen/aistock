from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import StrategyResultDB, User, get_db
from app.routers.auth import get_current_user
from app.routers.stocks import build_custom_backtest, get_stock_detail
from app.schemas import BacktestRequest, StrategyDetail

router = APIRouter(prefix="/api")

@router.post("/backtests", response_model=StrategyDetail)
def create_backtest(request: BacktestRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> StrategyDetail:
    detail = get_stock_detail(db, request.code)
    strategy_detail = build_custom_backtest(detail, request)

    # 娣囨繂鐡ㄩ崚鐗堟殶閹诡喖绨?
    strategy_db = StrategyResultDB(
        id=strategy_detail.strategy.id,
        stock_code=request.code,
        name=strategy_detail.strategy.name,
        period=strategy_detail.strategy.period,
        return_rate=strategy_detail.strategy.return_rate,
        max_drawdown=strategy_detail.strategy.max_drawdown,
        win_rate=strategy_detail.strategy.win_rate,
        risk=strategy_detail.strategy.risk,
        summary=strategy_detail.strategy.summary,
    )
    db.add(strategy_db)
    db.commit()

    return strategy_detail
