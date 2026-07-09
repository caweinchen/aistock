# 普通用户 MVP 实施计划

> **给 agentic workers 的要求：** 实施本计划时必须使用 `superpowers:subagent-driven-development`（推荐）或 `superpowers:executing-plans`，按任务逐项执行。步骤使用 checkbox（`- [ ]`）语法，便于跟踪进度。

**目标：** 将当前股票分析 App 改造成更适合普通用户的 MVP：提供克制的参考状态、数据健康信息、自选股分组，以及更清晰的个股详情摘要。

**架构思路：** 保持现有 FastAPI 响应兼容，不删除旧的 `signal` 字段，而是在响应中新增普通用户字段。后端增加一个轻量决策层，把已有的因子、风险提示、历史行情和股票元数据转换成普通用户能理解的参考状态。前端优先读取新字段；如果读取的是旧缓存或旧接口响应，则回退到现有的 `signal`、`data_status` 和 `updated_at`。

**技术栈：** FastAPI、Pydantic、SQLAlchemy、pytest/unittest 后端测试、Expo 56、React Native 0.85、TypeScript、Vitest 前端测试。

## 全局约束

- 修改前端代码前，必须按 `AGENTS.md` 要求阅读 Expo 56 精确版本文档：`https://docs.expo.dev/versions/v56.0.0/`。
- 不输出直接交易指令，例如“立即买入”“强烈卖出”“必涨”“稳赚”“最佳买点”。
- 本 MVP 阶段保留 `signal: neutral | buy | sell`，用于兼容现有接口、缓存和页面。
- 新增面向普通用户的参考状态：`positive`、`watch`、`cautious`、`insufficient_data`。
- 所有个股详情结论都必须包含数据新鲜度或数据完整度语境。
- 本 MVP 不做会员、支付、订阅、专业版和管理后台商业化能力。

---

## 当前代码地图

- `backend/app/main.py`：Pydantic API 模型、个股详情组装、因子评分、风险提示、AI 摘要、股票列表和自选股 API。
- `backend/app/database.py`：SQLAlchemy 模型。`Stock` 已有 `score`、`signal`、`ai_summary`、`data_status`、`updated_at`、`quote_updated_at`、`history_updated_at`。
- `backend/tests/test_user_admin_and_watchlist.py`：已有认证、自选股隔离、个股详情、TuShare 缓存、分红、复权因子、持有人接口等测试。
- `frontend/src/types/index.ts`：前端共享 API 类型。当前 `Signal` 为 `neutral | buy | sell`。
- `frontend/src/services/api.ts`：缓存优先的服务调用。股票列表和个股详情以 JSON 形式写入本地缓存。
- `frontend/src/services/localDb.ts`：本地缓存工具，包含股票列表、个股详情、策略详情、分红、新闻、机构持仓等。
- `frontend/src/components/StockRow.tsx`：自选股行组件，展示股票名称、价格、评分和翻译后的信号。
- `frontend/src/pages/HomeScreen.tsx`：当前首页，展示自选股、选中股票摘要、因子、策略和风险提示。
- `frontend/src/pages/StockDetailScreen.tsx`：个股详情页，展示价格卡、评分/信号、因子、策略、分红、新闻、机构持仓和风险提示。
- `frontend/src/i18n/locales/zh.ts`、`zh-Hant.ts`、`en.ts`：多语言文案。

## 范围

本计划只实现第一阶段 MVP：

1. 后端为单只股票新增普通用户字段。
2. 后端新增自选股洞察接口，对用户自选股进行分组。
3. 前端新增类型和 API 调用支持。
4. 首页新增“今日自选股参考”分组展示。
5. 个股详情页新增普通用户摘要和数据健康展示。
6. 将“机构持仓”文案调整为“重要股东变动”。

本计划明确不实现：订阅、支付、持仓仓位管理、完整组合风险、管理端统计、报告导出、专业版功能。

