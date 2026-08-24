# Windows Clean Agent
# Task 006：Web维护控制台与Agent通信系统

版本：V3.3

## 目标

在 Task005 的任务协议、身份绑定、授权会话和 Agent 骨架基础上，增加维护人员使用的 Web 控制台、SQLite 服务器、Agent 主动通信和 AI 备用配置页面。

AI 只作为分析助手、报告助手和建议助手，不进入执行链。人工查看、人工决定、网页生成任务，目标 Agent 再按 Task005 授权握手处理。

## 服务器与数据库

新增 `server/api/`、`server/database/`、`server/models/`、`server/task_queue/`。SQLite 保存 `devices`、`software`、`tasks`、`logs`，并保存扫描 artifacts 和脱敏展示的 AI 配置。

Agent 接口：登记、心跳、上传 `computer_profile`/`software_inventory`/`software_profile`/`migration_plan`、主动拉取任务、回传结果。服务器不监听客户电脑端口；内置开发服务器只绑定回环，远程部署必须使用认证 TLS 反向代理。

## Web 页面

`web/dashboard/index.html` 提供客户电脑列表、电脑详情/软件保护状态、任务历史和 AI 配置。WPS、微信、QQ、浏览器、输入法等保护软件显示锁定；目标软件只允许生成白名单任务，不提供删除或 Shell 控件。

## 安全边界

保留 Task005 的 A0/A1/A2 权限和目标用户授权。禁止远程 Shell、隐藏控制、自动启动、绕过权限、删除、格式化和禁用安全。`approved_action` 在 Task007 前没有默认系统执行器。

## 验收

测试覆盖 Agent 登记、心跳、扫描结果上传、网页读取、任务创建/拉取/回传、AI 配置脱敏、令牌隔离和客户端主动 HTTP 轮询。提交信息：`feat: add web maintenance dashboard and agent communication`。

# 任务结束
