# AIStock Docker 本机部署测试指南

这份文档用于用 Docker 部署并测试 AIStock。部署后会启动 3 个容器：

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

### Windows Server 2026 重要说明

本项目 Docker 方案使用的是 Linux 容器镜像：

- `mysql:8.0`
- `python:3.12-slim`
- `node:22-alpine`
- `nginx:1.27-alpine`

如果 Windows Server 2026 上的 Docker 当前运行在 Windows containers 模式，会出现类似错误：

```text
no matching manifest for windows/amd64 ... in the manifest list entries
```

这不是镜像源问题，而是容器平台不匹配。Windows containers 不能运行这些 Linux 镜像。

推荐做法：

1. **生产部署推荐**：使用 Linux 服务器或 Linux 虚拟机运行 Docker。
2. **Windows Server 测试部署**：在 Windows Server 上安装 WSL2 + Ubuntu，然后在 Ubuntu 里安装 Docker Engine，并在 Ubuntu 终端里执行本文的 Docker Compose 命令。
3. **不推荐**：把本项目改成 Windows containers。MySQL、Node、Nginx、Python 依赖链都会复杂很多，维护成本高。

Microsoft 官方文档说明 Windows Server 2022/2025 支持安装 WSL。Windows Server 2026 环境下也应优先走 WSL2/Ubuntu 方式来运行 Linux 容器。

如果你使用的是 Docker Desktop，必须切换到 Linux containers。右键系统托盘里的 Docker Desktop 图标，如果看到 `Switch to Linux containers...`，请点击切换；如果看到 `Switch to Windows containers...`，说明当前已经是 Linux containers。

## Windows Server 2026 推荐部署方式：WSL2 + Ubuntu

在 Windows Server 2026 的管理员 PowerShell 中执行：

```powershell
wsl --install -d Ubuntu-24.04
```

安装完成后重启服务器。重启后进入 Ubuntu：

```powershell
wsl -d Ubuntu-24.04
```

以下命令都在 Ubuntu 终端中执行。

安装基础工具：

```bash
sudo apt update
sudo apt install -y ca-certificates curl git
```

安装 Docker Engine：

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
```

退出 Ubuntu 后重新进入，让 docker 用户组生效：

```bash
exit
```

再次进入：

```powershell
wsl -d Ubuntu-24.04
```

验证 Docker：

```bash
docker --version
docker compose version
```

拉取项目代码：

```bash
git clone https://github.com/caweinchen/aistock.git
cd aistock
```

复制配置：

```bash
cp docker/.env.example docker/.env
```

编辑配置：

```bash
nano docker/.env
```

至少修改：

```env
MYSQL_ROOT_PASSWORD=你的MySQLRoot密码
DB_PASSWORD=你的应用数据库密码
```

启动：

```bash
docker compose --env-file docker/.env up -d --build
```

查看状态：

```bash
docker compose --env-file docker/.env ps
```

验证后端：

```bash
curl http://127.0.0.1:8000/api/health
```

### 可选

- TuShare token
- 真实服务器 IP 或域名
- HTTPS 证书和反向代理

如果端口已被占用，可以在 `docker\.env` 中修改。

## 国内网络加速说明

`docker\.env.example` 已提供两类国内镜像配置。

第一类是 Docker 基础镜像地址，影响 `mysql`、`python`、`node`、`nginx` 镜像拉取：

```env
MYSQL_IMAGE=docker.m.daocloud.io/library/mysql:8.0
PYTHON_IMAGE=docker.m.daocloud.io/library/python:3.12-slim
NODE_IMAGE=docker.m.daocloud.io/library/node:22-alpine
NGINX_IMAGE=docker.m.daocloud.io/library/nginx:1.27-alpine
```

第二类是容器构建过程中的 apt、apk、pip、npm 下载源：

```env
APT_MIRROR=https://mirrors.aliyun.com/debian
ALPINE_MIRROR=https://mirrors.aliyun.com/alpine
PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
NPM_REGISTRY=https://registry.npmmirror.com
```

如果部署时仍然看到 `registry-1.docker.io` 超时，说明当前使用的镜像地址仍是 Docker Hub。请确认 `docker\.env` 中已经包含并启用了上面的 `MYSQL_IMAGE`、`PYTHON_IMAGE`、`NODE_IMAGE`、`NGINX_IMAGE`。

也可以在服务器的 Docker daemon 或 Docker Desktop 中配置 registry mirror。Linux 示例：

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

DOCKER_PLATFORM=linux/amd64

MYSQL_IMAGE=docker.m.daocloud.io/library/mysql:8.0
PYTHON_IMAGE=docker.m.daocloud.io/library/python:3.12-slim
NODE_IMAGE=docker.m.daocloud.io/library/node:22-alpine
NGINX_IMAGE=docker.m.daocloud.io/library/nginx:1.27-alpine

APT_MIRROR=https://mirrors.aliyun.com/debian
ALPINE_MIRROR=https://mirrors.aliyun.com/alpine
PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
NPM_REGISTRY=https://registry.npmmirror.com
```

## 第 2 步：构建并启动

在项目根目录执行：

```powershell
docker compose --env-file docker\.env up -d --build
```

如果是在 WSL2/Ubuntu 或 Linux 服务器中执行，路径分隔符使用 `/`：

```bash
docker compose --env-file docker/.env up -d --build
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

### no matching manifest for windows/amd64

如果看到：

```text
no matching manifest for windows/amd64 ... in the manifest list entries
```

说明 Docker Desktop 当前使用的是 Windows containers。请切换到 Linux containers：

1. 右键系统托盘 Docker Desktop 图标。
2. 点击 `Switch to Linux containers...`。
3. 等待 Docker 重启完成。
4. 重新执行：

```powershell
docker compose --env-file docker\.env up -d --build
```

`docker\.env` 中应保留：

```env
DOCKER_PLATFORM=linux/amd64
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