---

### 任务 1：后端普通用户决策字段

**文件：**
- 修改：`backend/app/main.py`
- 测试：`backend/tests/test_user_admin_and_watchlist.py`

**接口：**
- 新增 `ReferenceStatus = Literal["positive", "watch", "cautious", "insufficient_data"]`。
- 新增 `DataCompleteness = Literal["complete", "mostly_complete", "incomplete", "insufficient"]`。
- `StockSummary` 新增可选字段：`reference_status`、`reference_label`、`primary_support`、`primary_risk`、`data_completeness`、`data_updated_at`。
- `StockDetail` 后续会新增：`ordinary_summary`、`support_factors`、`risk_factors`、`data_completeness`、`data_updated_at`、`disclaimer`。

- [x] **步骤 1：添加失败的后端测试**

在 `UserAdminAndWatchlistTest` 中新增：

```python
def test_stock_list_returns_ordinary_user_reference_fields(self):
    self.db.add(WatchlistItem(user_id=self.user_a.id, stock_code="600519", created_at=datetime.now(timezone.utc)))
    stock = self.db.query(Stock).filter(Stock.code == "600519").first()
    stock.score = 82
    stock.signal = "buy"
    stock.data_status = "normal"
    stock.updated_at = datetime(2026, 7, 8, 9, 30, tzinfo=timezone.utc)
    self.db.commit()

    alice_token = self._login("alice", "Alice@123!")
    response = self.client.get("/api/stocks", headers={"Authorization": f"Bearer {alice_token}"})

    self.assertEqual(response.status_code, 200, response.text)
    item = response.json()[0]
    self.assertEqual(item["reference_status"], "positive")
    self.assertEqual(item["reference_label"], "偏积极")
    self.assertIn("重点观察", item["primary_support"])
    self.assertEqual(item["data_completeness"], "mostly_complete")
    self.assertIsNotNone(item["data_updated_at"])
```

- [x] **步骤 2：运行测试并确认失败**

运行：

```powershell
python -m pytest backend/tests/test_user_admin_and_watchlist.py::UserAdminAndWatchlistTest::test_stock_list_returns_ordinary_user_reference_fields -q
```

预期：失败，因为响应中还没有 `reference_status`。

- [x] **步骤 3：添加后端类型和辅助函数**

在 `backend/app/main.py` 中，将：

```python
Signal = Literal["neutral", "buy", "sell"]
RiskLevel = Literal["low", "medium", "high"]
```

替换为：

```python
Signal = Literal["neutral", "buy", "sell"]
ReferenceStatus = Literal["positive", "watch", "cautious", "insufficient_data"]
DataCompleteness = Literal["complete", "mostly_complete", "incomplete", "insufficient"]
RiskLevel = Literal["low", "medium", "high"]
```

扩展 `StockSummary`：

```python
class StockSummary(BaseModel):
    code: str
    name: str
    price: float
    change_percent: float
    score: int = Field(ge=0, le=100)
    signal: Signal
    reference_status: ReferenceStatus = "watch"
    reference_label: str = "中性观察"
    primary_support: str = "暂无明确支持因素，适合继续观察。"
    primary_risk: str = "仍需结合估值、波动和数据完整度判断。"
    data_completeness: DataCompleteness = "incomplete"
    data_updated_at: datetime | None = None
```

在 `stock_to_summary` 上方增加：

