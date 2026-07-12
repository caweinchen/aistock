# Multica Daemon 仓库缓存恢复手册

本文用于两台开发电脑处理以下故障：Multica agent 执行 `repo checkout` 时报告 `cannot resolve requested ref`，同时 daemon 无法从 GitHub 刷新仓库缓存。

本流程只维护 Multica daemon 的 bare clone cache，不修改项目源码、产品文档内容或 Git 提交历史。

## TODO Tracking

- [x] 已确认 Multica `repo checkout` 从 daemon 的 bare clone cache 创建 worktree。
- [x] 已在前端电脑验证目标 ref 的安全补齐和缓存完整性检查方法。
- [ ] TODO：另一台电脑按本文完成验证，并确认 Multica agent 能成功 checkout。
- [ ] TODO：排查并长期解决两台电脑到 `github.com:443` 的间歇性超时或连接重置。

## 适用症状

同时或先后出现以下现象时使用本文：

```text
cannot resolve requested ref
Failed to connect to github.com port 443
Recv failure: Connection was reset
repo is configured but not synced
```

不要因为上述错误直接判断远端分支不存在。应分别检查 GitHub 远端、Multica bare cache 和网络链路。

## 工作原理

`multica repo checkout <url> --ref <ref>` 不直接使用 IDE 当前打开的项目目录。该命令由 Multica agent 在 daemon 任务环境内调用，daemon 从以下位置的 bare clone cache 创建独立 worktree：

```text
%USERPROFILE%\multica_workspaces\.repos\<workspace-id>\<repository-cache>
```

因此可能出现以下状态：

1. GitHub 上已经存在目标分支。
2. 本地普通项目目录也有对应 commit。
3. daemon 缓存因 GitHub 网络失败而没有目标 ref。
4. Multica 按短分支名解析失败。

## 当前已知目标

本次确认的信息为：

```text
Repository: https://github.com/caweinchen/aistock.git
Ref:        MUL-20260712
Commit:     339770790b04b7bf061fa702b5e3c4e508418ed1
```

该值只适用于本次已确认状态。以后处理其他分支时，必须重新从可信远端确认 commit SHA，不能照抄。

## 第一步：检查 daemon 和仓库登记

```powershell
multica daemon status
multica repo list --output json
```

预期结果：

- daemon 状态为 `running`。
- 仓库列表包含 `https://github.com/caweinchen/aistock.git`。

如果仓库未登记，应先通过正常 Multica 工作区配置添加仓库，不要手工创建缓存目录。

## 第二步：确认 GitHub 远端 ref

优先尝试 Git：

```powershell
git ls-remote --heads https://github.com/caweinchen/aistock.git MUL-20260712
```

如果 `github.com:443` 超时，但 GitHub API 可用，可以只读查询：

```powershell
$headers = @{ "User-Agent" = "Multica-cache-recovery" }
$remoteRef = Invoke-RestMethod `
  -Uri "https://api.github.com/repos/caweinchen/aistock/git/ref/heads/MUL-20260712" `
  -Headers $headers `
  -TimeoutSec 20

$remoteRef.ref
$remoteRef.object.sha
```

必须得到准确的 `refs/heads/...` 和 commit SHA 后才能继续。

## 第三步：定位 bare cache

```powershell
$matches = Get-ChildItem "$HOME\multica_workspaces\.repos" -Directory -Recurse |
  Where-Object Name -eq "github.com+caweinchen+aistock.git"

