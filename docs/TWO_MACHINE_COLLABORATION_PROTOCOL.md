# Two-Machine Collaboration Protocol

本规约用于约束两台开发电脑在同一项目中的推进方式。两台电脑都必须按本文执行，除非用户明确临时授权偏离。

## 角色边界

两台电脑必须使用各自的本机角色模板：

- 前端电脑：`docs/agents/frontend-machine.md`
- 后端电脑：`docs/agents/backend-machine.md`

### 前端电脑

- 只开发前端代码、前端测试、前端构建脚本、前后端联调配置。
- 不得修改后端代码，除非用户明确授权。
- 可以启动或配置本地后端服务用于联调，但这不等同于承担后端功能开发。
- 前端本地验证无误后，提交并推送到远端 `main` 分支，准备合并后端联调。

### 后端电脑

- 只开发后端代码、数据库迁移、后端测试、接口契约文档。
- 不得修改前端代码，除非用户明确授权。
- 修改接口、鉴权、错误码、响应字段或数据语义时，必须同步更新接口契约文档。
- 后端本地验证无误后，提交并推送到远端 `main` 分支，准备前端接入或联调。

## 标准推进流程

每个功能都按以下顺序推进：

1. 规格书
2. 后端计划
3. 后端实现和后端测试
4. 接口契约
5. 前端计划
6. 前端实现和前端测试
7. 联调计划
8. 联调验证
9. 文档 TODO 状态更新
10. 提交并推送 `main`

如果某一步暂时无法完成，必须在对应文档中保留明确 TODO，并写清阻塞原因或后续动作。

## 文档结构

机器角色模板放在：

```text
docs/agents/
```

规格书放在：

```text
docs/superpowers/specs/
```

计划放在：

```text
docs/superpowers/plans/
```

接口契约放在：

```text
docs/contracts/
```

项目推进总看板放在：

```text
docs/superpowers/roadmaps/current-project-board.md
```

当目录不存在时，由需要使用该目录的任务创建。

## 文档要求

所有规格书、计划、路线图和看板必须使用显式 TODO 跟踪未完成工作。

示例：

```md
## TODO Tracking

- [ ] Spec locked
- [ ] Backend API implemented
- [ ] Backend tests passed
- [ ] API contract documented
- [ ] Frontend integration implemented
- [ ] Frontend tests passed
- [ ] Local joint verification passed
- [ ] Merged to main
```

完成任务、阶段或子切片时，必须在同一变更集中更新对应文档，将 TODO 标为完成或部分完成。

大型功能必须拆成多份聚焦文档，避免单个规格或计划过大。

## 接口契约要求

后端新增或变更接口时，必须维护对应契约文档。契约至少包含：

- Method and path
- Auth requirement
- Request params or body
- Response body
- Error cases
- Example JSON
- Compatibility notes

前端接入接口时，以契约文档为准。如果契约和实际接口不一致，先记录问题并推动契约或后端修正，不靠猜测继续扩大实现。

## 分支和提交

默认分支为：

```text
main
```

推荐短分支命名：

```text
backend/feature-name
frontend/feature-name
integration/feature-name
```

如果直接在 `main` 工作，开始前必须确认本地基于最新远端状态；结束时必须在验证通过后提交并推送。

每次提交应只包含同一职责范围内的变更：

- 前端提交不夹带后端实现。
- 后端提交不夹带前端实现。
- 规格、计划、契约、看板更新应随对应功能变更一起提交。

## 完成定义

### 规格完成

- 功能目标清楚。
- 用户路径清楚。
- 数据、接口或本地状态边界清楚。
- TODO 已写入计划或看板。

### 后端完成

- 接口或后端能力已实现。
- 后端测试通过。
- 接口契约已更新。
- 没有未经授权的前端改动。
- 已提交并推送到 `main`。

### 前端完成

- 页面、状态、交互或服务接入已实现。
- 前端测试或必要构建验证通过。
- 没有未经授权的后端改动。
- 相关计划 TODO 已更新。
- 已提交并推送到 `main`。

### 联调完成

- 后端服务可启动。
- 前端可访问真实接口。
- 关键路径已手工验证。
- 相关规格、计划、契约或看板 TODO 已更新。
- 已提交并推送到 `main`。

## 冲突处理

- 发现另一台电脑的未合并工作时，不得擅自回滚。
- 发现职责范围外的改动时，先保留并说明，不自行重写。
- 如果当前任务必须跨越职责边界，先获得用户明确授权。
- 如果接口契约、规格和代码不一致，以规格和契约为讨论依据，修正后再继续开发。
