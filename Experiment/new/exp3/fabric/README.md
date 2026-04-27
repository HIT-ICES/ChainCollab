# Fabric Track

这一组目录预留给实验三中的 Fabric / Go 执行对照线。

## 当前状态

当前实验三里已经有：

- DSL 参考语义执行线
- Solidity / FireFly 执行线

Fabric 这一侧目前还没有独立执行脚本落到 `exp3/` 目录中，因此这里先作为并行结构入口保留。

## 未来建议放这里的内容

- Fabric 回放脚本
- Fabric 环境配置模板
- 与 DSL 共享的路径输入文件
- Fabric 执行轨迹输出说明

## 推荐目标结构

后续建议让 Fabric 这条线也做到：

- 使用与 DSL / Solidity 相同的 `steps`
- 输入相同路径文件
- 输出统一格式轨迹

这样实验三就能形成：

- DSL
- Fabric
- Solidity

三条真正并行的执行线。
