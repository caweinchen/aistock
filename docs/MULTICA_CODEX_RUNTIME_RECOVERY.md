# Multica Codex Runtime 恢复手册

本文用于处理 Multica agent 启动 Codex app-server 后长期没有语义事件，并在 30 秒后失败的问题。本文只调整本机 Multica/Codex 运行时，不修改项目业务代码。

## TODO Tracking

- [x] 已在前端电脑完成根因定位和自动 smoke issue 验证。
- [x] 已确认最终测试返回 `MULTICA_CODEX_OK`。
- [ ] TODO：另一台电脑按本文建立独立 runtime profile 并完成 smoke issue 验证。
- [ ] TODO：VS Code OpenAI 扩展升级后重新同步配套 binary，并复测 runtime。

## 适用症状

典型错误如下：

```text
codex app-server no progress timeout after 30s
received turn start but no item, message, tool, turn/completed, or error event
codex_semantic_inactivity
```

日志还可能包含：

```text
failed to decode models response: missing field `models`
http/request failed: error sending request for url
https://chatgpt.com/backend-api/ps/mcp
```

该故障发生在 Codex app-server 初始化或模型事件传输阶段，与 Git 仓库 checkout 是两类问题。若日志已经出现 `repo checkout`、`cannot resolve requested ref` 或 bare cache 错误，应改用 [`MULTICA_DAEMON_REPO_CACHE_RECOVERY.md`](MULTICA_DAEMON_REPO_CACHE_RECOVERY.md)。

## 已确认的根因

本次环境中：

- VS Code OpenAI 扩展使用其内置 `codex.exe`，运行正常。
- Multica 默认调用全局 `codex.cmd`，app-server 运行异常。
- 两者即使显示相同版本号，也可能是不同构建产物，不能只比较 `codex --version`。
- VS Code 以 `features.code_mode_host=true` 启动 Codex。
- Codex 的 `apps` feature 默认启用，会连接 `chatgpt.com/backend-api/ps/mcp`。
- 当前网络无法稳定访问该地址，Apps MCP 初始化阻塞了 Multica turn。
- `code_mode_host` 还依赖与 `codex.exe` 同目录的 `codex-code-mode-host.exe`。

最终有效方案是让 Multica 使用 VS Code 扩展内置的同一套 binary，启用 code-mode host，同时禁用不需要且不可达的 ChatGPT Apps MCP。

## 已证明无效的尝试

### 只安装相同版本的 npm CLI

以下操作不足以保证与 VS Code 行为一致：

```powershell
npm install -g @openai/codex@0.144.0-alpha.4
```

原因是 VS Code 内置 binary 与 npm 发布物可能不是相同构建。

### 使用 `features.rmcp_client=false`

该构建已经不识别 `rmcp_client` feature。参数可能被 CLI 接受，但不会关闭 Apps MCP。

实际可用的开关是：

```text
features.apps=false
```

可通过以下命令查看当前构建支持的 feature：

```powershell
codex features list
```

### 只复制 `codex.exe`

启用 `features.code_mode_host=true` 后还需要：

```text
codex-code-mode-host.exe
```

缺少该文件时，agent 可能产生消息，但所有工具执行都会报告找不到 code-mode host。

### 直接固定到 VS Code 扩展目录

Multica 0.3.43 在本次 Windows 环境中曾将扩展目录里的绝对路径误判为不可执行。此外，VS Code 扩展升级后目录名会变化。因此应复制到稳定的 Multica bin 目录。

## 第一步：确认 VS Code Codex 正常

列出扩展目录：

```powershell
Get-ChildItem "$HOME\.vscode\extensions" -Directory |
  Where-Object Name -Match '^openai\.chatgpt'
```

设置实际目录：

```powershell
$extension = "$HOME\.vscode\extensions\openai.chatgpt-<version>-win32-x64"
$sourceDir = Join-Path $extension "bin\windows-x86_64"
$sourceCodex = Join-Path $sourceDir "codex.exe"
$sourceHost = Join-Path $sourceDir "codex-code-mode-host.exe"

Test-Path -LiteralPath $sourceCodex
Test-Path -LiteralPath $sourceHost
& $sourceCodex --version
```

两个 `Test-Path` 都必须返回 `True`。

## 第二步：复制到稳定目录

```powershell
$targetCodex = "$HOME\.multica\bin\codex-vscode.exe"
$targetHost = "$HOME\.multica\bin\codex-code-mode-host.exe"

Copy-Item -LiteralPath $sourceCodex -Destination $targetCodex -Force
Copy-Item -LiteralPath $sourceHost -Destination $targetHost -Force
```

验证文件哈希：

```powershell
(Get-FileHash -LiteralPath $sourceCodex -Algorithm SHA256).Hash
(Get-FileHash -LiteralPath $targetCodex -Algorithm SHA256).Hash
(Get-FileHash -LiteralPath $sourceHost -Algorithm SHA256).Hash
(Get-FileHash -LiteralPath $targetHost -Algorithm SHA256).Hash
```

每一对 source/target 哈希必须一致。然后验证：

```powershell
& $targetCodex --version
& $targetCodex features list
```

## 第三步：创建 custom runtime profile

先检查是否已经存在：

```powershell
multica runtime profile list --output json
```

不存在时创建：

```powershell
$profileJson = multica runtime profile create `
  --display-name "VS Code Codex" `
  --description "Codex binary copied from the working VS Code OpenAI extension" `
  --command-name codex-vscode `
  --protocol-family codex `
  --output json

