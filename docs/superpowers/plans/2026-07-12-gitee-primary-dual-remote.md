# Gitee Primary Dual-Remote Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Gitee 固化为项目主远端、GitHub 固化为辅助镜像，并要求每次提交按顺序同步两个远端。

**Architecture:** 根目录 `AGENTS.md` 保存所有 Codex 会话必须读取的长期规则；`docs/TWO_MACHINE_COLLABORATION_PROTOCOL.md` 保存两台开发电脑共同遵守的操作细则和完成定义。远端名称固定为 `gitee` 与 `origin`，本地 `main` 跟踪 `gitee/main`。

**Tech Stack:** Git、Gitee、GitHub、Markdown、PowerShell

## Global Constraints

- Gitee 是主远端，固定名称为 `gitee`。
- GitHub 是辅助镜像远端，固定名称为 `origin`。
- 每次提交先推送 `gitee/main`，再推送 `origin/main`。
- Gitee 推送失败时不得标记为已同步。
- GitHub 因网络失败时必须明确报告、保留 TODO，并在网络恢复后补推。
- 未经用户针对具体分支明确授权，禁止强制推送。
- 不修改业务代码。

---

### Task 1: 固化并启用双远端协作规则

**Files:**
- Modify: `AGENTS.md`
- Modify: `docs/TWO_MACHINE_COLLABORATION_PROTOCOL.md`
- Modify: `docs/superpowers/plans/2026-07-12-gitee-primary-dual-remote.md`

**Interfaces:**
- Consumes: Git 远端 `gitee` 和 `origin`，分支 `main`。
- Produces: 后续所有 agent 和两台开发电脑共同遵守的拉取、推送、失败处理与完成定义。

**Multica enforcement:**

- [x] 前后端 agent instructions 已写入 Gitee 优先、双远端顺序、GitHub 失败 TODO 和禁止强推规则。
- [x] Workspace 仓库登记已移除重复 GitHub 项目资源，只保留 `https://gitee.com/caweinhen/aistock.git`。

- [x] **Step 1: 更新根目录长期指令**

在 `AGENTS.md` 添加 `# Git Remotes`，明确远端角色、推送顺序、失败处理、禁止强推和 `main` 跟踪规则。

- [x] **Step 2: 更新两机协作协议**

在 `docs/TWO_MACHINE_COLLABORATION_PROTOCOL.md` 添加“双远端同步规则”，并把角色完成条件和整体完成定义中的笼统“推送到远端”改为 Gitee 主远端必须成功、GitHub 辅助远端同步或记录 TODO。

- [x] **Step 3: 验证文档一致性**

运行：

```powershell
git diff --check
rg -n "gitee|origin|GitHub|Gitee|强制推送|TODO" AGENTS.md docs/TWO_MACHINE_COLLABORATION_PROTOCOL.md
```

预期：`git diff --check` 退出码为 `0`；两份文档明确包含相同的远端名称、顺序和失败语义。

- [x] **Step 4: 更新计划 TODO 并提交**

将本计划已完成步骤标为 `[x]`，然后运行：

```powershell
git add AGENTS.md docs/TWO_MACHINE_COLLABORATION_PROTOCOL.md docs/superpowers/plans/2026-07-12-gitee-primary-dual-remote.md
git commit -m "docs: make Gitee the primary remote"
```

预期：提交只包含上述三份文档。

- [x] **Step 5: 按新规则同步远端**

运行：

```powershell
git push gitee main
git push origin main
```

预期：Gitee 推送必须成功；GitHub 推送成功则完成双端同步，因网络失败则在本计划新增明确 TODO，记录失败原因和待补推动作。

Verification: 2026-07-12，Gitee `main` 与 GitHub `origin/main` 均同步到 `be2de5202db56bf6583a17c41f938ff1c3915597`。
