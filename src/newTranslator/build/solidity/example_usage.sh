#!/bin/bash

# 示例1: 没有构造函数的合约（如SimpleStorage）
python3 convert_contract.py simple_storage.json.backup \
  -c SimpleStorage \
  -o simple_storage_deployable.json

# 示例2: 有构造函数的合约（如WorkflowContract）
# 需要提供oracle地址参数
python3 convert_contract.py simple_storage.json.backup \
  -c WorkflowContract \
  -p '["0x1234567890123456789012345678901234567890"]' \
  -o workflow_deployable.json

echo "转换完成！"
echo "- simple_storage_deployable.json: 无构造函数参数"
echo "- workflow_deployable.json: 包含oracle地址参数"
