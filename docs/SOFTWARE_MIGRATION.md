# Software Migration Design

## Goal

拆解家庭 Windows 常见软件生态，保留功能，替换冗余组件。

## Processing Flow

发现软件

↓

识别功能

↓

寻找替代

↓

安装/验证替代方案

↓

删除旧组件

## 重点生态

### 360

分析：
- 安全卫士
- 杀毒
- 浏览器
- 压缩
- 看图
- 驱动工具

### 2345

分析：
- 浏览器
- 好压
- 看图王
- 推广组件

## Safety Rules

禁止直接删除：

- 用户正在使用浏览器
- 输入法
- 看图工具
- 驱动工具
- 安全软件

必须满足：

Replacement Ready + Function Test + User Confirm