```python
def determine_data_completeness(stock: Stock, history: list[PricePointDB] | None = None, factors: list[FactorScore] | None = None) -> DataCompleteness:
    if stock.data_status == "partial":
        return "incomplete"
    if history is not None and len(history) < 20:
        return "insufficient"
    if factors is not None and len(factors) >= 4 and stock.updated_at:
        return "complete"
    if stock.updated_at:
        return "mostly_complete"
    return "incomplete"


def determine_reference_status(score: int, signal: str, data_completeness: DataCompleteness, alerts: list[AlertItem] | None = None) -> ReferenceStatus:
    if data_completeness in ("insufficient", "incomplete"):
        return "insufficient_data"
    high_alert_count = len([alert for alert in (alerts or []) if alert.level == "high"])
    if high_alert_count >= 2 or signal == "sell" or score < 45:
        return "cautious"
    if score >= 70 and signal == "buy" and high_alert_count == 0:
        return "positive"
    return "watch"


def reference_label(status: ReferenceStatus) -> str:
    return {
        "positive": "偏积极",
        "watch": "中性观察",
        "cautious": "偏谨慎",
        "insufficient_data": "数据不足",
    }[status]


def build_primary_support(score: int, status: ReferenceStatus) -> str:
    if status == "positive":
        return "当前综合表现靠前，适合加入重点观察，但不代表建议立即买入。"
    if status == "watch":
        return "当前缺少明确优势，适合继续观察后续业绩、资金和价格趋势变化。"
    if status == "cautious":
        return "当前风险项较多，建议先确认风险是否可接受。"
    return "当前数据不足，暂不适合形成明确判断。"


def build_primary_risk(status: ReferenceStatus, data_completeness: DataCompleteness) -> str:
    if data_completeness in ("insufficient", "incomplete"):
        return "关键数据不完整，结论只能弱参考。"
    if status == "positive":
        return "仍需关注估值、仓位和短期波动，不能只凭排序操作。"
    if status == "cautious":
        return "需要重点检查估值、波动、资金流出或盈利变化。"
    return "需要等待更明确的支撑因素或风险变化。"
```

将 `stock_to_summary` 改为：

```python
def stock_to_summary(stock: Stock, history: list[PricePointDB] | None = None, factors: list[FactorScore] | None = None, alerts: list[AlertItem] | None = None) -> StockSummary:
    score = stock.score or 50
    data_completeness = determine_data_completeness(stock, history, factors)
    status = determine_reference_status(score, stock.signal or "neutral", data_completeness, alerts)
    return StockSummary(
        code=stock.code,
        name=stock.name,
        price=stock.price or 0,
        change_percent=stock.change_percent or 0,
        score=score,
        signal=stock.signal or "neutral",
        reference_status=status,
        reference_label=reference_label(status),
        primary_support=build_primary_support(score, status),
        primary_risk=build_primary_risk(status, data_completeness),
        data_completeness=data_completeness,
        data_updated_at=stock.updated_at,
    )
```

- [x] **步骤 4：再次运行测试**

运行：

```powershell
python -m pytest backend/tests/test_user_admin_and_watchlist.py::UserAdminAndWatchlistTest::test_stock_list_returns_ordinary_user_reference_fields -q
```

预期：通过。

- [x] **步骤 5：提交**

```powershell
git add backend/app/main.py backend/tests/test_user_admin_and_watchlist.py
git commit -m "feat: add ordinary user reference fields"
```

---

### 任务 2：后端个股详情普通用户摘要

**文件：**
- 修改：`backend/app/main.py`
- 测试：`backend/tests/test_user_admin_and_watchlist.py`

**接口：**
- 复用 `determine_data_completeness`、`determine_reference_status`、`reference_label`。
- 新增 `build_ordinary_stock_summary(stock, factors, alerts, data_completeness) -> tuple[str, list[str], list[str]]`。

- [x] **步骤 1：添加失败的个股详情测试**

新增：

