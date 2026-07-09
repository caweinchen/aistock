# 第二阶段：自选股智能参考增强设计

## 1. 背景

阶段 1 已完成普通用户可信度与留存增强：个股详情具备数据健康、风险解释和操作前检查清单，首页自选股洞察具备基础分组和数据健康概览。

阶段 2 的目标不是生成更强的买卖信号，而是把“自选股列表”升级为“自选股池分析助手”。产品应帮助普通用户理解今天应该优先看哪些自选股、为什么值得关注、哪些风险更高、哪些因为数据不足不能形成明确参考。

## 2. 产品目标

第二阶段长期目标：

- 在用户自选股池内提供可解释的关注优先级。
- 输出今日观察建议，帮助用户形成复查习惯。
- 展示每只自选股的主要支撑因素、主要风险因素和数据健康状态。
- 支持综合参考、风险优先、数据完整度、最近变化等排序维度。
- 为后续普通会员体系保留核心价值，但本阶段不实现会员、支付或权限限制。

第一轮落地目标：

- 新增自选股智能参考规则层。
- 增强现有 `/api/watchlist/insights`，不新增独立页面。
- 在首页现有“自选股洞察”面板内显示机会雷达、今日观察建议和更清晰的分组理由。
- 修正现有 watchlist insights 中数据健康统计与分组统计口径混用的问题。

## 3. 非目标

本阶段不做：

- 全市场荐股或全市场筛选。
- 直接买卖建议、收益承诺或确定性排名。
- 会员、订阅、支付、管理后台。
- 完整持仓管理、仓位权重、组合风险分析。
- 独立自选股洞察页的完整 UI。
- 用户可勾选并持久化的待办清单。

禁止文案包括但不限于：

- 立即买入
- 强烈卖出
- 必涨
- 稳赚
- 最佳买点
- 今日牛股
- 必买股票

允许使用的克制表达：

- 重点观察
- 继续观察
- 谨慎关注
- 数据不足
- 风险较多
- 适合进一步查看详情
- 建议先补充数据后再参考

## 4. 阶段拆分

### 4.1 阶段 2A：自选股洞察数据模型

新增后端产品规则模块 `backend/app/watchlist_intelligence.py`，负责把已有自选股、数据健康和普通用户解释结果组合成自选股池级别的参考结果。

该模块只做产品决策表达，不直接访问数据库。API 层负责查询数据并传入规则模块。

核心输出：

- 自选股单项洞察。
- 自选股池雷达摘要。
- 今日观察建议。
- 排序分组结果。
- 数据健康统计。

### 4.2 阶段 2B：首页轻量增强

扩展现有 `/api/watchlist/insights` 响应，不破坏已有字段：

- 保留 `total`
- 保留 `groups`
- 保留 `risk_overview`
- 保留 `data_health_overview`
- 新增可选字段用于前端渐进展示

首页仍使用现有“自选股洞察”面板，新增：

- 机会雷达摘要
- 今日观察建议
- 分组理由
- 每组最多展示若干代表股票

### 4.3 阶段 2C：排序与筛选维度

在 2A/2B 稳定后，支持以下排序维度：

- 综合参考
- 风险优先
- 数据完整度
- 最近变化

第一版可以由后端返回预计算排序结果，前端只做切换。后续如果新增独立页面，再把排序体验展开。

### 4.4 阶段 2D：独立自选股洞察页预留

当首页信息密度过高时，再新增独立页面。该页面不是本轮实现目标，但接口和类型应预留扩展空间。

未来页面可承载：

- 自选股池总览
- 分组统计
- 排序切换
- 每只股票的支撑/风险卡片
- 数据不足清单
- 后续会员能力入口

## 5. 后端设计

### 5.1 新增规则模块

新增 `backend/app/watchlist_intelligence.py`。

建议定义：

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

WatchlistFocusLevel = Literal["priority", "watch", "cautious", "insufficient_data"]
WatchlistSortMode = Literal["overall", "risk", "data_health", "recent_change"]
ObservationType = Literal["priority", "risk", "data_quality", "refresh", "balanced"]


@dataclass
class WatchlistStockInsightResult:
    code: str
    name: str
    focus_level: WatchlistFocusLevel
    focus_label: str
    focus_reason: str
    support_points: list[str] = field(default_factory=list)
    risk_points: list[str] = field(default_factory=list)
    data_completeness: str = "incomplete"
    score: int | None = None
    risk_score: int = 0
    priority_score: int = 0
    updated_at: datetime | None = None


@dataclass
class WatchlistRadarResult:
    title: str
    summary: str
    priority_count: int = 0
    cautious_count: int = 0
    insufficient_count: int = 0
    average_score: float | None = None


@dataclass
class WatchlistObservationResult:
    type: ObservationType
    title: str
    description: str
    stock_codes: list[str] = field(default_factory=list)


@dataclass
class WatchlistIntelligenceResult:
    radar: WatchlistRadarResult
    observations: list[WatchlistObservationResult] = field(default_factory=list)
    insights: list[WatchlistStockInsightResult] = field(default_factory=list)
    sort_modes: list[WatchlistSortMode] = field(default_factory=list)