$matches | Select-Object -ExpandProperty FullName
```

正常情况下，每个 Multica workspace 对应该仓库的一个缓存目录。确认目标 workspace 后设置：

```powershell
$cache = "$HOME\multica_workspaces\.repos\<workspace-id>\github.com+caweinchen+aistock.git"
$ref = "MUL-20260712"
$sha = "339770790b04b7bf061fa702b5e3c4e508418ed1"
```

不要修改其他 workspace 的缓存。

## 第四步：执行安全前置检查

确认目录确实是 bare repository：

```powershell
git --git-dir="$cache" rev-parse --is-bare-repository
git --git-dir="$cache" remote -v
```

预期分别看到 `true` 和正确的 aistock 远端地址。

确认目标对象已经存在：

```powershell
git --git-dir="$cache" cat-file -t $sha
```

只有输出以下内容时才可继续：

```text
commit
```

如果对象不存在，禁止创建 ref。此时必须先恢复 GitHub 网络并让缓存完成 fetch，或者使用由 GitHub 验证过的正常 Git 传输方式补齐对象。

检查是否已经存在同名但指向其他 SHA 的 ref：

```powershell
git --git-dir="$cache" show-ref $ref
```

如果存在且 SHA 不同，应停止处理并重新核对远端，不能覆盖。

## 第五步：补齐缓存 ref

在上述检查全部通过后执行：

```powershell
git --git-dir="$cache" update-ref "refs/heads/$ref" $sha
git --git-dir="$cache" update-ref "refs/remotes/origin/$ref" $sha
```

同时补两个 ref 的原因是：现有 Multica bare cache 同时维护本地 heads 和远端跟踪 refs，而 checkout 接收的是短分支名。

## 第六步：验证缓存

```powershell
git --git-dir="$cache" rev-parse --verify "$ref^{commit}"
git --git-dir="$cache" rev-parse --verify "origin/$ref^{commit}"
git --git-dir="$cache" fsck --connectivity-only
```

前两条命令必须输出同一个预期 SHA，`fsck` 必须退出码为 `0`。

再次检查 daemon：

```powershell
multica daemon status
```

## 第七步：从 Multica agent 任务复测

重新运行对应 Multica agent 任务，并在任务环境内执行：

```text
multica repo checkout https://github.com/caweinchen/aistock.git --ref MUL-20260712
```

不要在普通 PowerShell 终端中把该命令失败当作缓存故障。`repo checkout` 需要 daemon task 注入 `MULTICA_DAEMON_PORT`、workspace ID、task ID 和 workdir；缺少这些变量时会明确提示该命令只能由 daemon 内的 agent 使用。

成功标准：

- 不再出现 `cannot resolve requested ref`。
- 输出新建 worktree 路径。
- worktree HEAD 等于远端确认的 SHA。
- worktree 包含 `frontend`、`backend` 和 `docs` 等仓库内容。

## 回滚

如果补错了 ref，并且已经重新确认该 ref 不应存在，可以只删除本次创建的两个引用：

```powershell
git --git-dir="$cache" update-ref -d "refs/heads/$ref"
git --git-dir="$cache" update-ref -d "refs/remotes/origin/$ref"
git --git-dir="$cache" fsck --connectivity-only
```

不要删除整个 `.repos`、workspace 或项目目录。不要使用 `git reset --hard`。

## 网络问题仍需单独处理

手工补 ref 只恢复已经存在于缓存中的 commit，不能替代正常 fetch。若出现新分支或新 commit，而对应对象尚未进入缓存，问题仍会复发。

建议分别检查：

```powershell
Resolve-DnsName github.com -Type A
Test-NetConnection github.com -Port 443
git config --show-origin --get-regexp "^(http\.|https\.|url\.|core\.gitproxy)"
git ls-remote https://github.com/caweinchen/aistock.git HEAD
```

重点核对 VPN、系统代理、Git 独立代理、防火墙、DNS 和网络出口。普通网页可以访问 GitHub，不代表 Git smart-HTTP 请求一定稳定。

## 禁止事项

- 不在未验证 SHA 的情况下创建或覆盖 ref。
- 不在 commit 对象缺失时创建悬空 ref。
- 不删除整个 Multica bare cache 来碰运气。
- 不把普通终端缺少 `MULTICA_DAEMON_PORT` 当成 daemon 故障。
- 不修改项目源码来规避仓库 checkout 问题。
- 不提交或推送仅用于本地缓存恢复的 ref。