```python
def test_stock_detail_returns_ordinary_summary_and_data_health(self):
    self.db.add(Stock(code="601398", name="ICBC", price=6.12, change_percent=1.23, score=76, signal="buy"))
    for index in range(30):
        self.db.add(PricePointDB(stock_code="601398", date=f"2026-06-{index + 1:02d}", open=6, high=6.2, low=5.9, close=6 + index * 0.01, volume=10000))
    self.db.add(FactorScoreDB(stock_code="601398", key="valuation", label="Valuation", value=68, description="估值处于合理区间。"))
    self.db.add(FactorScoreDB(stock_code="601398", key="momentum", label="Momentum", value=74, description="价格趋势有所改善。"))
    self.db.commit()

    alice_token = self._login("alice", "Alice@123!")
    response = self.client.get("/api/stocks/601398", headers={"Authorization": f"Bearer {alice_token}"})

    self.assertEqual(response.status_code, 200, response.text)
    payload = response.json()
    self.assertIn("ordinary_summary", payload)
    self.assertIn("data_completeness", payload)
    self.assertIn("support_factors", payload)
    self.assertIn("risk_factors", payload)
    self.assertEqual(payload["disclaimer"], "仅供学习和分析参考，不构成投资建议。")
```

- [x] **步骤 2：运行测试并确认失败**

```powershell
python -m pytest backend/tests/test_user_admin_and_watchlist.py::UserAdminAndWatchlistTest::test_stock_detail_returns_ordinary_summary_and_data_health -q
```

预期：失败，因为响应中还没有普通用户摘要字段。

- [x] **步骤 3：扩展 `StockDetail`**

```python
class StockDetail(BaseModel):
    stock: StockSummary
    factors: list[FactorScore]
    strategies: list[StrategyResult]
    alerts: list[AlertItem]
    history: list[PricePoint]
    ai_summary: str | None = None
    data_status: str
    updated_at: datetime | None = None
    ordinary_summary: str
    support_factors: list[str]
    risk_factors: list[str]
    data_completeness: DataCompleteness
    data_updated_at: datetime | None = None
    disclaimer: str = "仅供学习和分析参考，不构成投资建议。"
```

新增摘要生成函数：

```python
def build_ordinary_stock_summary(stock: Stock, factors: list[FactorScore], alerts: list[AlertItem], data_completeness: DataCompleteness) -> tuple[str, list[str], list[str]]:
    support_factors = [f"{factor.label}: {factor.description}" for factor in factors if factor.value >= 65][:3]
    risk_factors = [alert.message for alert in alerts[:3]]
    if data_completeness in ("insufficient", "incomplete"):
        return "当前数据不足，暂不适合形成明确判断。建议补充数据后再分析。", support_factors, risk_factors or ["关键数据不完整，结论只能弱参考。"]
    status = determine_reference_status(stock.score or 50, stock.signal or "neutral", data_completeness, alerts)
    if status == "positive":
        summary = "当前整体偏积极，适合加入重点观察，但不代表建议立即买入。"
    elif status == "cautious":
        summary = "当前风险项较多，建议谨慎关注，并先完成操作前检查。"
    else:
        summary = "当前整体偏中性，适合继续观察后续业绩、资金和价格趋势变化。"
    if not support_factors:
        support_factors = [build_primary_support(stock.score or 50, status)]
    if not risk_factors:
        risk_factors = [build_primary_risk(status, data_completeness)]
    return summary, support_factors, risk_factors
```

在 `get_stock_detail` 返回前计算：

```python
factor_models = [db_factor_to_model(f) for f in factors]
alert_models = [db_alert_to_model(a) for a in alerts]
data_completeness = determine_data_completeness(stock, history, factor_models)
ordinary_summary, support_factors, risk_factors = build_ordinary_stock_summary(stock, factor_models, alert_models, data_completeness)
```

然后把 `StockDetail(...)` 返回值调整为：

```python
return StockDetail(
    stock=stock_to_summary(stock, history, factor_models, alert_models),
    factors=factor_models,
    strategies=strategy_models,
    alerts=alert_models,
    history=[db_price_to_model(h) for h in history],
    ai_summary=ensure_ai_summary(db, stock, history, factors, alerts),
    data_status=stock.data_status,
    updated_at=stock.updated_at,
    ordinary_summary=ordinary_summary,
    support_factors=support_factors,
    risk_factors=risk_factors,
    data_completeness=data_completeness,
    data_updated_at=stock.updated_at,
)
```

