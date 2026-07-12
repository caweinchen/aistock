# AIStock 双机交付治理设计

## 目标

将现有规格书、实施计划、API 契约和项目看板整理成可由前端电脑与后端电脑独立领取、明确交接、共同验收的交付链，避免单份大型计划同时要求两台电脑跨职责修改代码。

## 当前进度判断

截至 2026-07-12，AIStock 主产品已经完成：

- 普通用户 MVP、可信度与留存增强。
- 自选股智能参考增强的已规划切片。
- 股票详情与全局导航前端接入及验证。
- 核心 auth、stocks、watchlist、backtests API 契约。
- 后端路由第一阶段拆分。
- 股票详情 assembler、股票数据 service、股票分析 service 拆分。
- Gitee 主远端、GitHub 辅助镜像与 Multica Gitee-only 项目资源。

当前未完成或需要决策的主线：

- 后端长期结构约束：`main.py` 仅负责 app 装配，router 不重新吸收复杂业务逻辑。
- 离线优先登录与缓存计划：已有完整计划，但尚未获得当前阶段重新确认，暂列前端候选而非自动开工项。
- 阶段联调硬门禁：已有设计，但尚需落入协议、角色文件和看板。
- GitHub 辅助镜像仍受网络阻塞，需要持续 TODO，而不阻塞 Gitee 主线协作。

## 文档分层

### 阶段规格

阶段规格定义用户目标、数据语义、边界和验收条件，不直接混写两台电脑的实现步骤。

### 后端交付计划

后端计划只能修改后端实现、后端测试、数据库迁移和 API 契约。完成后交付：

- Gitee `main` SHA。
- 后端验证证据。
- 更新后的 `docs/contracts/`。
- 前端可依赖的兼容性说明。

### 前端交付计划

前端计划只能修改前端实现、前端测试和联调配置。它必须依赖已冻结的契约版本，不通过猜测补足后端语义。

### 联调计划

联调计划不承载新的业务实现，只描述两端基准、环境、真实接口路径、成功/失败场景、证据和缺陷归属。

### 当前项目看板

`docs/superpowers/roadmaps/current-project-board.md` 是当前任务领取和交接的唯一入口。历史规格与计划保留作为证据，但不得仅凭历史未勾选项自动开工。

## 标准切片状态

每个当前切片使用以下状态：

1. `Spec Ready`
2. `Backend In Progress`
3. `Contract Ready`
4. `Frontend In Progress`
5. `Awaiting Integration`
6. `Integration Passed`
7. `Completed`

纯前端或纯后端切片可以将不适用阶段标为 `N/A`，但必须在看板说明原因。

## 看板字段

每个未完成切片至少记录：

- Owner
- Current status
- Spec
- Backend plan
- Contract
- Frontend plan
- Integration plan or evidence
- Gitee baseline SHA
- GitHub mirror status/TODO
- Blockers
- Next handoff

## 门禁规则

- 后端接口或数据语义变更未形成契约，不得进入前端实现。
- 后端和前端未分别通过本机验证，不得进入 `Awaiting Integration`。
- 未使用真实接口完成关键路径验证，不得标记 `Integration Passed`。
- 门禁失败时新增带 Owner 和验收条件的 TODO，下一阶段保持 Pending。
- Gitee 主远端未同步不得交接；GitHub 失败可记录 TODO 后继续。
- 纯文档整理可以豁免运行联调，但必须通过文档检查并说明未改变运行行为。

## 历史文档策略

- 已完成历史计划不做全量拆分，保留其实施证据。
- 大型混合计划中的后继工作必须新建聚焦的 backend/frontend/integration 计划。
- 明显过期或状态不明的计划在看板列为 `Needs Decision`，不得伪装成进行中。
- 与 AIStock 无关的独立项目文档从本仓库删除。

## TODO Tracking

- [x] TODO：盘点现有规格、计划、契约、角色和看板。
- [x] TODO：确认移除与 AIStock 无关的游戏文档。
- [x] TODO：定义双机交付链、状态和看板字段。
- [x] TODO：将阶段联调门禁落入协议与角色文件。
- [x] TODO：按本设计重构当前项目看板。
- [ ] TODO：为下一项获批功能分别建立聚焦的 backend/frontend/integration 计划。
