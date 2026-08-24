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

## 安全原则

- 默认分析优先
- 删除需要验证
- 替代功能必须测试
- 用户文件保护
- 操作可追踪