- [x] **步骤 4：再次运行测试**

```powershell
python -m pytest backend/tests/test_user_admin_and_watchlist.py::UserAdminAndWatchlistTest::test_stock_detail_returns_ordinary_summary_and_data_health -q
```

预期：通过。

- [x] **步骤 5：提交**

```powershell
git add backend/app/main.py backend/tests/test_user_admin_and_watchlist.py
git commit -m "feat: add ordinary stock detail summary"
```

---

### 任务 3：后端自选股洞察接口

**文件：**
- 修改：`backend/app/main.py`
- 测试：`backend/tests/test_user_admin_and_watchlist.py`

**接口：**
- 新增 `GET /api/watchlist/insights`。
- 响应模型：`WatchlistInsights`。
- 分组键：`positive`、`watch`、`cautious`、`insufficient_data`。

- [x] **步骤 1：添加失败的接口测试**

新增：

```python
def test_watchlist_insights_groups_user_stocks(self):
    self.db.add_all([
        Stock(code="601398", name="ICBC", price=6.12, change_percent=1.2, score=80, signal="buy", data_status="normal"),
        Stock(code="000001", name="Ping An Bank", price=12.3, change_percent=-0.5, score=40, signal="sell", data_status="normal"),
        WatchlistItem(user_id=self.user_a.id, stock_code="601398", created_at=datetime.now(timezone.utc)),
        WatchlistItem(user_id=self.user_a.id, stock_code="000001", created_at=datetime.now(timezone.utc)),
    ])
    self.db.commit()

    alice_token = self._login("alice", "Alice@123!")
    response = self.client.get("/api/watchlist/insights", headers={"Authorization": f"Bearer {alice_token}"})

    self.assertEqual(response.status_code, 200, response.text)
    payload = response.json()
    self.assertEqual(payload["total"], 2)
    self.assertEqual(payload["disclaimer"], "仅供学习和分析参考，不构成投资建议。")
    self.assertIn("positive", payload["groups"])
    self.assertIn("cautious", payload["groups"])
```

- [x] **步骤 2：运行测试并确认失败**

```powershell
python -m pytest backend/tests/test_user_admin_and_watchlist.py::UserAdminAndWatchlistTest::test_watchlist_insights_groups_user_stocks -q
```

预期：失败，接口返回 404。

- [x] **步骤 3：新增响应模型和路由**

在 `backend/app/main.py` 中新增：

```python
class WatchlistInsights(BaseModel):
    total: int
    groups: dict[ReferenceStatus, list[StockSummary]]
    risk_overview: str
    data_updated_at: datetime | None = None
    disclaimer: str = "仅供学习和分析参考，不构成投资建议。"
```

在 `/api/watchlist/{code}` 这类动态路由之前新增：

```python
@app.get("/api/watchlist/insights", response_model=WatchlistInsights)
def get_watchlist_insights(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    watchlist_items = db.query(WatchlistItem).filter(WatchlistItem.user_id == user.id).all()
    codes = [item.stock_code for item in watchlist_items]
    stocks = db.query(Stock).filter(Stock.code.in_(codes)).all() if codes else []
    groups: dict[str, list[StockSummary]] = {
        "positive": [],
        "watch": [],
        "cautious": [],
        "insufficient_data": [],
    }
    latest_updated_at = None
    for stock in stocks:
        summary = stock_to_summary(stock)
        groups[summary.reference_status].append(summary)
        if stock.updated_at and (latest_updated_at is None or stock.updated_at > latest_updated_at):
            latest_updated_at = stock.updated_at
    cautious_count = len(groups["cautious"])
    insufficient_count = len(groups["insufficient_data"])
    if cautious_count:
        risk_overview = f"当前自选股中有 {cautious_count} 只需要谨慎关注。"
    elif insufficient_count:
        risk_overview = f"当前自选股中有 {insufficient_count} 只数据不足，建议先补充数据。"
    else:
        risk_overview = "当前自选股未发现集中高风险提示，仍需结合仓位和估值检查。"
    return WatchlistInsights(
        total=len(stocks),
        groups=groups,
        risk_overview=risk_overview,
        data_updated_at=latest_updated_at,
    )
```

