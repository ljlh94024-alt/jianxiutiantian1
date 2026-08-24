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
