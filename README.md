# AIStock Mobile

AIStock Mobile 是一个基于 Expo、React Native 和 FastAPI 的股票分析应用。项目包含移动端/网页前端、Python 后端、MySQL 数据库、用户认证、自选股、个股详情、策略回测、离线登录和本地缓存能力。

本项目用于学习、研究和产品原型验证，不构成任何投资建议。

## 当前功能

### 前端

- 登录、注册、退出登录和离线登录
- 管理员用户管理，包括启用/禁用用户和角色管理
- 自选股列表、搜索、添加和移除自选股
- 个股详情页，包括行情、因子评分、策略回测、风险提示、新闻、分红和机构持仓
- 自定义回测构建器
- 首页全局搜索、刷新和连接状态提示
- 简体中文、繁体中文和英文多语言
- 服务地址配置页，支持 Web、Android 模拟器和本机后端切换
- 本地缓存，支持后端不可用时读取已缓存数据

### 后端

- FastAPI API 服务
- SQLAlchemy 数据模型
- MySQL 持久化，配置上支持 SQLite
- PBKDF2 密码哈希
- RSA 公钥接口，支持前端加密传输密码
- token 会话认证
- 用户注册、登录、改密、认证校验和管理员用户管理
- 自选股、个股详情、价格历史、因子、策略、风险提示和回测接口
- TuShare / EastMoney 数据服务状态和刷新接口

## 技术栈

| 层级 | 技术 |
| --- | --- |
| 前端 | Expo 56、React Native、TypeScript、Vitest |
| 后端 | Python、FastAPI、SQLAlchemy、unittest |
| 数据库 | MySQL，支持 SQLite 配置 |
| 存储 | Web localStorage、Native AsyncStorage |
| 数据源 | TuShare / EastMoney / 本地数据库 |

## 项目结构

```text
AIStock-new/
├─ frontend/
│  ├─ App.tsx
│  ├─ src/
│  │  ├─ components/
│  │  ├─ hooks/
│  │  ├─ i18n/
│  │  ├─ pages/
│  │  ├─ services/
│  │  ├─ types/
│  │  └─ utils/
│  └─ package.json
├─ backend/
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ database.py
│  │  ├─ config.py
│  │  ├─ security.py
│  │  ├─ rsa_utils.py
│  │  └─ tushare_service.py
│  ├─ tests/
│  └─ requirements.txt
├─ db/
├─ docs/
├─ start_backend.bat
└─ README.md
```

## 环境要求

- Node.js 和 npm
- Python 3.11+，当前开发环境使用 Python 3.14
- MySQL 8.x
- Expo / React Native 开发环境
- Android 模拟器可选

如果只是想快速部署一套可运行系统，请优先阅读：

- [Windows 简易部署指南](./docs/DEPLOY_SIMPLE.md)
- [Docker 本机部署测试指南](./docs/DEPLOY_DOCKER.md)

## 后端配置

后端读取 `backend/.env` 或项目根目录 `.env`。常用配置如下：

```env
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USERNAME=aistock
DB_PASSWORD=AI@stock!234
DB_NAME=ai_stock
DB_DIALECT=mysql
DB_DRIVER=mysqlconnector

APP_HOST=0.0.0.0
APP_PORT=8000

TUSHARE_ENABLED=true
TUSHARE_TOKEN=your_token
```

默认后端地址是：

```text
http://127.0.0.1:8000
```

移动端或模拟器访问后端时，应在前端服务配置页填写真实后端服务器 IP：

```text
<后端服务器IP>:8000
```

`10.0.2.2:8000` 只适用于 Android 模拟器访问同一台开发电脑上的本地后端，不适用于真机或独立部署环境。

## 启动后端

在项目根目录执行：