- [x] **步骤 4：再次运行测试**

```powershell
python -m pytest backend/tests/test_user_admin_and_watchlist.py::UserAdminAndWatchlistTest::test_watchlist_insights_groups_user_stocks -q
```

预期：通过。

- [x] **步骤 5：提交**

```powershell
git add backend/app/main.py backend/tests/test_user_admin_and_watchlist.py
git commit -m "feat: add watchlist insights endpoint"
```

---

### 任务 4：前端类型和 API 支持

**文件：**
- 修改：`frontend/src/types/index.ts`
- 修改：`frontend/src/services/api.ts`
- 测试：`frontend/src/services/api.test.ts`

**接口：**
- 消费后端 `WatchlistInsights`。
- 新增 `getWatchlistInsights()`。

- [x] **步骤 1：新增类型**

在 `frontend/src/types/index.ts` 中新增：

```ts
export type ReferenceStatus = 'positive' | 'watch' | 'cautious' | 'insufficient_data';
export type DataCompleteness = 'complete' | 'mostly_complete' | 'incomplete' | 'insufficient';
```

扩展 `StockSummary`：

```ts
  reference_status?: ReferenceStatus;
  reference_label?: string;
  primary_support?: string;
  primary_risk?: string;
  data_completeness?: DataCompleteness;
  data_updated_at?: string | null;
```

扩展 `StockDetail`：

```ts
  ordinary_summary?: string;
  support_factors?: string[];
  risk_factors?: string[];
  data_completeness?: DataCompleteness;
  data_updated_at?: string | null;
  disclaimer?: string;
```

新增：

```ts
export interface WatchlistInsights {
  total: number;
  groups: Record<ReferenceStatus, StockSummary[]>;
  risk_overview: string;
  data_updated_at?: string | null;
  disclaimer: string;
}
```

- [x] **步骤 2：新增 API 函数**

在 `frontend/src/services/api.ts` 中导入 `WatchlistInsights`，并新增：

```ts
export async function getWatchlistInsights(): Promise<WatchlistInsights> {
  const response = await fetch(`${getApiBase()}/api/watchlist/insights`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) throw new Error('fetchWatchlistInsights');
  return response.json() as Promise<WatchlistInsights>;
}
```

- [x] **步骤 3：运行前端测试**

```powershell
cd frontend
npm test -- --run
```

预期：现有测试通过。

- [x] **步骤 4：提交**

```powershell
git add frontend/src/types/index.ts frontend/src/services/api.ts
git commit -m "feat: add watchlist insight client types"
```

---

### 任务 5：首页自选股洞察 UI

**文件：**
- 修改：`frontend/src/pages/HomeScreen.tsx`
- 修改：`frontend/src/i18n/locales/zh.ts`
- 修改：`frontend/src/i18n/locales/zh-Hant.ts`
- 修改：`frontend/src/i18n/locales/en.ts`

**接口：**
- 使用 `getWatchlistInsights`。
- 按以下顺序展示分组：`positive`、`watch`、`cautious`、`insufficient_data`。

- [x] **步骤 1：前端修改前阅读 Expo 56 文档**

打开 `https://docs.expo.dev/versions/v56.0.0/`，确认本任务使用的 React Native 基础组件 `View`、`Text`、`Pressable`、`ActivityIndicator` 没有 Expo 56 特殊限制。

- [x] **步骤 2：新增文案**

在各语言文件的 `home` 下新增等价文案：

