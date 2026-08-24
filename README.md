# Windows Clean Agent V3.0

基于 Kilo Code + MCP 的一次性 Windows 家庭电脑软件生态整理 Agent。

## 项目目标

不是简单删除垃圾，而是：

- 扫描 Windows 家庭电脑
- 建立软件画像
- 分析软件真实用途
- 拆解软件生态
- 寻找安全替代方案
- 完成功能迁移
- 验证功能后清理冗余组件

## 核心架构

```
Scanner
 ↓
Software Inventory
 ↓
Software Fingerprint
 ↓
Function Analyzer
 ↓
Software Migration Engine
 ↓
Replacement Database
 ↓
Safety Gate
 ↓
Executor
 ↓
Verification
```

## 重点处理

### 360生态

处理：

- 360安全卫士
- 360杀毒
- 360浏览器
- 360压缩
- 360看图
- 360相关组件

原则：先保证功能，再删除。

### 2345生态

处理：

- 2345浏览器
- 2345好压
- 2345看图王
- 推广组件

## MCP能力

提供：

- 软件扫描
- 文件操作
- 系统信息读取
- 注册表分析
- 执行操作
- 报告生成

## 文档入口

- `docs/V3.0软件生态整理重构任务包.md`
- `docs/ARCHITECTURE.md`
- `docs/SOFTWARE_MIGRATION.md`
- `docs/REPLACEMENT_DATABASE.md`
- `任务包_002_软件指纹库与软件生态识别框架.md`

## 软件指纹识别（Task 002）

当前版本提供只读的软件资产采集与数据驱动指纹识别：

```powershell
python -m pip install -r requirements.txt
python main.py scan
python main.py analyze
```

命令生成 `software_inventory.json` 和 `software_profile.json`。首次运行读取 Windows 标准卸载注册表；已有 inventory 文件默认复用，可用 `--refresh-inventory` 重新采集。指纹规则位于 `rules/software_fingerprint/`，增加生态或产品时只需添加/修改 YAML，无需改分类器核心代码。

`analyze` 读取 `software_profile.json`，按 `database/` 中的替代数据库生成 `replacement_suggestion.json`。它只生成建议，不安装、卸载、删除或修改系统设置。浏览器是用户明确保护的类别，不生成迁移建议。

## 目标电脑指定软件生态整理规划（Task 004）

```powershell
python main.py scan --target-profile examples/target_profile.json --refresh-inventory
python main.py analyze
python main.py plan --target-profile examples/target_profile.json
```

输出位于 `reports/migration_plan.json` 和 `reports/migration_report.json`。开发电脑和目标电脑均不执行修改。P0/P1 软件直接保护，P2 普通软件仅报告，P3 等待人工审查，仅 P4 指定的高推广生态进入替代分析；规则位于 `rules/software_protection/`。

## 远程维护授权握手（Task 005）

Controller 可生成绑定目标身份的离线任务包：

```powershell
python main.py create-task --target-id PC001 --task-id task_001 --action analyze
```

目标 Agent 验证 `target_id` 后，为每项任务建立短期一次性会话，要求目标用户明确同意，再请求对应 A0/A1/A2 权限。用户拒绝、身份不符、会话不符或权限未授予时均停止。审计记录分别写入 `logs/session.log`、`authorization.log` 和 `execution.log`。

当前版本支持离线任务包/结果包及客户端主动连接接口，但不提供网络监听、后台服务、自动启动、自动提权、密码保存或系统动作执行器。`approved_action` 的真实实现保留到 Task 007。

## Web维护控制台（Task 006）

启动本地控制台：

```powershell
python -m server.run
```

默认只绑定 `127.0.0.1:8765`，SQLite 文件为 `maintenance.db`。控制台包含客户电脑、软件明细、任务历史和 AI 备用配置页面；Agent 使用主动轮询接口登记、心跳、上传画像、拉取任务和回传结果。设置 `WCA_CONSOLE_TOKEN` 与 `WCA_AGENT_TOKEN` 可启用两套独立令牌。内置服务器拒绝非回环绑定，远程部署需由外部认证 TLS 反向代理承载。

网页不会提供删除按钮或 Shell 输入框；保护软件只显示锁定，目标软件只能创建白名单任务，仍由 Task005 的目标 Agent 授权握手决定是否执行。

## 安全执行器（Task 007）

Task007 提供固定替代软件包目录 `packages/`（ImageGlass、7-Zip、VLC）和 `src/agent/executor/` 安全执行器。安装前校验固定包名、SHA-256 和捆绑组件；当前仓库只提交元数据，零哈希表示尚未配置真实安装包，禁止下载或盲装。

支持的执行操作仅有 `install_replacement`、`uninstall_component` 和 `optimize_input_method`。卸载使用精确白名单；WPS、Office、浏览器和输入法主体永远受保护。输入法只可整理推广启动项、推广服务、通知入口和推广缓存，不替换主体、不删除词库、不修改默认输入法。所有操作需要 Task005 用户授权和 Agent 权限，默认 dry-run，安装后必须经过注入式验证后端。

## Windows 后台组件清理引擎（Task 008）

Task008 增加 `src/agent/component_cleaner/`：只读扫描服务、启动项、计划任务和后台进程，使用 `rules/component_behavior/` 中的 YAML 识别鲁大师、360/2345 推广组件以及壁纸/屏保/桌面助手。规划等级为 C0-C4，默认最高只到 C2；C3/C4 只生成网页待确认计划。Windows、Microsoft、WPS、Office、微信、QQ、浏览器、输入法主体和用户数据永久保护；未知组件只记录。服务器 SQLite 增加后台组件库存，设备详情页显示组件并可创建已授权任务。执行器默认 dry-run，真实后端必须由目标 Agent 显式注入，执行后写入 `component_clean.log` 并进行注入式验证。



已支持 360、2345、腾讯、百度、搜狗和迅雷生态，以及 `security`、`browser`、`archive`、`image_viewer`、`driver_tool`、`downloader`、`input_method` 等分类。风险等级仅用于报告标记，不会触发任何操作。

运行测试：

```powershell
python -m pytest
```

## 安全原则

- 默认分析优先
- 删除需要验证
- 替代功能必须测试
- 用户文件保护
- 操作可追踪
