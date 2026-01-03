#!/usr/bin/env python3
"""
将solc编译输出的JSON格式转换为简化的合约部署格式

输入格式: solc --combined-json abi,bin 生成的JSON
输出格式: 包含 contract(bytecode), definition(ABI), input(constructor params) 的简化JSON
"""

import json
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional


def extract_contract_info(
    solc_output: Dict[str, Any],
    contract_name: Optional[str] = None,
    constructor_params: Optional[List[Any]] = None
) -> Dict[str, Any]:
    """
    从solc输出中提取指定合约的信息

    Args:
        solc_output: solc --combined-json abi,bin 的输出
        contract_name: 要提取的合约名称，如果为None则提取第一个非接口合约
        constructor_params: 构造函数参数值列表（可选）

    Returns:
        包含 contract, definition, input 的字典
    """
    contracts = solc_output.get("contracts", {})

    if not contracts:
        raise ValueError("No contracts found in solc output")

    # 如果未指定合约名，选择第一个有bytecode的合约（排除接口）
    if contract_name is None:
        for name, info in contracts.items():
            if info.get("bin") and len(info["bin"]) > 0:
                contract_name = name
                break
        if contract_name is None:
            raise ValueError("No deployable contract found (all contracts have empty bytecode)")

    # 查找匹配的合约
    contract_info = None
    for name, info in contracts.items():
        if contract_name in name or name.endswith(f":{contract_name}"):
            contract_info = info
            break

    if contract_info is None:
        available = ", ".join(contracts.keys())
        raise ValueError(f"Contract '{contract_name}' not found. Available: {available}")

    # 提取bytecode
    bytecode = contract_info.get("bin", "")

    # 提取ABI
    abi = contract_info.get("abi", [])

    # input字段：如果提供了constructor_params则使用，否则为空数组
    # Firefly需要的是构造函数参数的值数组，不是参数定义
    input_values = constructor_params if constructor_params is not None else []

    return {
        "contract": bytecode,
        "definition": abi,
        "input": input_values
    }


def convert_file(
    input_path: Path,
    output_path: Optional[Path] = None,
    contract_name: Optional[str] = None,
    constructor_params: Optional[List[Any]] = None,
    pretty: bool = True
) -> None:
    """
    转换JSON文件

    Args:
        input_path: solc输出的JSON文件路径
        output_path: 输出文件路径，如果为None则覆盖输入文件
        contract_name: 要提取的合约名称
        constructor_params: 构造函数参数值列表
        pretty: 是否格式化输出
    """
    # 读取输入文件
    with open(input_path, 'r', encoding='utf-8') as f:
        solc_output = json.load(f)

    # 转换格式
    result = extract_contract_info(solc_output, contract_name, constructor_params)

    # 确定输出路径
    if output_path is None:
        output_path = input_path

    # 写入输出文件
    with open(output_path, 'w', encoding='utf-8') as f:
        if pretty:
            json.dump(result, f, indent=2, ensure_ascii=False)
        else:
            json.dump(result, f, ensure_ascii=False)

    print(f"Converted successfully: {output_path}")
    print(f"  - Bytecode length: {len(result['contract'])} chars")
    print(f"  - ABI items: {len(result['definition'])}")
    print(f"  - Constructor inputs: {len(result['input'])}")


def main():
    """命令行入口"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Convert solc JSON output to simplified contract deployment format"
    )
    parser.add_argument(
        "input",
        type=Path,
        help="Input JSON file (solc --combined-json abi,bin output)"
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="Output JSON file (default: overwrite input file)"
    )
    parser.add_argument(
        "-c", "--contract",
        help="Contract name to extract (default: first non-interface contract)"
    )
    parser.add_argument(
        "-p", "--params",
        help="Constructor parameters as JSON array (e.g., '[\"0x123...\", 42]')"
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Output compact JSON (no pretty printing)"
    )

    args = parser.parse_args()

    # 解析constructor参数
    constructor_params = None
    if args.params:
        try:
            constructor_params = json.loads(args.params)
            if not isinstance(constructor_params, list):
                print("Error: --params must be a JSON array", file=sys.stderr)
                sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in --params: {e}", file=sys.stderr)
            sys.exit(1)

    try:
        convert_file(
            args.input,
            args.output,
            args.contract,
            constructor_params,
            pretty=not args.compact
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