```ts
watchlistInsights: '今日自选股参考',
watchlistRiskOverview: '自选股风险概览',
groupPositive: '重点关注',
groupWatch: '继续观察',
groupCautious: '谨慎关注',
groupInsufficientData: '数据不足',
investmentDisclaimer: '仅供学习和分析参考，不构成投资建议。',
```

- [x] **步骤 3：在 `HomeScreen.tsx` 中加载洞察数据**

新增状态：

```ts
const [watchlistInsights, setWatchlistInsights] = useState<WatchlistInsights | null>(null);
const [isLoadingInsights, setIsLoadingInsights] = useState(false);
```

自选股刷新成功后调用：

```ts
setIsLoadingInsights(true);
try {
  const insights = await getWatchlistInsights();
  setWatchlistInsights(insights);
} finally {
  setIsLoadingInsights(false);
}
```

- [x] **步骤 4：在股票列表上方渲染分组卡片**

在现有 `stockList` 之前渲染：

```tsx
{watchlistInsights && (
  <View style={styles.insightPanel}>
    <Text style={styles.sectionTitle}>{t.home.watchlistInsights}</Text>
    <Text style={styles.subtleText}>{watchlistInsights.risk_overview}</Text>
    {(['positive', 'watch', 'cautious', 'insufficient_data'] as const).map((groupKey) => (
      <View key={groupKey} style={styles.insightGroup}>
        <Text style={styles.insightGroupTitle}>{groupTitle(groupKey, t)}</Text>
        {watchlistInsights.groups[groupKey].slice(0, 3).map((stock) => (
          <Pressable key={stock.code} style={styles.insightItem} onPress={() => handleStockPress(stock.code)}>
            <Text style={styles.insightName}>{stock.name}</Text>
            <Text style={styles.insightReason}>{stock.primary_support ?? stock.reference_label}</Text>
          </Pressable>
        ))}
      </View>
    ))}
    <Text style={styles.disclaimerText}>{watchlistInsights.disclaimer}</Text>
  </View>
)}
```

新增 helper：

```ts
function groupTitle(status: ReferenceStatus, t: Translation): string {
  return {
    positive: t.home.groupPositive,
    watch: t.home.groupWatch,
    cautious: t.home.groupCautious,
    insufficient_data: t.home.groupInsufficientData,
  }[status];
}
```

如果本地 i18n 类型名称不同，从 `frontend/src/i18n/types.ts` 导入项目实际使用的类型。

- [x] **步骤 5：运行前端测试**

```powershell
cd frontend
npm test -- --run
```

预期：通过。

- [x] **步骤 6：提交**

```powershell
git add frontend/src/pages/HomeScreen.tsx frontend/src/i18n/locales/zh.ts frontend/src/i18n/locales/zh-Hant.ts frontend/src/i18n/locales/en.ts
git commit -m "feat: show watchlist insights on home"
```

---

### 任务 6：前端个股详情摘要与数据健康 UI

**文件：**
- 修改：`frontend/src/pages/StockDetailScreen.tsx`
- 修改：`frontend/src/i18n/locales/zh.ts`
- 修改：`frontend/src/i18n/locales/zh-Hant.ts`
- 修改：`frontend/src/i18n/locales/en.ts`

**接口：**
- 使用 `ordinary_summary`、`support_factors`、`risk_factors`、`data_completeness`、`data_updated_at`、`disclaimer`。

- [x] **步骤 1：新增文案**

在 `detail` 下新增：

```ts
ordinarySummary: '普通用户摘要',
supportFactors: '主要支撑因素',
riskFactors: '主要风险因素',
dataHealth: '数据健康',
importantHolderChanges: '重要股东变动',
```

将中文语言文件里的 `institutionHoldings` 文案从“机构持仓”改为“重要股东变动”，英文改为 `Important Holder Changes`。

- [x] **步骤 2：在价格卡下方渲染摘要**

在 `StockDetailScreen.tsx` 的价格面板之后增加：

