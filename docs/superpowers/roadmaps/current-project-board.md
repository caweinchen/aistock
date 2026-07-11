# Current Project Board

本看板用于两台电脑同步项目推进状态。所有未完成事项必须使用显式 TODO。

## Current Checkpoint

- Updated: 2026-07-11
- Current phase: waiting for next frontend task or backend integration handoff
- Completed: shared research panel, global header navigation checks, frontend verification, health integration check, core API contracts, and stock analysis service extraction
- Next: frontend machine当前无待执行 TODO；等待后端接口变更或新增前端规格/计划
- Blockers: none
- Frontend baseline: `b604cb2 feat: add shared research panel`
- Backend baseline: `8ca69e7 docs: define core api contracts`
- Verification baseline: 10 frontend test files / 29 tests passed; TypeScript passed; global header and detail i18n scripts passed; Metro Web bundle returned 200; `GET /api/health` returned HTTP 200 with `status=healthy`
- Key decision: 本机继续只承担前端开发和联调配置；后端 service/assembler 后续分解保留给后端机

## In Progress

- [x] TODO: 补齐核心 API 契约文档
  - Owner: backend machine
  - Location: `docs/contracts/`
  - Status: done
  - Note: 已补齐 auth、stocks、watchlist、backtests 四个核心域；后续接口变更按域同步维护。

- [x] TODO: 后端 health 联调环境复核
  - Owner: frontend machine
  - Related plan: `docs/superpowers/plans/2026-06-23-global-header-search-navigation.md`
  - Status: completed
  - Verification: 2026-07-11 启动本机用户态 MySQL 和后端联调服务后，`GET http://127.0.0.1:8010/api/health` 返回 HTTP 200 和 `status=healthy`；未修改后端代码。

## Ready For Frontend

- [x] TODO: 普通用户前后端联调
  - Owner: frontend machine
  - Plan: `docs/superpowers/plans/2026-07-11-ordinary-user-frontend-integration.md`
  - Status: completed
  - Verification: frontend tests passed, TypeScript check passed, local browser integration verified.

## Ready For Backend

- [ ] TODO: 后端 `main.py` 后续 service/assembler 分解
  - Owner: backend machine
  - Spec: `docs/superpowers/specs/2026-07-10-backend-main-decomposition-design.md`
  - Status: pending
  - Note: 前端电脑不得修改后端实现；如前端联调发现接口缺口，只记录问题并交给后端电脑。

## Blocked

- [ ] TODO: 当前无阻塞项

## Done

- [x] TODO: 全局头部搜索导航前端验证修复
  - Owner: frontend machine
  - Plan: `docs/superpowers/plans/2026-06-23-global-header-search-navigation.md`
  - Status: completed
  - Verification: global header script passed, i18n script passed, frontend tests passed, TypeScript check passed, Metro Web bundle passed, backend health integration check passed.

- [x] TODO: 建立两机协作规约
  - Protocol: `docs/TWO_MACHINE_COLLABORATION_PROTOCOL.md`
  - Frontend role: `docs/agents/frontend-machine.md`
  - Backend role: `docs/agents/backend-machine.md`

- [x] TODO: 后端启动脚本本地联调改进已推送
  - File: `start_backend.bat`
  - Status: pushed to `main`