```

建议暴露：

```python
def build_watchlist_intelligence(stock_contexts) -> WatchlistIntelligenceResult: ...
def sort_watchlist_insights(insights, mode: WatchlistSortMode) -> list[WatchlistStockInsightResult]: ...
```

`stock_contexts` 可以先用轻量 dataclass 或 `SimpleNamespace` 表达，包含：

- stock
- summary
- data_health
- risk_explanations
- support_factors
- risk_factors

### 5.2 API 模型扩展

在 `backend/app/main.py` 中新增 Pydantic 模型：

- `WatchlistStockInsight`
- `WatchlistRadar`
- `WatchlistObservation`
- `WatchlistIntelligence`

扩展 `WatchlistInsights`：

```python
class WatchlistInsights(BaseModel):
    ...
    intelligence: WatchlistIntelligence | None = None
```

所有新增字段必须有默认值或可为空，避免旧缓存和旧前端崩溃。

### 5.3 分组口径

当前 `get_watchlist_insights` 中 `insufficient_count` 同时承担了数据健康统计和分组数量含义，容易导致统计不准确。第二阶段应拆成：

- `data_insufficient_count`
- `group_insufficient_count`

`data_health_overview.insufficient_count` 只表示数据健康不足数量。

`groups["insufficient_data"]` 只表示普通参考分组中的数据不足股票。

## 6. 前端设计

### 6.1 类型扩展

在 `frontend/src/types/index.ts` 增加：

- `WatchlistFocusLevel`
- `WatchlistSortMode`
- `ObservationType`
- `WatchlistStockInsight`
- `WatchlistRadar`
- `WatchlistObservation`
- `WatchlistIntelligence`

扩展：

```ts
export interface WatchlistInsights {
  ...
  intelligence?: WatchlistIntelligence | null;
}
```

### 6.2 首页展示

在 `HomeScreen.tsx` 的现有 `watchlistInsights` 面板中增强，不新增页面。

展示顺序：

1. 现有 `risk_overview`
2. 数据健康概览
3. 机会雷达摘要
4. 今日观察建议
5. 现有四类分组列表
6. 免责声明

今日观察建议只读展示，不做勾选和持久化。

### 6.3 交互边界

第一轮不新增复杂筛选器。若需要展示排序维度，可以先显示“当前按综合参考排序”，具体切换留到 2C。

点击股票仍进入现有个股详情页。

## 7. 数据流

1. 用户打开首页。
2. 前端调用 `/api/watchlist/insights`。
3. API 查询用户自选股。
4. API 为每只股票构建 `StockSummary`。
5. API 复用阶段 1 的数据健康和风险解释逻辑。
6. API 调用 `build_watchlist_intelligence`。
7. API 返回兼容旧字段的新响应。
8. 首页渐进展示新洞察。

## 8. 测试策略

后端：

- 新增 `backend/tests/test_watchlist_intelligence.py`
- 测试重点观察、谨慎关注、数据不足的分类规则。
- 测试 radar 统计。
- 测试 observation 生成。
- 扩展 `test_user_admin_and_watchlist.py`，验证 API 返回 `intelligence`。

前端：

- 扩展 `frontend/src/services/api.test.ts`，验证新字段兼容。
- 运行 TypeScript 检查。
- 若现有前端测试覆盖 HomeScreen，则补充首页渲染断言；如果没有稳定测试环境，至少保证 API 类型测试和 `tsc --noEmit` 通过。

验证：

- `python -m pytest backend/tests -q`
- `cd frontend && npm test -- --run`
- `cd frontend && npx tsc --noEmit`

## 9. 发布与验收

第一轮完成标准：

- `/api/watchlist/insights` 保持旧字段兼容。
- 响应中包含 `intelligence`。
- 首页出现机会雷达摘要和今日观察建议。
- 数据健康统计不再与分组统计混用。
- 页面文案不出现禁止交易指令。
- 后端测试、前端测试和 TypeScript 检查通过。

第二阶段整体完成标准：

- 自选股池具备可解释的重点观察、继续观察、谨慎关注、数据不足分组。
- 用户能理解每只股票进入某个分组的原因。
- 用户能看到今天优先检查什么，而不是只看到股票列表。
- 排序维度能支持后续独立洞察页。
- 能自然衔接普通会员体系，但尚未引入会员和支付。

## 10. 风险与缓解

风险：被用户误解为荐股。

缓解：所有排序和分组使用“参考、观察、风险、数据不足”表达，不使用买卖指令。

风险：首页信息过载。

缓解：第一轮只展示摘要和少量建议，详细解释继续放在个股详情页。

风险：后端 `main.py` 继续膨胀。

缓解：规则逻辑放入 `watchlist_intelligence.py`，API 层只做数据装配和模型转换。

风险：数据不足股票被错误归入积极分组。

缓解：数据健康不足时强制降级到 `insufficient_data` 或谨慎展示。

## 11. 实施顺序

1. 后端规则模块与单元测试。
2. API 模型和 `/api/watchlist/insights` 集成。
3. 前端类型和 API 测试。
4. 首页轻量展示。
5. 全量验证。
6. 更新路线图和实施计划状态。