```tsx
<View style={styles.summaryPanel}>
  <Text style={styles.sectionTitle}>{t.detail.ordinarySummary}</Text>
  <Text style={styles.summaryText}>{detail.ordinary_summary ?? detail.ai_summary}</Text>
  <View style={styles.dataHealthRow}>
    <Text style={styles.dataHealthLabel}>{t.detail.dataHealth}</Text>
    <Text style={styles.dataHealthValue}>{detail.data_completeness ?? detail.data_status}</Text>
  </View>
  <Text style={styles.disclaimerText}>{detail.disclaimer ?? t.home.investmentDisclaimer}</Text>
</View>
```

- [x] **步骤 3：在因子区前展示支撑因素和风险因素**

新增：

```tsx
{Boolean(detail.support_factors?.length) && (
  <View style={styles.reasonPanel}>
    <Text style={styles.sectionTitle}>{t.detail.supportFactors}</Text>
    {detail.support_factors!.map((item) => <Text key={item} style={styles.reasonText}>• {item}</Text>)}
  </View>
)}
{Boolean(detail.risk_factors?.length) && (
  <View style={styles.reasonPanel}>
    <Text style={styles.sectionTitle}>{t.detail.riskFactors}</Text>
    {detail.risk_factors!.map((item) => <Text key={item} style={styles.reasonText}>• {item}</Text>)}
  </View>
)}
```

- [x] **步骤 4：运行前端测试**

```powershell
cd frontend
npm test -- --run
```

预期：通过。

- [x] **步骤 5：提交**

```powershell
git add frontend/src/pages/StockDetailScreen.tsx frontend/src/i18n/locales/zh.ts frontend/src/i18n/locales/zh-Hant.ts frontend/src/i18n/locales/en.ts
git commit -m "feat: add ordinary stock detail summary"
```

---

### 任务 7：验证与回归检查

**文件：**
- 不计划修改源代码。

**接口：**
- 验证后端和前端行为是否一致。

- [x] **步骤 1：运行后端测试**

```powershell
python -m pytest backend/tests -q
```

预期：通过。

- [x] **步骤 2：运行前端测试**

```powershell
cd frontend
npm test -- --run
```

预期：通过。

- [x] **步骤 3：运行 TypeScript 检查**

```powershell
cd frontend
npx tsc --noEmit
```

预期：通过。

- [x] **步骤 4：手动 API 冒烟测试**

启动后端：

```powershell
python backend/start.py
```

调用：

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/watchlist/insights -Headers @{ Authorization = "Bearer <token>" }
```

预期 JSON 包含：`total`、`groups.positive`、`groups.watch`、`groups.cautious`、`groups.insufficient_data`、`risk_overview`、`disclaimer`。

- [x] **步骤 5：手动 App 冒烟测试**

```powershell
cd frontend
npm run web
```

预期：
- 首页显示“今日自选股参考”。
- 原有自选股行仍正常渲染。
- 详情页显示普通用户摘要和数据健康。
- 页面中不出现“立即买入”“强烈卖出”“必涨”“稳赚”“最佳买点”等文案。

---

## 自检

**需求覆盖：** 本计划覆盖产品分析中的第一阶段 MVP：克制参考表达、数据新鲜度/完整度、普通用户摘要、自选股分组、风险导向详情页、重要股东文案调整。会员体系、付费权限、组合仓位、导出、管理端分析和专业版能力已明确延期。

**占位符检查：** 文档中没有 `TBD`、`TODO`、`implement later` 或未定义路径。任务 5 中关于 i18n 类型的说明，是为了适配当前项目实际导出的类型名。

**类型一致性：** 后端 `ReferenceStatus` 与前端 `ReferenceStatus` 一致。后端 `DataCompleteness` 与前端 `DataCompleteness` 一致。`WatchlistInsights.groups` 在前后端都使用同样四个分组键。
