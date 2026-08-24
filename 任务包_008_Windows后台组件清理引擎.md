# Windows Clean Agent
# Task 008：Windows后台组件清理引擎

版本：V3.5

## 目标

在既有扫描、软件指纹、规划、授权、Web 控制台和安全执行器基础上，识别软件伸出的后台组件：服务、启动项、计划任务、后台进程、壁纸/屏保/桌面助手、更新助手和推广组件。

本阶段必须遵循：

- 先扫描、匹配、规划，再由网页人工确认；默认只读或 dry-run。
- 永久保护 Windows/Microsoft 系统组件、WPS、Office、微信、QQ、浏览器、输入法主体、用户词库和用户数据。
- 未命中规则、来源不明或保护范围内的组件只能记录，不能处理。
- 禁止批量关闭服务、任意删除系统文件、隐藏运行、绕过授权或连接未经配置的服务器。

## 新增目录

```text
src/agent/component_cleaner/
  models.py scanner.py matcher.py planner.py executor.py verifier.py audit.py
rules/component_behavior/
  services.yaml startup.yaml scheduled_tasks.yaml desktop_apps.yaml
tests/component_cleaner/
```

## 扫描与规则

扫描器支持注入式数据源，Windows 实现只读查询 Service Manager、Run 注册表/Startup 文件夹、Task Scheduler 和进程列表。规则全部来自 YAML，按组件类型、名称、发布商和路径匹配，首批覆盖鲁大师、360 壁纸/资讯/桌面助手、2345 更新/推广组件以及壁纸、屏保、桌面美化程序。

## 计划等级

```text
C0 仅记录
C1 禁止启动
C2 禁用服务（默认规划上限）
C3 删除推广组件（必须网页确认）
C4 完整卸载（必须网页确认，当前不由后台组件执行器默认提供）
```

规划器输出 `record`、`disable_startup`、`disable_service`、`remove_task` 或 `remove_component`，并带有风险、规则、保护状态和是否需要确认。超过默认 C2 的规则只生成待确认计划，不会静默降级为执行动作。

## 执行与验证

执行器只接受 Task005 的授权任务和白名单动作；C3/C4 必须有网页人工确认。默认后端为 dry-run，真实服务/注册表/计划任务修改必须由目标 Agent 显式注入经过审查的后端。执行后按组件类型验证服务停止、启动项/计划任务/组件消失或进程状态，并追加写入 `component_clean.log`。

## Web 与服务器

服务器 SQLite 增加 `components` 表，接受 `component_inventory` 与 `component_plan` 工件并在设备详情返回后台组件。网页增加“后台组件”区域，只为规则命中的组件创建 `approved_action` 任务；保护项显示锁定，未知项不提供执行入口。

## 验收

```powershell
python -m pytest -q
```

必须验证：规则命中、C3 确认门、WPS/浏览器/输入法保护、任务身份校验、审计日志和服务/启动项/计划任务的注入式验证。开发电脑不执行实际禁用、删除或系统修改。
