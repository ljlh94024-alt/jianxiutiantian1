# Remote Maintenance Agent Authorization

## Trust boundary

AI Controller 只能创建任务请求。目标电脑上的可见 Agent 负责身份校验、用户同意、权限申请和白名单分发。AI 不持有管理员密码，也不能直接调用管理员 Shell。

## Handshake

1. Controller 创建带 `target_id`、`task_id`、动作、风险和权限声明的任务包。
2. Agent 将任务目标与本地预配置身份比较；不一致立即拒绝并记录。
3. Agent 创建随机、短期、一次性的授权会话。
4. 本地可见 Consent Provider 返回绑定目标、任务、会话及权限等级的决定。
5. 拒绝即终止；同意后才向 Permission Provider 请求 A0/A1/A2。
6. 权限未授予即终止；成功后消费会话并调用显式注册的白名单处理器。
7. 会话、授权和结果分别写入追加式 JSON Lines 日志。

## Permission levels

- A0：普通读取和报告，不需管理员权限，但仍需本次用户同意
- A1：管理员任务，必须由可见宿主通过 Windows UAC 请求
- A2：安全软件、驱动、服务等高风险任务，需要二次等级的显式授权

默认 Permission Provider 不会提权。仓库中没有 `runas`、凭据获取、UAC 绕过或管理员 Shell 实现。

## Transport

首版定义客户端主动连接的 `OutboundTransport` 接口，要求认证 TLS。仓库不开放监听端口，不实现隐藏运行、自动启动或驻留服务。离线模式通过任务 JSON 和结果 JSON 往返。

## Task 007 boundary

Task 005 的执行器只分发调用方显式注册的白名单处理器。默认没有系统修改处理器，`approved_action` 返回 `not_implemented`。卸载、文件或系统配置修改必须等 Task 007 另行设计、审查和授权。

