# AIStock Mobile

AIStock Mobile 是一个基于 Expo + React Native 的跨平台股票分析 App 原型，同一套代码可用于 Android、iOS 和 Web 预览。

## 当前版本

当前实现的是研究型 MVP 首页，包含：

- 市场温度、预警数量、策略胜率概览
- 自选股评分列表
- 个股因子雷达入口
- 策略回测摘要
- 投资风险提示

界面中的行情和评分是模拟数据，方便先验证产品体验。接入真实行情前，不应把这些数据用于投资决策。

## 推荐技术路线

- 移动端：Expo + React Native + TypeScript
- 数据源：TuShare Pro 或自建数据服务
- 本地缓存：SQLite / MMKV
- 服务端：Python FastAPI
- 数据存储：DuckDB / PostgreSQL
- 回测引擎：Backtrader 起步，复杂场景再评估 Lean
- AI 能力：先做研报摘要、风险解释、因子归因，不直接承诺涨跌预测

## 运行

```bash
npm install
npm run start
```

常用平台命令：

```bash
npm run android
npm run ios
npm run web
```

说明：iOS 原生构建需要 macOS 和 Xcode。在 Windows 上可以用 Expo Go 预览，或使用 EAS Build 云端打包。

## 后端接口

项目已包含一个 FastAPI 后端原型：

```bash
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

核心接口：

- `GET /api/stocks`：返回自选股列表
- `GET /api/stocks/search?q=keyword`：按股票代码或名称搜索
- `GET /api/watchlist`：返回自选股列表
- `POST /api/watchlist/{code}`：加入自选股
- `DELETE /api/watchlist/{code}`：移出自选股
- `GET /api/stocks/{code}`：返回选中股票的详情、因子、策略、预警和 AI 摘要
- `GET /api/stocks/{code}/factors`：返回因子评分
- `GET /api/stocks/{code}/strategies`：返回策略回测摘要
- `GET /api/stocks/{code}/strategies/{strategy_id}`：返回单个策略的规则、指标和交易明细
- `GET /api/stocks/{code}/alerts`：返回风险提示
- `GET /api/stocks/{code}/history`：返回价格走势数据

移动端当前会自动连接：

- Web / iOS 模拟器：`http://127.0.0.1:8000`
- Android 模拟器：`http://10.0.2.2:8000`

如果用真实手机预览，需要把 `App.tsx` 里的 `API_BASE_URL` 改成本机局域网 IP，例如 `http://192.168.1.10:8000`。
同时后端需要这样启动，允许局域网设备访问：

```bash
.\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
```

## 下一步

1. 抽出 `src/` 目录，拆分页面、组件和数据服务。
2. 增加自选股搜索、详情页和回测详情页。
3. 建立后端 API，统一封装行情、财务、策略回测和 AI 解释。
4. 加入登录、数据缓存、错误状态和免责声明。
5. 准备应用商店上架所需的隐私政策和合规文案。
