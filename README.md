# AIStock Mobile

AIStock Mobile 是一个基于 Expo + React Native 的跨平台股票分析 App 原型，同一套代码可用于 Android、iOS 和 Web 预览。

## 当前版本

当前实现的是一个完整的股票分析 MVP，包含以下功能：

### ✅ 已完成功能

**前端功能：**
- ✅ 市场温度、预警数量、策略胜率概览
- ✅ 自选股评分列表（支持搜索）
- ✅ 个股详情页（因子雷达、策略回测、风险提示）
- ✅ 用户登录/注册系统
- ✅ 个人中心（修改密码、语言设置）
- ✅ 多语言支持（简体中文、繁体中文、English）
- ✅ 服务器配置页面（可配置后端地址）

**后端功能：**
- ✅ FastAPI 后端服务
- ✅ MySQL 数据库持久化存储
- ✅ 用户认证系统（PBKDF2 密码加密）
- ✅ 股票数据查询和搜索
- ✅ 因子评分、策略回测、风险预警接口
- ✅ 价格历史数据接口

**技术架构：**
- ✅ 前端：Expo + React Native + TypeScript
- ✅ 后端：Python FastAPI + SQLAlchemy
- ✅ 数据库：MySQL（支持 SQLite 切换）
- ✅ 密码安全：PBKDF2 加密

界面中的行情和评分是模拟数据，方便先验证产品体验。接入真实行情前，不应把这些数据用于投资决策。

## 技术栈

| 层级 | 技术 |
|------|------|
| 移动端 | Expo + React Native + TypeScript |
| 服务端 | Python FastAPI + SQLAlchemy |
| 数据库 | MySQL / SQLite |
| 数据源 | TuShare Pro（待接入）或自建数据服务 |

## 快速开始

### 前端启动

```bash
npm install
npm run web
```

### 后端启动

```bash
# 激活虚拟环境
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt

# 启动服务
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

### 部署配置

后端配置文件位于 `backend/.env.example`，复制并修改：

```bash
cd backend
copy .env.example .env
# 编辑 .env 修改数据库连接信息
```

## API 接口

### 认证接口
- `POST /api/auth/login` - 用户登录
- `POST /api/auth/change-password` - 修改密码
- `POST /api/auth/validate-password` - 验证密码强度
- `GET /api/auth/generate-password` - 生成随机强密码

### 股票接口
- `GET /api/stocks` - 返回自选股列表
- `GET /api/stocks/search?q=keyword` - 按股票代码或名称搜索
- `GET /api/stocks/{code}` - 返回选中股票的详情
- `GET /api/stocks/{code}/factors` - 返回因子评分
- `GET /api/stocks/{code}/strategies` - 返回策略回测摘要
- `GET /api/stocks/{code}/strategies/{strategy_id}` - 返回单个策略详情
- `GET /api/stocks/{code}/alerts` - 返回风险提示
- `GET /api/stocks/{code}/history` - 返回价格走势数据

### 自选股接口
- `GET /api/watchlist` - 返回自选股列表
- `POST /api/watchlist/{code}` - 加入自选股
- `DELETE /api/watchlist/{code}` - 移出自选股

### 其他接口
- `GET /api/health` - 健康检查
- `POST /api/backtests` - 创建自定义回测

## 测试账号

| 用户名 | 密码 |
|--------|------|
| admin | Test@bcd!234 |

## 下一步

### 核心功能
- [x] 接入真实行情数据（TuShare Pro）
- [ ] 个股详情页完整回测功能
- [ ] 自定义策略回测构建器

### 用户体验
- [ ] 投资组合管理
- [ ] 消息推送通知
- [ ] 离线数据缓存

### 合规与上架
- [ ] 完善免责声明
- [ ] 应用商店上架材料准备
- [ ] 用户协议完善

## 项目结构

```
AIStock-new/
├── src/
│   ├── pages/          # 页面组件
│   │   ├── HomeScreen.tsx
│   │   ├── LoginScreen.tsx
│   │   ├── ProfileScreen.tsx
│   │   └── SettingsScreen.tsx
│   ├── components/     # 可复用组件
│   ├── hooks/          # React Hooks
│   ├── services/        # API 服务
│   ├── i18n/           # 多语言配置
│   └── utils/           # 工具函数
├── backend/
│   ├── app/
│   │   ├── main.py     # FastAPI 入口
│   │   ├── config.py    # 配置文件
│   │   ├── database.py  # 数据库模型
│   │   └── security.py  # 安全认证
│   └── requirements.txt
└── ...
```

## 法律声明

本应用仅供参考和学习研究使用，不构成任何投资建议。股票投资有风险，入市需谨慎。

详细法律条款请参阅：
- [隐私政策](./PRIVACY.md)
- [服务条款](./TERMS.md)
