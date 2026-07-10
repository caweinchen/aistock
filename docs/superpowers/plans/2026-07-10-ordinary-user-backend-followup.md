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

## TODO 跟踪

- [ ] TODO: 在后端工作机确认当前后端测试通过。
- [ ] TODO: 确认 `DataHealth`、`RiskExplanation`、`PreTradeChecklist` 和检查项 schema 默认值保持向后兼容。
- [ ] TODO: 将 `backend/app/routers/stocks.py` 中复杂个股详情装配逻辑拆到 service/assembler 模块。
- [ ] TODO: 拆分后保持 router 模块只负责参数、鉴权、调用和响应。
- [ ] TODO: 增加数据健康四种完整度场景的后端测试。
- [ ] TODO: 增加风险说明书测试，覆盖估值、波动、基本面、股东变化、分红、数据质量输入。
- [ ] TODO: 增加买入前/卖出前检查清单响应结构测试。
- [ ] TODO: 增加自选股洞察 `data_health_overview` 测试。
- [ ] TODO: 运行完整后端验证，并把结果记录回本计划。

## 建议验证

```powershell
python -m pytest backend/tests -q
```

如果加密相关测试需要本地后端服务，按后端拆分计划中的方式启动临时服务，测试后关闭。

## 前端交接说明

- 前端依赖新增字段前，后端先记录字段名、可空性和默认行为。
- 前端开始实现后，字段名应保持稳定。
- 如果某字段暂时无法提供，后端可省略该字段或返回 `null`；前端会展示旧字段回退或空态。
- 后端分支不要求同时包含前端修改。

