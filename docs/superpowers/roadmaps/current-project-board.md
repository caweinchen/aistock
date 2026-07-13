# Current Project Board

本看板是两台电脑领取当前 AIStock 工作、交接和判断阶段准入的唯一入口。历史规格与计划仅作为证据；未列入本看板的历史 TODO 不得自动开工。

## Current Checkpoint

- Updated: 2026-07-12
- Primary remote: Gitee `main`
- Current baseline: `be2de5202db56bf6583a17c41f938ff1c3915597`
- GitHub mirror: synchronized to `be2de5202db56bf6583a17c41f938ff1c3915597`
- Current phase: documentation governance and next-slice selection
- Integration gate: documentation-only change, runtime integration exempt because no product behavior or API contract changes
- Blockers: 下一产品切片尚未由用户选定
- Next handoff: 用户选择下一切片后，先锁定阶段规格，再由后端或前端 owner 建立聚焦计划

## Completed Baseline

- [x] TODO: 普通用户 MVP、可信度与留存增强完成。
- [x] TODO: 自选股智能参考增强的已规划切片完成。
- [x] TODO: 股票详情、全局导航和普通用户前端联调完成。
- [x] TODO: auth、stocks、watchlist、backtests 核心 API 契约完成。
- [x] TODO: 后端路由第一阶段拆分完成。
- [x] TODO: 股票详情 assembler、股票数据 service、股票分析 service 拆分完成。
- [x] TODO: Gitee 主远端、双远端规则和 Multica Gitee-only 项目资源完成。

## Current Work Queue

### Stage 2C Watchlist Risk Backend

- Owner: backend machine
- Current status: `Implementation Complete - Verification Pending`
- Plan: `docs/superpowers/plans/2026-07-12-watchlist-risk-recent-change.md`
- Contract: `docs/contracts/watchlist.md`
- Backend branch: `feature/backend/MUL-12-watchlist-risk`
- Migration: reversible `watchlist_insight_baselines` up/down SQL scripts
- Next handoff: after backend regression and dual-remote SHA verification, the frontend may integrate the additive `intelligence.risk_overview`, `industry_concentration`, and per-stock `recent_change` fields.
- [x] TODO: Owner `backend machine` — implement the Stage 2C backend contract without deterministic trading advice.
- [ ] TODO: Owner `frontend machine` — integrate only after the backend branch is accepted.

### Backend Structural Guard

- Owner: backend machine
- Current status: `Spec Ready`
- Spec: `docs/superpowers/specs/2026-07-10-backend-main-decomposition-design.md`
- Backend plan: 下一次出现复杂 router/service 变更时新建聚焦后端计划；不继续扩张旧大型计划
- Contract: `N/A`，除非重构改变接口或数据语义
- Frontend plan: `N/A`
- Integration: 纯内部重构且契约不变时记录豁免；否则进入真实接口联调
- Gitee baseline SHA: TODO — 后端机领取时填写
- GitHub mirror: TODO — 网络恢复后补推
- Blockers: 无当前实现任务；这是长期结构门禁
- Next handoff: 后端机在下一次后端功能前检查 `main.py`、router、service/assembler 边界
- [ ] TODO: Owner `backend machine` — 保持 `main.py` 只负责 app 装配，禁止复杂业务逻辑回流。

### Offline-First Login and App Cache

- Owner: frontend machine after user approval
- Current status: `Needs Decision`
- Spec: `docs/superpowers/specs/2026-06-29-offline-first-login-cache-design.md`
- Frontend plan: `docs/superpowers/plans/2026-06-29-offline-first-login-cache.md`
- Backend plan: `N/A`，当前范围不新增离线写队列或后端接口
- Contract: 复用现有契约；若发现缺口，先交给后端机处理
- Integration: 获批后需建立新的聚焦联调计划
- Gitee baseline SHA: TODO — 获批时填写
- GitHub mirror: TODO — 网络恢复后补推
- Blockers: 用户尚未选择其为下一阶段
- Next handoff: 用户批准后由前端机重新核对 Expo 56 和当前缓存实现，再拆出聚焦计划
- [ ] TODO: Owner `user` — 决定是否将离线优先登录缓存作为下一前端切片。

## Integration Gate

- Current gate status: `N/A — documentation-only`
- Backend baseline SHA: `N/A`
- Frontend baseline SHA: `N/A`
- Contract status: unchanged
- Automated verification: passed — `git diff --check`
- Manual verification: exempt; no runtime behavior changed
- Next-stage admission: Pending user selection

## Blocked

- [x] TODO: Owner `repository maintainers` — 本次治理提交已同步 Gitee 与 GitHub；后续若 `github.com:443` 再次超时，按双远端规则新增当次补推 TODO。

## Next Slice Creation Rules

下一功能获批后，必须在同一变更集中：

1. 在本看板新增切片及 Owner。
2. 锁定阶段规格。
3. 如涉及接口，先建立 backend 计划并更新契约。
4. 契约 `Contract Ready` 后再建立 frontend 计划。
5. 两端本机验证完成后建立 integration 计划。
6. 联调通过后更新 Gitee SHA、GitHub 状态和 Next handoff。
