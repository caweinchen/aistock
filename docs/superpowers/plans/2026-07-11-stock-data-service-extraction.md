# 股票行情数据服务拆分实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将实时行情、交易时段判断和历史行情刷新从 `routers/stocks.py` 拆到独立 service，同时保持 API 和兼容导出稳定。

**Architecture:** 新建 `stock_data_service.py` 承担行情数据业务逻辑，并使用显式 operations 依赖访问 EastMoney/TuShare。`routers/stocks.py` 保留原函数名，但函数体只委托 service，以继续支持现有 patch 路径。

**Tech Stack:** Python 3.14、FastAPI、SQLAlchemy、unittest/pytest。

## Global Constraints

- 只修改后端代码、后端测试和本计划文档；不修改 `frontend/**`。
- 不修改任何 API 路径、响应模型或鉴权规则。
- 保留 `app.routers.stocks` 下现有行情函数名和测试 patch 路径。
- 使用 TDD：先看到边界测试失败，再写最小实现。
- 每完成一个任务即更新本文档对应 TODO。

---

### Task 1: 拆分交易时间和刷新判断

**Files:**
- Create: `backend/app/stock_data_service.py`
- Create: `backend/tests/test_stock_data_service.py`
- Modify: `backend/app/routers/stocks.py`
- Modify: `docs/superpowers/plans/2026-07-11-stock-data-service-extraction.md`

**Interfaces:**
- Produces: `StockDataOperations`、`is_trading_time()`、`is_morning_break_time()`、`last_market_session_end_time()`、`history_needs_refresh(history, stock)`。
- Preserves: `stocks._is_trading_time()`、`stocks._is_morning_break_time()`、`stocks._last_market_session_end_time()`、`stocks._history_needs_refresh()`。

- [ ] **Step 1: 写 router 委托失败测试**

```python
from unittest.mock import patch
from backend.app.routers import stocks

def test_history_refresh_boundary_delegates_to_service():
    with patch.object(stocks, "service_history_needs_refresh", return_value=False) as delegated:
        assert stocks._history_needs_refresh([], object()) is False
    delegated.assert_called_once()
```

- [ ] **Step 2: 运行失败测试**

Run: `python -m pytest backend/tests/test_stock_data_service.py -q`

Expected: FAIL，因为 `service_history_needs_refresh` 尚不存在或 router 仍执行本地逻辑。

- [ ] **Step 3: 新建 service 并迁移时间判断**

实现四个确定签名：`is_trading_time() -> bool`、`is_morning_break_time() -> bool`、`last_market_session_end_time() -> datetime`、`history_needs_refresh(history: list[PricePointDB], stock: Stock, *, is_trading_time: Callable[[], bool], last_market_session_end_time: Callable[[], datetime]) -> bool`。逐行迁移现有规则：交易时间内 5 分钟过期；非交易时间比较最近交易时段结束时间；最新行情日期落后时刷新。

- [ ] **Step 4: 将 router 函数改为兼容委托**

```python
def _history_needs_refresh(history, stock):
    return service_history_needs_refresh(
        history,
        stock,
        is_trading_time=_is_trading_time,
        last_market_session_end_time=_last_market_session_end_time,
    )
```

其他时间函数以同样方式委托，确保现有对 `stocks._is_trading_time` 的 patch 仍会影响刷新判断。

- [ ] **Step 5: 运行定向测试**

Run: `python -m pytest backend/tests/test_stock_data_service.py backend/tests/test_backtest_engine.py -q`

Expected: PASS。

- [ ] **Step 6: 更新 TODO 并提交**

```powershell
git add backend/app/stock_data_service.py backend/app/routers/stocks.py backend/tests/test_stock_data_service.py docs/superpowers/plans/2026-07-11-stock-data-service-extraction.md
git commit -m "refactor: extract stock refresh decisions"
```

---

### Task 2: 拆分历史行情读取和增量刷新

**Files:**
- Modify: `backend/app/stock_data_service.py`
- Modify: `backend/app/routers/stocks.py`
- Modify: `backend/tests/test_stock_data_service.py`
- Modify: `docs/superpowers/plans/2026-07-11-stock-data-service-extraction.md`

**Interfaces:**
- Produces: `get_price_history(db, code)` 和 `ensure_price_history(db, stock, operations)`。
- `StockDataOperations` 字段: `get_tushare_service: Callable[[], Any]`。
- Preserves: `stocks.get_price_history(db, code)` 和 `stocks.ensure_price_history(db, stock)`。

- [ ] **Step 1: 写三个失败测试**

