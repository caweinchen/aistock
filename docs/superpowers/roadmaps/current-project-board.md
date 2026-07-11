# Current Project Board

本看板用于两台电脑同步项目推进状态。所有未完成事项必须使用显式 TODO。

## In Progress

- [ ] TODO: 补齐核心 API 契约文档
  - Owner: backend machine
  - Location: `docs/contracts/`
  - Status: pending
  - Note: 现有前端联调已完成，但历史接口契约目录刚建立，后端电脑应在下一轮后端任务中补齐或按接口变更逐步补齐。

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

- [x] TODO: 建立两机协作规约
  - Protocol: `docs/TWO_MACHINE_COLLABORATION_PROTOCOL.md`
  - Frontend role: `docs/agents/frontend-machine.md`
  - Backend role: `docs/agents/backend-machine.md`

- [x] TODO: 后端启动脚本本地联调改进已推送
  - File: `start_backend.bat`
  - Status: pushed to `main`
