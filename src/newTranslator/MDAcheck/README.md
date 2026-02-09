# MDAcheck（Ecore + OCL）

本目录用于把 `B2CDSL` 的 textX 元模型导出为 EMF `Ecore`，从而在 Eclipse/EMF OCL 环境里运行 `check.ocl` 约束。

详细原理说明见：`转换原理与流程.md`

## 1) 生成 `b2c.ecore`

在项目根（`code/ChainCollab/src/newTranslator`）执行：

```bash
./.venv/bin/python MDAcheck/export_b2c_ecore.py
```

输出文件：`code/ChainCollab/src/newTranslator/MDAcheck/b2c.ecore`

## 2) 将 `.b2c` 转换为 `.xmi`

`.b2c` 是 textX DSL 的实例文本；Eclipse/EMF OCL 一般对 **XMI 实例模型**做校验，因此需要先转换：

```bash
# 输入：build 产物（或你的任意 .b2c）
./.venv/bin/python MDAcheck/b2c_to_xmi.py \
  --in build/b2c/chaincode.b2c \
  --out MDAcheck/chaincode.xmi
```

## 3) 在 Eclipse 里使用（概要）

- 导入 `b2c.ecore`（Ecore Tools / EMF）。
- 加载 `check.ocl`。
- 打开/加载 `chaincode.xmi`，对其执行约束校验。

## 4) 用脚本跑 Eclipse OCL 校验（Java Standalone）

Eclipse OCL（Pivot/Complete OCL）主要以 **Eclipse Bundle（p2）** 形式发布，Maven Central 上不保证可用。
因此本项目提供了 Tycho（p2）方式的命令行校验器：`MDAcheck/ocl-runner-tycho/`。

```bash
cd code/ChainCollab/src/newTranslator

# 仅跑校验（前提：b2c.ecore/chaincode.xmi 已存在）
mvn -q -f MDAcheck/ocl-runner-tycho/pom.xml -Dtycho.disableP2Mirrors=true \
  -Decore=MDAcheck/b2c.ecore -Docl=MDAcheck/check.ocl -Dxmi=MDAcheck/chaincode.xmi \
  integration-test

# 一键：导出 ecore + 转换 xmi + 运行 OCL 校验
bash MDAcheck/run_ocl_validate.sh
```

## 2) 在 Eclipse 里使用（概要）

- 导入 `b2c.ecore`（Ecore Tools / EMF）。
- 把 `check.ocl` 作为 OCL 约束文件加载到同一个环境里。
- 准备一个符合 `b2c.ecore` 的实例模型（通常是 `.xmi`），对其执行约束校验。
