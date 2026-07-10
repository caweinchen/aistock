# 普通用户体验后端后继开发计划

**负责人：** 后端工作机。

**目标：** 与前端开发解耦，继续稳定普通用户可信度与留存相关 API 契约，并把复杂个股装配逻辑迁移到 service/assembler 层。

**范围：** 后端 API 契约、service/assembler 拆分、后端测试和后端验证。

## 约束

- 本计划由后端工作机执行；前端工作机未经用户明确允许不得修改后端文件。
- 不修改现有 API 路径。
- 保持现有前端客户端兼容。
- 新增响应字段应为可选字段，或提供安全默认值。
- 所有未完成事项必须使用显式 `TODO` 复选框追踪。
- 前端依赖新增字段前，后端需先在计划或规格中记录响应结构。

## 后端工作机负责文件

- `backend/app/routers/*`
- `backend/app/schemas.py`
- `backend/app/ordinary_user.py`
- `backend/app/stock_summary.py`
- 后续新增的 `backend/app/` 下 service 或 assembler 模块
- `backend/tests/*`
- 后端专属验证记录或计划文档

## 避免触碰前端文件

- `frontend/**`
- 前端 package/config 文件
- 前端 i18n、页面、组件文件

## 需要维护的 API 契约

- `GET /api/stocks/{code}`
  - 现有字段保持不变。
  - 给前端消费的可选字段：
    - `data_health`
    - `risk_explanations`
    - `buy_checklist`
    - `sell_checklist`
- `GET /api/watchlist/insights`
  - 现有字段保持不变。
  - 给前端消费的可选字段：
    - `data_health_overview`

### 响应结构与默认行为

- `data_health`: 可为 `null`；存在时 `completeness` 默认为 `incomplete`，列表字段默认为空列表，`updated_at` 默认为 `null`。
- `risk_explanations`: 默认为空列表；每个风险项的 `evidence` 默认为空列表。
- `buy_checklist` / `sell_checklist`: 可为 `null`；存在时 `items` 默认为空列表，检查项 `user_confirm_required` 默认为 `false`。
- `data_health_overview`: 可为 `null`；存在时计数默认为 `0`，`latest_updated_at` 默认为 `null`。

## TODO 跟踪

- [x] TODO: 在后端工作机确认当前后端测试通过。
- [x] TODO: 确认 `DataHealth`、`RiskExplanation`、`PreTradeChecklist` 和检查项 schema 默认值保持向后兼容。
- [x] TODO: 将 `backend/app/routers/stocks.py` 中复杂个股详情装配逻辑拆到 service/assembler 模块。
- [x] TODO: 拆分后保持 router 模块只负责参数、鉴权、调用和响应。
- [x] TODO: 增加数据健康四种完整度场景的后端测试。
- [x] TODO: 增加风险说明书测试，覆盖估值、波动、基本面、股东变化、分红、数据质量输入。
- [x] TODO: 增加买入前/卖出前检查清单响应结构测试。
- [x] TODO: 增加自选股洞察 `data_health_overview` 测试。
- [x] TODO: 运行完整后端验证，并把结果记录回本计划。

## 建议验证

```powershell
python -m pytest backend/tests -q
```

如果加密相关测试需要本地后端服务，按后端拆分计划中的方式启动临时服务，测试后关闭。

## 验证记录

- 2026-07-11：在后端工作机启动临时 API 服务后运行 `python -m pytest backend/tests -q`。
- 结果：62 项测试通过，0 失败，5 个参数化子测试通过。
- 已知警告：6 条，均为现有 SQLAlchemy `declarative_base()` 和 FastAPI `on_event` 弃用警告。

## 前端交接说明

- 前端依赖新增字段前，后端先记录字段名、可空性和默认行为。
- 前端开始实现后，字段名应保持稳定。
- 如果某字段暂时无法提供，后端可省略该字段或返回 `null`；前端会展示旧字段回退或空态。
- 后端分支不要求同时包含前端修改。

