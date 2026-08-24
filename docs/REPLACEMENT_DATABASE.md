# Replacement Database Design

## Purpose

维护旧软件到安全替代方案的映射。

## Examples

|旧软件|功能|替代|
|-|-|-|
|360压缩|压缩解压|7-Zip|
|2345好压|压缩解压|7-Zip|
|2345看图王|图片查看|ImageGlass / IrfanView|
|360浏览器|网页浏览|Edge / Chrome / Firefox|

## Rules

替代软件必须先验证功能，再允许卸载旧软件。

数据库文件未来对应：

replacement_database.json
