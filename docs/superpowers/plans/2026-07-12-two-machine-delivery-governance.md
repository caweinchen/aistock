# AIStock Two-Machine Delivery Governance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 AIStock 当前文档整理成前端电脑、后端电脑和联调门禁可独立执行与交接的工作体系。

**Architecture:** 规格负责跨端目标与边界；后端计划先产出实现、测试和契约；前端计划只消费已冻结契约；联调计划基于同一 Gitee `main` 完成真实接口验收。当前项目看板是唯一任务入口，历史计划仅作为证据。

**Tech Stack:** Markdown、Git、Gitee、GitHub、Multica

## Global Constraints

- 不修改前端或后端业务代码。
- Gitee `main` 是主协作基准，GitHub 是辅助镜像。
- 未完成工作必须使用显式 TODO、Owner 和验收条件。
- 不将历史计划中的陈旧复选框直接视为当前任务。

---

### Task 1: 落地协作门禁与角色职责

**Files:**
- Modify: `docs/TWO_MACHINE_COLLABORATION_PROTOCOL.md`
- Modify: `docs/agents/backend-machine.md`
- Modify: `docs/agents/frontend-machine.md`
- Modify: `docs/superpowers/specs/2026-07-11-stage-integration-gate-design.md`

- [x] **Step 1:** 将状态流转和联调通过条件写入两机协议。
- [x] **Step 2:** 在后端角色中加入契约交接包和联调职责。
- [x] **Step 3:** 在前端角色中加入契约消费和真实接口联调职责。
- [x] **Step 4:** 更新阶段门禁设计 TODO。

### Task 2: 重构当前项目看板

**Files:**
- Modify: `docs/superpowers/roadmaps/current-project-board.md`
- Modify: `docs/superpowers/plans/2026-06-29-offline-first-login-cache.md`

- [x] **Step 1:** 记录当前已完成基线和文档审计日期。
- [x] **Step 2:** 将后端长期结构控制列为 backend owner 主线。
- [x] **Step 3:** 将离线优先登录缓存列为 `Needs Decision` 前端候选。
- [x] **Step 4:** 增加门禁字段、Gitee SHA、GitHub TODO 和 Next handoff。
- [x] **Step 5:** 在离线计划顶部标明未获当前阶段批准，不得自动执行。

### Task 3: 验证、提交和同步

**Files:**
- Modify: `docs/superpowers/specs/2026-07-12-two-machine-delivery-governance-design.md`
- Modify: `docs/superpowers/plans/2026-07-12-two-machine-delivery-governance.md`

- [x] **Step 1:** 运行 `git diff --check`。
- [x] **Step 2:** 检查所有当前 TODO 都具有 Owner 或决策条件。
- [x] **Step 3:** 删除非 AIStock 游戏规格和计划。
- [x] **Step 4:** 更新本规格和计划 TODO 状态。
- [x] **Step 5:** 提交文档变更并先推送 Gitee `main`。
- [x] **Step 6:** 同步 GitHub `main`；Gitee 与 GitHub 均验证到 `be2de5202db56bf6583a17c41f938ff1c3915597`。