$profile = $profileJson | ConvertFrom-Json
$profileId = $profile.id
```

固定本机 executable：

```powershell
multica runtime profile set-path $profileId --path $targetCodex
```

Profile ID 在每个 workspace 中不同，不要复制另一台电脑的 UUID。

## 第四步：重启 daemon

```powershell
multica daemon restart
multica daemon status
```

如果 daemon 由 Multica Desktop 或更高权限启动，普通终端可能返回 `OpenProcess: Access is denied`。此时关闭并重新打开 Multica Desktop。

重启后查询 runtime：

```powershell
multica runtime list --output json
```

找到满足以下条件的本机 runtime：

```text
name       = VS Code Codex (<machine>)
profile_id = <刚创建的 profile ID>
status     = online
```

记录其 `id` 为 `$runtimeId`。另一台电脑会生成不同 runtime ID。

## 第五步：将 agent 切换到新 runtime

先查询 agent：

```powershell
multica agent list --output json
```

记录目标 agent 的 `id` 为 `$agentId`，然后更新：

```powershell
multica agent update $agentId `
  --runtime-id $runtimeId `
  --model gpt-5.6-sol `
  --custom-args '["-c","features.code_mode_host=true","-c","features.apps=false"]' `
  --output json
```

Windows PowerShell 5.1 可能破坏 JSON 引号。如果命令报告 `--custom-args must be a valid JSON array of strings`，使用 `.NET ProcessStartInfo` 明确转义：

```powershell
$multicaExe = (Get-Command multica.exe).Source
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $multicaExe
$psi.Arguments = 'agent update ' + $agentId +
  ' --runtime-id ' + $runtimeId +
  ' --model gpt-5.6-sol' +
  ' --custom-args "[\"-c\",\"features.code_mode_host=true\",\"-c\",\"features.apps=false\"]"' +
  ' --output json'
$psi.UseShellExecute = $false
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.CreateNoWindow = $true

$process = [System.Diagnostics.Process]::Start($psi)
$stdout = $process.StandardOutput.ReadToEnd()
$stderr = $process.StandardError.ReadToEnd()
$process.WaitForExit()
$stdout
$stderr
$process.ExitCode
```

验证 agent：

```powershell
multica agent get $agentId --output json
```

必须确认：

```json
{
  "runtime_id": "<new-runtime-id>",
  "model": "gpt-5.6-sol",
  "custom_args": [
    "-c",
    "features.code_mode_host=true",
    "-c",
    "features.apps=false"
  ]
}
```

## 第六步：自动 smoke issue

使用只允许固定回复、禁止修改文件的最小任务：

```powershell
$smoke = multica issue create `
  --title "[SMOKE] VS Code Codex runtime verification" `
  --description "Diagnostic only. Do not inspect repositories, do not modify files, and do not create a PR. Reply exactly: MULTICA_CODEX_OK" `
  --assignee-id $agentId `
  --project <project-id> `
  --priority low `
  --output json

$issueId = ($smoke | ConvertFrom-Json).id
```

查询运行结果：

```powershell
multica issue runs $issueId --output json
multica agent tasks $agentId --output json
```

成功标准：

- run 的 `status` 为 `completed`。
- `error` 为 `null`。
- `result.output` 包含 `MULTICA_CODEX_OK`。
- daemon 日志出现 `reasoning`、`agentMessage` 或 `tool-use`。
- 不再出现 `codex_semantic_inactivity`。

## 第七步：检查实际日志

```powershell
rg -n "invoking backend|agent command|semantic activity|agent finished|MULTICA_CODEX_OK|no progress timeout" `
  "$HOME\.multica\daemon.log" |
  Select-Object -Last 160
```

应能确认实际 executable 和参数，例如：

```text
exec=C:\Users\<user>\.multica\bin\codex-vscode.exe
features.code_mode_host=true
features.apps=false
agent finished ... status=completed
```

## 允许存在的非阻塞警告

在网络不稳定时仍可能看到：

```text
failed to send analytics events
stream disconnected - retrying sampling request
Reconnecting... 1/5
```

只要出现持续语义活动并最终 `status=completed`，这些警告不等同于任务失败。

## VS Code 扩展升级后的维护

扩展升级后，新目录可能包含新版配套 binary。重复以下步骤：

1. 找到最新 `openai.chatgpt-<version>-win32-x64`。
2. 重新复制 `codex.exe` 和 `codex-code-mode-host.exe`。
3. 校验 SHA-256。
4. 重启 Multica daemon。
5. 重新运行 smoke issue。

不要只更新一个 binary。`codex.exe` 和 code-mode host 应来自同一扩展版本。

## 回滚

先把 agent 切回原 runtime：

```powershell
multica agent update $agentId --runtime-id <original-runtime-id> --output json
```

然后删除 profile：

```powershell
multica runtime profile delete $profileId
```

确认没有 agent 使用稳定副本后，才删除：

```text
%USERPROFILE%\.multica\bin\codex-vscode.exe
%USERPROFILE%\.multica\bin\codex-code-mode-host.exe
```

不要删除 Multica 自带的 `multica.exe` 或整个 `.multica\bin` 目录。

## 本机验证记录

前端电脑最终自动 smoke run：

```text
Issue: AI-8
Runtime: VS Code Codex (Leven)
Status: completed
Tools: 9
Models with usage: 1
Final output: MULTICA_CODEX_OK
```

该验证没有修改 AIStock 项目业务代码。