```powershell
python -m pip install -r backend\requirements.txt
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

或使用项目脚本：

```powershell
.\start_backend.bat
```

健康检查：

```powershell
Invoke-WebRequest http://127.0.0.1:8000/api/health -UseBasicParsing
```

## 启动前端

```powershell
cd frontend
npm install
npm run web
```

常用脚本：

```powershell
npm run web      # Web 预览
npm run android  # Android
npm run ios      # iOS
npm test -- --run
```

## 测试账号

| 用户名 | 密码 | 角色 |
| --- | --- | --- |
| admin | Test@bcd!234 | admin |
| Test | Test@bcd!234 | user |
| demo | Demo@123! | user |
| user | User@456! | user |

注册的新用户默认未启用，需要管理员在用户管理页启用后才能登录。

## 离线登录和缓存

项目包含两类本地数据：

- **离线登录凭据**：在线登录成功后保存本地密码哈希。后端不可用时，前端会用本地哈希校验用户名和密码，校验通过后生成 `offline_` token。
- **业务数据缓存**：股票列表、搜索结果、个股详情、策略详情、分红、新闻、机构持仓等数据会按用户命名空间写入本地存储。

行为说明：

- 在线登录成功后会保存离线登录凭据。
- 首页在线加载且本地无股票缓存时，会主动拉取股票列表并写入缓存。
- 手动刷新自选股会刷新股票列表，并尽量缓存对应个股的详情数据。
- 后端断开、超时、网络失败或返回 5xx 时，登录会尝试离线回退。
- 401/403 不会走离线回退，避免密码错误或账号禁用时绕过后端。
- 退出登录会清除在线 token，但保留离线登录所需的密码哈希。

## API 摘要

### 认证

- `GET /api/auth/public-key`
- `POST /api/auth/login`
- `POST /api/auth/register`
- `POST /api/auth/change-password`
- `POST /api/auth/validate-password`
- `GET /api/auth/verify`
- `GET /api/auth/generate-password`

### 管理员

- `GET /api/admin/users`
- `PATCH /api/admin/users/{user_id}`

### 股票和自选股

- `GET /api/stocks`
- `GET /api/stocks/refresh-all`
- `GET /api/stocks/search?q=keyword`
- `GET /api/stocks/{code}`
- `GET /api/stocks/{code}/refresh`
- `GET /api/stocks/{code}/history`
- `GET /api/stocks/{code}/realtime`
- `GET /api/stocks/{code}/factors`
- `GET /api/stocks/{code}/alerts`
- `GET /api/stocks/{code}/strategies`
- `GET /api/stocks/{code}/strategies/{strategy_id}`
- `GET /api/stocks/{code}/dividend`
- `GET /api/stocks/{code}/news`
- `GET /api/stocks/{code}/adj-factor`
- `GET /api/stocks/{code}/inst-hold`
- `GET /api/watchlist`
- `POST /api/watchlist/{code}`
- `DELETE /api/watchlist/{code}`

### 回测和数据源

- `POST /api/backtests`
- `GET /api/tushare/status`
- `GET /api/eastmoney/status`
- `GET /api/eastmoney/refresh/{code}`

### 系统

- `GET /api/health`

## 测试

前端：

```powershell
cd frontend
npm test -- --run
```

后端：

```powershell
$env:PYTHONPATH='backend'
python -m unittest discover -s backend/tests
```

注意：部分后端加密接口测试会请求 `localhost:8000`，运行完整后端测试前需要先启动后端服务。

## 常见问题

### Web 能登录，移动端不能登录

移动端里的 `127.0.0.1` 指向设备自身，不是后端服务器。请在前端设置页把服务器地址改成真实后端 IP：

```text
<后端服务器IP>:8000
```

如果只是 Android 模拟器访问同一台开发电脑上的本地后端，可以使用 `10.0.2.2:8000`。

### 后端关闭后不能离线登录

请确认这个账号至少成功在线登录过一次。只有在线登录成功后，本地才会保存离线登录密码哈希。仅刷新股票数据不会生成离线登录凭据。

### 有缓存但仍然登录失败

股票缓存和离线登录凭据是两套数据。股票缓存只能用于进入系统后展示数据，登录页是否放行取决于本地密码哈希是否存在且匹配。

### 后端测试连接失败

如果 `test_auth_encryption.py` 报 `ConnectionRefusedError`，说明 `localhost:8000` 后端服务没有启动。先启动后端再运行完整测试。

## 法律声明

本项目仅用于学习、研究和产品原型验证，不提供任何投资建议。股票投资有风险，入市需谨慎。项目中的分析结果、评分、策略和行情数据不保证准确性、完整性和实时性，不应作为投资决策的唯一依据。

详细法律条款请参阅：

- [隐私政策](./PRIVACY.md)
- [服务条款](./TERMS.md)
