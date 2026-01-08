#
# SPDX-License-Identifier: Apache-2.0
#
import os
import json
import subprocess
import tempfile
import logging
import re
from typing import Tuple, Dict, Optional

logger = logging.getLogger(__name__)


class SolidityCompiler:
    """Wrapper for Solidity compiler (solc) operations."""

    def __init__(self, solc_path: str = "solc", version: str = "0.8.19"):
        """
        Initialize the Solidity compiler wrapper.

        Args:
            solc_path: Path to the solc executable, defaults to "solc" (assumes it's in PATH)
            version: Solidity version to use (requires solc-select to be installed)
        """
        self.solc_path = solc_path
        self.version = version

        # 尝试使用 solc-select 切换到指定版本
        try:
            import subprocess
            result = subprocess.run(
                ["solc-select", "use", self.version],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                logger.info(f"Successfully switched to Solidity {self.version}")
            else:
                logger.warning(f"Failed to switch to Solidity {self.version}: {result.stderr}")
        except FileNotFoundError:
            logger.warning("solc-select not found, using default solc version")
        except Exception as e:
            logger.warning(f"Error switching Solidity version: {str(e)}")

    @staticmethod
    def extract_pragma_version(source_code: str) -> Optional[str]:
        """
        Extract Solidity version from pragma statement in source code.

        Args:
            source_code: The Solidity source code

        Returns:
            Version string (e.g., "0.8.19") or None if not found
        """
        # Match patterns like: pragma solidity ^0.8.19;
        # or: pragma solidity >=0.8.0 <0.9.0;
        # or: pragma solidity 0.8.19;
        pattern = r'pragma\s+solidity\s+(?:\^|>=)?\s*(\d+\.\d+\.\d+)'
        match = re.search(pattern, source_code)

        if match:
            version = match.group(1)
            logger.info(f"Extracted pragma version: {version}")
            return version

        logger.warning("No pragma version found in source code")
        return None

    def switch_version(self, version: str) -> bool:
        """
        Switch to a specific Solidity version using solc-select.

        Args:
            version: Version to switch to (e.g., "0.8.19")

        Returns:
            True if successful, False otherwise
        """
        try:
            result = subprocess.run(
                ["solc-select", "use", version],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                logger.info(f"Successfully switched to Solidity {version}")
                self.version = version
                return True
            else:
                logger.warning(f"Failed to switch to Solidity {version}: {result.stderr}")
                return False
        except FileNotFoundError:
            logger.warning("solc-select not found")
            return False
        except Exception as e:
            logger.warning(f"Error switching Solidity version: {str(e)}")
            return False

    def check_installation(self) -> Tuple[bool, str]:
        """
        Check if solc is installed and accessible.

        Returns:
            Tuple of (success: bool, version or error message: str)
        """
        try:
            result = subprocess.run(
                [self.solc_path, "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                # Extract version from output
                version_line = result.stdout.split('\n')[0] if result.stdout else "Unknown"
                return True, version_line
            else:
                return False, result.stderr
        except FileNotFoundError:
            return False, "solc not found. Please install Solidity compiler."
        except Exception as e:
            return False, str(e)

    def compile_contract(
        self,
        contract_path: str,
        output_path: Optional[str] = None
    ) -> Tuple[int, Dict, str]:
        """
        Compile a Solidity contract using solc --combined-json.

        Args:
            contract_path: Path to the .sol file
            output_path: Optional path to save the compiled JSON output

        Returns:
            Tuple of (return_code: int, compiled_data: dict, error_message: str)
        """
        if not os.path.exists(contract_path):
            return 1, {}, f"Contract file not found: {contract_path}"

        try:
            # 确保使用指定版本的 Solidity 编译器
            logger.info(f"Switching to Solidity version: {self.version}")
            try:
                result = subprocess.run(
                    ["solc-select", "use", self.version],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    logger.info(f"✓ Successfully switched to Solidity {self.version}")
                    # 验证切换后的版本
                    verify_result = subprocess.run(
                        [self.solc_path, "--version"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if verify_result.returncode == 0:
                        lines = verify_result.stdout.split('\n')
                        actual_version = lines[1] if len(lines) > 1 else lines[0]
                        logger.info(f"✓ Verified solc version: {actual_version}")
                else:
                    logger.warning(f"✗ Failed to switch to Solidity {self.version}: {result.stderr}")
            except FileNotFoundError:
                logger.warning("✗ solc-select not found, using default solc version")
            except Exception as e:
                logger.warning(f"✗ Error switching Solidity version: {str(e)}")

            # Compile with combined-json output for ABI and bytecode
            cmd = [
                self.solc_path,
                contract_path,
                "--combined-json", "abi,bin,metadata"
            ]

            logger.info(f"Compiling contract: {contract_path}")
            logger.info(f"Command: {' '.join(cmd)}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=os.path.dirname(contract_path) or "."
            )

            # 只在出错时打印详细输出
            if result.returncode != 0:
                logger.error(f"✗ Compilation failed!")
                logger.error(f"Stderr: {result.stderr}")
                if result.stdout:
                    logger.error(f"Stdout: {result.stdout}")
                return result.returncode, {}, result.stderr

            logger.info("✓ Compilation successful")

            # Parse the JSON output
            try:
                compiled_data = json.loads(result.stdout)
            except json.JSONDecodeError as e:
                logger.error(f"✗ Failed to parse compiler output: {str(e)}")
                return 1, {}, f"Failed to parse compiler output: {str(e)}"

            # Optionally save to file
            if output_path:
                with open(output_path, 'w') as f:
                    json.dump(compiled_data, f, indent=2)
                logger.info(f"✓ Saved compiled output to: {output_path}")

            return 0, compiled_data, ""

        except subprocess.TimeoutExpired:
            logger.error("✗ Compilation timed out after 30 seconds")
            return 1, {}, "Compilation timed out after 30 seconds"
        except Exception as e:
            logger.error(f"✗ Compilation exception: {str(e)}")
            return 1, {}, f"Compilation failed: {str(e)}"

    def compile_from_source(
        self,
        source_code: str,
        contract_name: str = "Contract"
    ) -> Tuple[int, Dict, str]:
        """
        Compile Solidity source code from a string.

        Args:
            source_code: The Solidity source code as a string
            contract_name: Name for the temporary file (without .sol extension)

        Returns:
            Tuple of (return_code: int, compiled_data: dict, error_message: str)
        """
        # Create a temporary file for the source code
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.sol',
            delete=False,
            prefix=f"{contract_name}_"
        ) as tmp_file:
            tmp_file.write(source_code)
            tmp_path = tmp_file.name

        try:
            # Compile the temporary file
            return_code, compiled_data, error_msg = self.compile_contract(tmp_path)
            return return_code, compiled_data, error_msg
        finally:
            # Clean up temporary file
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def extract_contract_info(
        self,
        compiled_data: Dict,
        contract_key: Optional[str] = None
    ) -> Dict:
        """
        Extract ABI and bytecode from compiled data.

        Args:
            compiled_data: The JSON output from solc --combined-json
            contract_key: Specific contract key to extract (e.g., "Contract.sol:SimpleStorage")
                         If None, extracts the first contract found

        Returns:
            Dictionary with 'abi', 'bytecode', and 'contract_name' keys
        """
        contracts = compiled_data.get('contracts', {})

        if not contracts:
            return {}

        # If no specific contract key provided, get the first one
        if contract_key is None:
            contract_key = list(contracts.keys())[0]

        if contract_key not in contracts:
            available = ", ".join(contracts.keys())
            raise ValueError(
                f"Contract '{contract_key}' not found. Available: {available}"
            )

        contract = contracts[contract_key]

        # 检查 abi 的类型，避免解析错误
        abi = contract.get('abi', '[]')
        if isinstance(abi, str):
            try:
                abi = json.loads(abi)
            except:
                abi = []
        elif not isinstance(abi, list):
            abi = []

        return {
            'contract_name': contract_key,
            'abi': abi,
            'bytecode': contract.get('bin', ''),
            'metadata': contract.get('metadata', '')
        }
