# AIStock 简易部署指南（Windows）

这份文档面向想用本项目搭建一套可运行系统的用户。默认部署目标是 Windows 服务器或 Windows 电脑，后端端口为 `8000`，前端使用 Expo Web/移动端访问后端。

## 需要提前准备

- 一台 Windows 电脑或服务器
- Python 3.11 或更高版本
- Node.js LTS 和 npm
- MySQL 8.x
- 项目代码
- MySQL 数据库连接信息
- 可选：TuShare token
- 可选：真实域名和 HTTPS 证书

## 需要确认的信息

| 项目 | 示例 |
| --- | --- |
| 后端服务器 IP | `192.168.1.20` 或公网 IP |
| 后端端口 | `8000` |
| MySQL 主机 | `127.0.0.1` |
| MySQL 端口 | `3306` |
| MySQL 数据库名 | `ai_stock` |
| MySQL 用户名 | `aistock` |
| MySQL 密码 | 自行设置 |
| TuShare token | 可选 |

手机或其他电脑访问时，不要填写 `127.0.0.1:8000`。应填写真实后端服务器 IP，例如：

```text
192.168.1.20:8000
```

`10.0.2.2:8000` 只适用于 Android 模拟器访问同一台开发电脑上的本地后端。

## 一键准备环境

在项目根目录打开 PowerShell，执行：

```powershell
.\deploy_windows_server.ps1
```

脚本会自动完成：

- 检查 Python 和 npm
- 创建 `.venv`
- 安装后端依赖
- 复制 `backend\.env.example` 到 `backend\.env`（如果 `.env` 不存在）
- 安装前端依赖
- 输出后端访问地址和下一步命令

如果需要自动放行 Windows 防火墙端口，请用管理员权限打开 PowerShell，然后执行：

```powershell
.\deploy_windows_server.ps1 -OpenFirewall
```

如果希望准备完成后直接启动后端：

```powershell
.\deploy_windows_server.ps1 -OpenFirewall -StartBackend
```

## 修改后端配置

打开：

```text
backend\.env
```

确认以下配置：

```env
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USERNAME=aistock
DB_PASSWORD=你的数据库密码
DB_NAME=ai_stock
DB_DIALECT=mysql
DB_DRIVER=mysqlconnector

APP_HOST=0.0.0.0
APP_PORT=8000

TUSHARE_ENABLED=false
TUSHARE_TOKEN=你的TuShareToken
```

如果启用 TuShare：

```env
TUSHARE_ENABLED=true
TUSHARE_TOKEN=你的TuShareToken
```

## 准备数据库

确保 MySQL 中已经创建数据库和用户。示例：

```sql
CREATE DATABASE ai_stock DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
CREATE USER 'aistock'@'%' IDENTIFIED BY '你的数据库密码';
GRANT ALL PRIVILEGES ON ai_stock.* TO 'aistock'@'%';
FLUSH PRIVILEGES;
```

如果需要导入项目自带初始化 SQL：

```powershell
mysql -u aistock -p ai_stock < db\ai_stock.sql
```

## 启动后端

在项目根目录执行：

```powershell
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

验证：

```powershell
Invoke-WebRequest http://127.0.0.1:8000/api/health -UseBasicParsing
```

看到 `healthy` 表示后端启动成功。

## 启动前端

另开一个 PowerShell 窗口：

```powershell
cd frontend
npm run web
```

移动端或模拟器首次登录前，请进入服务配置页，把后端地址改成真实后端 IP：

```text
<后端服务器IP>:8000
```

## 默认账号

| 用户名 | 密码 | 角色 |
| --- | --- | --- |
| admin | Test@bcd!234 | admin |
| Test | Test@bcd!234 | user |

注册的新用户默认未启用，需要管理员进入用户管理页启用。

## 常见问题

### 手机登录失败

确认手机可以访问后端服务器 IP，并且防火墙已放行 `8000` 端口。手机里不要使用 `127.0.0.1:8000`。

### Android 模拟器登录失败

如果后端就在同一台开发电脑上，可以使用：

```text
10.0.2.2:8000
```

如果后端在独立服务器上，请使用真实服务器 IP。

### 后端测试失败，提示连接不上 localhost:8000

部分后端测试会请求正在运行的后端服务。请先启动后端，再运行完整测试。

### 后端关闭后不能离线登录

该账号必须至少在线登录成功过一次。在线登录成功后才会保存离线登录密码哈希。

## 测试命令

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
