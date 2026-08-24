# Windows Clean Agent
# Task 009：Windows真实执行后端与回滚系统

版本：V3.6

## 目标

把 Task008 的 dry-run 组件整理变成可控、可恢复、可审计的真实执行链：

```text
网页确认 → Task005授权 → 执行前快照 → 固定Windows函数 → 状态验证 → 审计结果 → 可恢复
```

本任务不提供万能命令执行器，不执行 PowerShell、cmd 字符串、任意脚本或远程 Shell。开发电脑不执行真实系统修改。

## 新增模块

```text
src/agent/windows_backend/
  service_manager.py   # 固定服务函数，原生 Service Control Manager
  startup_manager.py   # 精确 HKCU Run/Startup Folder
  task_manager.py      # 精确 Task Scheduler COM 操作
  file_cleaner.py      # 显式目录 allowlist 的文件操作
  snapshot.py          # backup/<machine_id>/<timestamp>/snapshot.json
  rollback.py          # 服务、启动项、计划任务恢复
  verifier.py          # 只读状态验证
  engine.py            # 授权、快照、执行、验证、审计编排
```

## 固定动作与保护

只允许 `disable_service`、`disable_startup`、`remove_task`、`remove_component`。服务必须先匹配精确名称并且只能禁用，不能删除；启动项限 HKCU Run 和配置的 Startup 文件夹；计划任务必须同时通过名称、创建者/作者和执行路径校验；文件只能位于显式配置的推广组件目录。

Windows/Microsoft/Defender/防火墙、WPS、Office、微信、QQ、浏览器、输入法主体、用户词库、用户文件和系统目录均拒绝执行。未知组件、路径越界、规则不匹配或目标身份不符均 fail-closed。

## 快照与回滚

每个非 dry-run 动作先写入 JSON 快照，包含目标、任务、动作、组件和原状态。网页任务历史会显示快照 ID，并可创建新的、仍需目标用户授权的恢复任务。当前支持恢复服务启动类型/状态、启动项原值和计划任务 XML/状态；文件删除默认不提供自动恢复入口。

## 验证与失败处理

动作完成后必须验证服务已停止且禁用、启动项不存在、计划任务不存在或组件不存在。验证失败返回 `failed`，不继续执行后续动作，并保留快照和审计记录 `component_clean.log`。

## 部署边界

Windows 目标 Agent 需要可见的管理员授权宿主；计划任务 COM 适配器需要目标环境安装 `pywin32`。没有注入真实管理器时只能 dry-run。香港服务器、API Key、密码和管理员凭据不由本任务读取或保存。

## 验收

```powershell
python -m pytest -q
```

测试必须覆盖模拟服务、启动项、计划任务、快照、回滚、保护对象、路径越界、目标绑定、授权门和网页恢复任务创建。
