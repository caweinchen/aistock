# Current Project Board

本看板用于两台电脑同步项目推进状态。所有未完成事项必须使用显式 TODO。

## In Progress

- [x] TODO: 补齐核心 API 契约文档
  - Owner: backend machine
  - Location: `docs/contracts/`
  - Status: done
  - Note: 已补齐 auth、stocks、watchlist、backtests 四个核心域；后续接口变更按域同步维护。

- [ ] TODO: 后端 health 联调环境复核
  - Owner: frontend machine
  - Related plan: `docs/superpowers/plans/2026-06-23-global-header-search-navigation.md`
  - Status: pending
  - Note: 前端脚本、测试、类型检查和 Web bundle 已通过；本机 `127.0.0.1:8010` 后端服务当前未连接，后续联调时复核 `/api/health`。

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
  - Status: completed except backend health environment check
  - Verification: global header script passed, i18n script passed, frontend tests passed, TypeScript check passed, Metro Web bundle passed.

- [x] TODO: 建立两机协作规约
  - Protocol: `docs/TWO_MACHINE_COLLABORATION_PROTOCOL.md`
  - Frontend role: `docs/agents/frontend-machine.md`
  - Backend role: `docs/agents/backend-machine.md`

- [x] TODO: 后端启动脚本本地联调改进已推送
  - File: `start_backend.bat`
  - Status: pushed to `main`