测试函数名固定为 `test_ensure_history_returns_cache_without_remote_call`、`test_ensure_history_upserts_incremental_rows` 和 `test_ensure_history_returns_original_cache_when_remote_fails`。第一个 patch `history_needs_refresh=False` 并断言 TuShare 未调用；第二个提供已有日期和两条远程数据，断言更新旧行并插入新行；第三个让远程抛异常，断言返回原缓存且执行 rollback。

- [ ] **Step 2: 运行测试并确认因未委托 service 而失败**

Run: `python -m pytest backend/tests/test_stock_data_service.py -q`

Expected: FAIL。

- [ ] **Step 3: 迁移历史行情实现**

```python
def get_price_history(db: Session, code: str) -> list[PricePointDB]:
    return db.query(PricePointDB).filter(PricePointDB.stock_code == code).order_by(PricePointDB.date).all()

def ensure_price_history(
    db: Session,
    stock: Stock,
    operations: StockDataOperations,
    *,
    history_needs_refresh: Callable[[list[PricePointDB], Stock], bool],
) -> list[PricePointDB]:
    """Return cached history or refresh it incrementally through operations."""
```

将原函数的 720 天回溯、增量起始日期、upsert、`data_status`、commit/rollback 和排序行为原样迁移。

- [ ] **Step 4: 将 router 兼容入口改为委托**

```python
def get_price_history(db, code):
    return service_get_price_history(db, code)

def ensure_price_history(db, stock):
    return service_ensure_price_history(
        db,
        stock,
        StockDataOperations(get_tushare_service=get_initialized_tushare_service),
        history_needs_refresh=_history_needs_refresh,
    )
```

- [ ] **Step 5: 运行定向测试**

Run: `python -m pytest backend/tests/test_stock_data_service.py backend/tests/test_backtest_engine.py backend/tests/test_tushare_integration.py -q`

Expected: PASS。

- [ ] **Step 6: 更新 TODO 并提交**

```powershell
git add backend/app/stock_data_service.py backend/app/routers/stocks.py backend/tests/test_stock_data_service.py docs/superpowers/plans/2026-07-11-stock-data-service-extraction.md
git commit -m "refactor: extract price history service"
```

---

### Task 3: 拆分实时行情更新并完成验证

**Files:**
- Modify: `backend/app/stock_data_service.py`
- Modify: `backend/app/routers/stocks.py`
- Modify: `backend/tests/test_stock_data_service.py`
- Modify: `docs/superpowers/plans/2026-07-11-stock-data-service-extraction.md`

**Interfaces:**
- Extends `StockDataOperations` with `get_realtime_quotes: Callable[[list[str]], list[dict]]`。
- Produces: `update_stock_realtime_quote(db, stock, operations) -> None`。
- Preserves: `stocks.update_stock_realtime_quote(db, stock) -> None`。

- [ ] **Step 1: 写成功和失败路径测试**

测试函数名固定为 `test_update_realtime_quote_persists_first_quote` 和 `test_update_realtime_quote_rolls_back_on_provider_error`。成功测试断言 price、change_percent、name、updated_at、commit 和 refresh；失败测试断言 rollback，并保持现有不向上抛出的行为。

- [ ] **Step 2: 运行失败测试**

Run: `python -m pytest backend/tests/test_stock_data_service.py -q`

Expected: FAIL，因为 router 仍包含实时更新实现。

- [ ] **Step 3: 迁移实时更新并保留 router 委托**

```python
def update_stock_realtime_quote(db: Session, stock: Stock, operations: StockDataOperations) -> None:
    try:
        quotes = operations.get_realtime_quotes([stock.code])
        if not quotes:
            return
        quote = quotes[0]
        stock.price = quote.get("price", stock.price or 0)
        stock.change_percent = quote.get("change_percent", stock.change_percent or 0)
        stock.name = quote.get("name", stock.name)
        stock.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(stock)
    except Exception:
        db.rollback()
```

router 传入 `get_eastmoney_service().get_realtime_quote` 作为 operation。

- [ ] **Step 4: 运行定向和非认证全量测试**

Run: `python -m pytest backend/tests --ignore=backend/tests/test_auth_encryption.py -q`

Expected: PASS。

- [ ] **Step 5: 启动临时 API 并运行全部后端测试**

Run: 使用隐藏后台进程运行 `backend/start.py`，就绪后执行 `python -m pytest backend/tests -q`，最后停止进程。

Expected: 所有测试 PASS。

- [ ] **Step 6: 更新计划验证记录与 TODO**

在文档末尾记录日期、命令、通过数量和已知警告，并将本计划所有复选框标记为完成。

- [ ] **Step 7: 最终提交**

```powershell
git add backend/app/stock_data_service.py backend/app/routers/stocks.py backend/tests/test_stock_data_service.py docs/superpowers/plans/2026-07-11-stock-data-service-extraction.md
git commit -m "refactor: extract realtime stock data service"
```
