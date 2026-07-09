# 后端 main.py 结构控制设计

## 1. 背景

`backend/app/main.py` 已增长到约 2280 行，包含 API 应用初始化、Pydantic schema、认证、股票查询、股票详情、数据刷新、自选股、回测、管理员用户和数据源状态等多类职责。

继续把新能力写入 `main.py` 会带来三个问题：

- 单文件上下文过大，后续修改容易误伤无关逻辑。
- schema、路由和业务装配混在一起，测试与复用成本升高。
- 第二阶段后续还会继续增加自选股、会员预留、组合风险和报告能力，必须先控制入口文件规模。

## 2. 目标

长期目标：

- `main.py` 只负责 FastAPI app 创建、middleware、startup 和 router 注册。
- schema、router、service/assembler 分层清晰。
- 每轮拆分都保持 API 行为兼容和测试通过。
- 所有拆分文档使用 `TODO` 跟踪，完成后同步标记。

第一轮目标：

- 新增 `backend/app/schemas.py`，迁出 Pydantic schema 和共享 `Literal` 类型。
- 新增 `backend/app/routers/auth.py`，迁出认证相关路由。
- 新增 `backend/app/routers/watchlist.py`，迁出自选股和 watchlist intelligence 路由。
- `main.py` 通过 `include_router(...)` 注册新 router。
- 第一轮完成后 `main.py` 行数明显下降，并且不再继续承载新自选股能力。

## 3. 非目标

第一轮不做：

- 不重写数据库模型。
- 不修改 API 路径、响应字段或认证行为。
- 不拆股票详情、数据刷新、回测和管理员模块。
- 不改变前端调用方式。
- 不做大规模服务层重构。

这些内容进入后续 TODO。

## 4. 结构设计

第一轮文件结构：

```text
backend/app/main.py
backend/app/schemas.py
backend/app/routers/__init__.py
backend/app/routers/auth.py
backend/app/routers/watchlist.py
```

职责边界：

- `schemas.py`
  - 保存 API schema、请求/响应模型和共享 `Literal` 类型。
  - 不访问数据库。
  - 不包含路由函数。

- `routers/auth.py`
  - 保存 `/api/auth/*` 路由。
  - 依赖 `get_db`、安全工具、schema 和当前用户依赖。
  - 不处理股票、自选股或回测逻辑。

- `routers/watchlist.py`
  - 保存 `/api/watchlist`、`/api/watchlist/insights`、新增/删除自选股路由。
  - 复用 watchlist intelligence 和 ordinary user 规则。
  - 不处理个股详情页面完整装配。

- `main.py`
  - 保留 app 初始化、CORS、startup、健康检查和暂未拆分的旧路由。
  - 注册 `auth_router` 和 `watchlist_router`。

## 5. 迁移策略

采用渐进式拆分：

1. 先搬 schema，保证 imports 统一。
2. 再搬 auth router，因为认证相对独立。
3. 再搬 watchlist router，因为这是阶段 2 核心且后续会继续增长。
4. 每一步都运行对应测试。
5. 每一步都独立提交。

不允许一次性搬空 `main.py`。

## 6. API 兼容要求

第一轮拆分后，下列路径必须保持兼容：

- `GET /api/auth/public-key`
- `POST /api/auth/login`
- `POST /api/auth/register`
- `POST /api/auth/change-password`
- `POST /api/auth/validate-password`
- `GET /api/auth/verify`
- `GET /api/auth/generate-password`
- `GET /api/watchlist`
- `GET /api/watchlist/insights`
- `POST /api/watchlist/{code}`
- `DELETE /api/watchlist/{code}`

响应字段不得减少，认证要求不得放宽。

## 7. 测试策略

后端验证：

- 先跑认证和自选股相关测试。
- 再跑完整后端测试。
- 因 `test_auth_encryption.py` 依赖本地 8000 服务，完整后端测试前需要启动临时后端服务，测试后关闭。

命令：

```powershell
python -m pytest backend/tests/test_user_admin_and_watchlist.py -q
python -m pytest backend/tests/test_auth_encryption.py -q
python -m pytest backend/tests -q
```

结构验证：

- `main.py` 行数应减少。
- `main.py` 不再定义第一轮迁出的 schema。
- `main.py` 不再直接定义 auth/watchlist 路由。

## 8. TODO 跟踪

- [ ] 第一轮：拆出 `schemas.py`、`routers/auth.py`、`routers/watchlist.py`
- [ ] 第二轮：拆出股票详情和股票数据查询 router
- [ ] 第三轮：拆出数据刷新和数据源状态 router
- [ ] 第四轮：拆出 backtest router
- [ ] 第五轮：拆出 admin router
- [ ] 第六轮：将复杂装配逻辑迁移到 service/assembler 层
- [ ] 长期：`main.py` 控制在 app 装配文件规模，不再承载业务路由新增

## 9. 验收标准

第一轮完成时：

- `main.py` 行数明显下降。
- `schemas.py` 成为 API schema 的统一入口。
- auth 和 watchlist 路由位于独立 router 文件。
- 阶段 2 watchlist intelligence 行为保持不变。
- 后端测试通过。
- 本设计文档和对应实施计划同步标记已完成项。

