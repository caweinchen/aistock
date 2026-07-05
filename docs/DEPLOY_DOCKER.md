# AIStock Docker 本机部署测试指南

这份文档用于在本机用 Docker 部署并测试 AIStock。部署后会启动 3 个容器：

- `aistock-mysql`：MySQL 8.0 数据库
- `aistock-backend`：FastAPI 后端，默认映射到本机 `8000`
- `aistock-frontend`：Expo Web 静态站点，默认映射到本机 `8080`

## 需要准备什么

### 必备

- Docker Desktop 或 Docker Engine
- Docker Compose
- 本项目代码
- 可用端口：
  - `3306`：MySQL
  - `8000`：后端 API
  - `8080`：前端 Web

### 可选

- TuShare token
- 真实服务器 IP 或域名
- HTTPS 证书和反向代理

如果端口已被占用，可以在 `docker\.env` 中修改。

## 国内网络加速说明

`docker\.env.example` 已提供 apt、apk、pip、npm 的国内镜像配置：

```env
APT_MIRROR=https://mirrors.aliyun.com/debian
ALPINE_MIRROR=https://mirrors.aliyun.com/alpine
PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
NPM_REGISTRY=https://registry.npmmirror.com
```

这些配置只影响 Docker build 过程中容器内部的软件包下载。

如果卡在 `python:3.12-slim`、`node:22-alpine`、`nginx:1.27-alpine`、`mysql:8.0` 这些基础镜像拉取阶段，需要在服务器的 Docker daemon 或 Docker Desktop 中配置 registry mirror。Linux 示例：

```bash
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json >/dev/null <<'EOF'
{
  "registry-mirrors": [
    "https://docker.m.daocloud.io"
  ]
}
EOF
sudo systemctl restart docker
```

Windows Docker Desktop：进入 Settings -> Docker Engine，在 JSON 中加入 `registry-mirrors` 后 Apply & Restart。

## 第 1 步：准备 Docker 环境变量

在项目根目录执行：

```powershell
copy docker\.env.example docker\.env
```

打开 `docker\.env`，至少修改这两项：

```env
MYSQL_ROOT_PASSWORD=你的MySQLRoot密码
DB_PASSWORD=你的应用数据库密码
```

如果要使用 TuShare：

```env
TUSHARE_ENABLED=true
TUSHARE_TOKEN=你的TuShareToken
```

完整示例：

```env
MYSQL_ROOT_PASSWORD=Root@123456
DB_USERNAME=aistock
DB_PASSWORD=AI@stock!234
DB_NAME=ai_stock

MYSQL_PORT=3306
BACKEND_PORT=8000
FRONTEND_PORT=8080

APP_DEBUG=false
TUSHARE_ENABLED=false
TUSHARE_TOKEN=
```

## 第 2 步：构建并启动

在项目根目录执行：

```powershell
docker compose --env-file docker\.env up -d --build
```

第一次启动会：

- 拉取 MySQL、Python、Node、Nginx 镜像
- 构建后端镜像
- 构建前端静态文件
- 创建 MySQL 数据卷
- 如果数据库数据卷是新的，会导入 `db\ai_stock.sql`

## 第 3 步：查看容器状态

```powershell
docker compose --env-file docker\.env ps
```

期望看到：

```text
aistock-mysql      running / healthy
aistock-backend    running / healthy
aistock-frontend   running
```

如果后端没有 healthy，查看日志：

```powershell
docker compose --env-file docker\.env logs -f backend
```

如果数据库没有 healthy，查看日志：

```powershell
docker compose --env-file docker\.env logs -f mysql
```

## 第 4 步：验证服务

验证后端：

```powershell
Invoke-WebRequest http://127.0.0.1:8000/api/health -UseBasicParsing
```

返回包含 `healthy` 即成功。

验证前端：

```text
http://127.0.0.1:8080
```

默认测试账号：

| 用户名 | 密码 | 角色 |
| --- | --- | --- |
| admin | Test@bcd!234 | admin |
| Test | Test@bcd!234 | user |

## 第 5 步：移动端如何填写后端地址

如果前端 Web 和后端都在本机 Docker 中运行，本机浏览器测试时后端地址填写：

```text
127.0.0.1:8000
```

如果手机访问同一台电脑上的后端，需要填写电脑的真实局域网 IP，例如：

```text
192.168.1.20:8000
```

不要在手机上填写 `127.0.0.1:8000`，它会指向手机自身。

`10.0.2.2:8000` 只适用于 Android 模拟器访问同一台开发电脑上的本地后端。

## 常用命令

停止容器但保留数据库数据：

```powershell
docker compose --env-file docker\.env down
```

重新启动：

```powershell
docker compose --env-file docker\.env up -d
```

重新构建：

```powershell
docker compose --env-file docker\.env up -d --build
```

查看日志：

```powershell
docker compose --env-file docker\.env logs -f
```

删除容器和数据库数据卷：

```powershell
docker compose --env-file docker\.env down -v
```

注意：`down -v` 会删除 MySQL 数据卷，数据库数据会丢失。

## 数据库初始化说明

Compose 文件会把 `db\ai_stock.sql` 挂载到 MySQL 初始化目录：

```text
/docker-entrypoint-initdb.d/01_ai_stock.sql
```

只有在 MySQL 数据卷首次创建时才会自动导入。后续如果想重新导入，需要先删除数据卷：

```powershell
docker compose --env-file docker\.env down -v
docker compose --env-file docker\.env up -d
```

## 常见问题

### 端口被占用

修改 `docker\.env`：

```env
MYSQL_PORT=3307
BACKEND_PORT=8001
FRONTEND_PORT=8081
```

然后重新启动：

```powershell
docker compose --env-file docker\.env up -d
```

### 后端连不上数据库

确认 `docker\.env` 中的 `DB_PASSWORD` 和 `MYSQL_ROOT_PASSWORD` 已设置。Docker 内部后端连接数据库时使用：

```env
DB_HOST=mysql
```

不要改成 `127.0.0.1`。

### 前端打开了但登录失败

进入前端服务配置页，确认后端地址填写正确：

```text
127.0.0.1:8000
```

如果是手机访问，填写真实电脑或服务器 IP：

```text
<后端服务器IP>:8000
```

### 修改代码后没有变化

重新构建镜像：

```powershell
docker compose --env-file docker\.env up -d --build
```
