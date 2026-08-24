# Windows Clean Agent
# Task 005：远程维护 Agent 与授权握手系统设计任务包

版本：V3.2

## 一、任务目标

维护人员电脑运行 AI Controller，目标家庭电脑运行可见的轻量 Agent。AI 只能生成任务请求；Local Agent 必须完成目标身份校验、权限检查和本地用户授权后，才能调用白名单处理器。

## 二、严格边界

禁止 AI 直接获得管理员 Shell，禁止自动提权、保存管理员密码、绕过 UAC、隐藏运行、自动启动、后台驻留、开放客户电脑端口或未授权控制。本任务不实现 Task 007 的系统修改执行器。

## 三、模块

- `src/controller/task_sender.py`：创建目标绑定任务包
- `src/agent/client.py`：接收、校验、授权握手和离线结果
- `src/agent/executor.py`：仅分发显式注册的白名单处理器
- `src/authorization/consent.py`：任务级用户同意
- `src/authorization/permission.py`：A0/A1/A2 权限接口
- `src/authorization/session.py`：短期一次性授权会话

## 四、任务和权限

任务包至少包含 `target_id`、`task_id`、`action`、`risk`、`require_admin`。允许动作仅为 `scan`、`analyze`、`report`、`approved_action`；拒绝 `delete_all`、`format`、`disable_security`、`hidden_execute`。

A0 用于普通读取和报告；A1 需要可见 Windows UAC；A2 用于安全软件、驱动或服务等高风险请求。默认权限提供器只允许 A0，不会自动触发或绕过 UAC。

## 五、身份、授权与通信

本地 `target_identity` 包含 `target_id`、计算机名、硬件标识和创建时间。授权必须同时绑定目标、任务、随机会话及权限等级；拒绝、过期、复用或错绑均停止。

联网模式只定义目标客户端主动发起的认证 TLS 传输接口，不开放端口。离线模式使用任务包和结果包复制往返。

## 六、日志与验收

会话、授权和执行结果分别记录到 `session.log`、`authorization.log`、`execution.log`。测试覆盖 A0 扫描、A1/A2 权限请求、用户拒绝、错误目标、错绑授权、动作黑名单、三类日志及离线往返。

提交信息：`feat: add remote maintenance agent authorization system`

# 任务结束
