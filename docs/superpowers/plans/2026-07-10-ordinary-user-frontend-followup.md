# 普通用户体验前端后继开发计划

**负责人：** 前端工作机。

**目标：** 按前后端分离原则继续推进普通用户可信度与留存体验。本机只做前端实现，消费现有或后端工作机提供的 API 契约，不直接修改后端代码。

**范围：** 数据健康、风险说明书、操作前检查清单相关的前端页面、组件、服务层、类型、i18n 和前端测试。

## 约束

- 本机只开发前端代码。
- 未经用户在同一任务中明确允许，不修改 `backend/` 下任何文件。
- 不修改 API 路径。
- 对后端新增字段采用防御式读取，兼容旧响应。
- 所有未完成事项必须使用显式 `TODO` 复选框追踪。
- 如果发现需要后端契约变更，只记录到后端后继计划，不在本机直接修改后端代码。

## 本机负责文件

- `frontend/src/pages/HomeScreen.tsx`
- `frontend/src/pages/StockDetailScreen.tsx`
- `frontend/src/components/*`
- `frontend/src/services/api.ts`
- `frontend/src/services/*.test.ts`
- `frontend/src/hooks/*`
- `frontend/src/i18n/*`
- `frontend/src/types/index.ts`
- 前端专属验证记录或计划文档

## 未经允许不得触碰

- `backend/**`
- `db/**`
- 后端部署脚本
- 后端 router、schema、database、测试文件

## 前端消费的后端契约

前端必须同时兼容旧响应和新响应。

- `GET /api/stocks/{code}`
  - 可选新字段：`data_health`、`risk_explanations`、`buy_checklist`、`sell_checklist`
  - 旧字段回退：`data_completeness`、`data_updated_at`、`support_factors`、`risk_factors`
- `GET /api/watchlist/insights`
  - 可选新字段：`data_health_overview`
  - 缺少该字段时，首页仍应正常展示已有自选股洞察内容。

## TODO 跟踪

- [ ] TODO: 确认前端类型中是否已有 `DataHealth`、`RiskExplanation`、`PreTradeChecklist` 和检查项状态。
- [ ] TODO: 补齐或调整 API 归一化逻辑，让缺失新字段的旧响应可以回退到旧字段。
- [ ] TODO: 在首页自选股洞察中展示数据健康概览。
- [ ] TODO: 在个股详情普通用户摘要附近展示数据健康区块。
- [ ] TODO: 在个股详情专业因子和策略数据之前展示风险说明书区块。
- [ ] TODO: 实现买入前/卖出前检查清单 UI，用户确认状态只保存在本地 UI。
- [ ] TODO: 检查前端文案，避免出现直接交易指令类表达。
- [ ] TODO: 新增或更新前端测试，覆盖旧响应回退、首页数据健康、个股风险说明、检查清单交互。
- [ ] TODO: 运行前端验证命令，并把结果记录回本计划。

## 建议验证

```powershell
cd frontend
npm test -- --runInBand
npm run typecheck
```

如果项目没有定义某个脚本，将缺失脚本作为验证记录写入本计划，不通过修改后端绕过。

## 集成说明

- 后端新增字段对前端来说必须是可选字段。
- 如果前端实现暴露后端数据缺口，在 `2026-07-10-ordinary-user-backend-followup.md` 增加 TODO，并继续以前端空态或旧字段回退完成当前 UI。
- 只要存在安全回退或占位状态，前端 UI 工作不阻塞等待后端实现。

