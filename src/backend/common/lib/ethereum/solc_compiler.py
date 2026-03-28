#
# SPDX-License-Identifier: Apache-2.0
#
import os
import json
import subprocess
import tempfile
import logging
import re
import stat
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
        self.evm_version = os.environ.get("SOLC_EVM_VERSION", "paris")
        optimize_env = os.environ.get("SOLC_OPTIMIZE", "true").strip().lower()
        self.optimize = optimize_env not in {"0", "false", "no", "off"}
        try:
            self.optimize_runs = int(os.environ.get("SOLC_OPTIMIZE_RUNS", "1"))
        except ValueError:
            self.optimize_runs = 1

        preferred_versions = [os.environ.get("SOLC_VERSION"), self.version]
        if self._ensure_local_solc_selected(preferred_versions):
            logger.info(f"Using local Solidity compiler version {self.version}")
        else:
            logger.warning(
                "Requested Solidity version is not installed locally; "
                "Docker fallback will be used when needed"
            )

    @staticmethod
    def _parse_versions(output: str) -> list[str]:
        versions: list[str] = []
        for line in output.splitlines():
            match = re.search(r"(\d+\.\d+\.\d+)", line)
            if match:
                versions.append(match.group(1))
        return versions

    def _installed_solc_versions(self) -> list[str]:
        try:
            result = subprocess.run(
                ["solc-select", "versions"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                return []
            return self._parse_versions(result.stdout)
        except FileNotFoundError:
            return []
        except Exception as e:
            logger.warning(f"Failed to list installed solc versions: {str(e)}")
            return []

    def _ensure_local_solc_selected(self, preferred_versions: list[str]) -> bool:
        installed_versions = self._installed_solc_versions()
        candidates = []
        for version in preferred_versions:
            if version and version not in candidates:
                candidates.append(version)
        for version in installed_versions:
            if version not in candidates:
                candidates.append(version)

        for version in candidates:
            if version not in installed_versions:
                continue
            try:
                result = subprocess.run(
                    ["solc-select", "use", version],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode != 0:
                    continue
                self.version = version
                artifact = os.path.expanduser(
                    f"~/.solc-select/artifacts/solc-{version}/solc-{version}"
                )
                if os.path.exists(artifact):
                    try:
                        mode = os.stat(artifact).st_mode
                        if not (mode & stat.S_IXUSR):
                            os.chmod(
                                artifact,
                                mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH,
                            )
                    except Exception as chmod_error:
                        logger.warning(
                            f"Failed to adjust solc artifact permissions for {version}: {chmod_error}"
                        )
                verify = subprocess.run(
                    [self.solc_path, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if verify.returncode == 0:
                    return True
            except FileNotFoundError:
                return False
            except Exception as e:
                logger.warning(f"Failed to activate local solc {version}: {str(e)}")
        return False

    def _run_docker_solc(self, contract_path: str):
        workdir = os.path.abspath(os.path.dirname(contract_path) or ".")
        filename = os.path.basename(contract_path)
        last_result = None
        last_error = None
        for image in self._docker_image_candidates():
            cmd = [
                "docker",
                "run",
                "--rm",
                "-v",
                f"{workdir}:/workspace",
                "-w",
                "/workspace",
                image,
                filename,
                "--evm-version",
                self.evm_version,
                "--combined-json",
                "abi,bin,metadata",
            ]
            if self.optimize:
                cmd.extend(
                    [
                        "--optimize",
                        "--optimize-runs",
                        str(self.optimize_runs),
                    ]
                )
            logger.info(f"Falling back to docker solc: {' '.join(cmd)}")
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                last_result = result
                if result.returncode == 0:
                    return result
                logger.warning(
                    "Docker solc image %s failed: %s",
                    image,
                    result.stderr or result.stdout,
                )
            except Exception as exc:
                last_error = exc
                logger.warning(f"Docker solc image {image} failed: {exc}")
        if last_result is not None:
            return last_result
        raise last_error or RuntimeError("docker solc unavailable")

    def _docker_image_candidates(self) -> list[str]:
        candidates: list[str] = []
        env_image = os.environ.get("SOLC_DOCKER_IMAGE")
        if env_image:
            candidates.append(env_image)
        if self.version:
            candidates.append(f"ethereum/solc:{self.version}")
        candidates.append("ethereum/solc:stable")
        deduped: list[str] = []
        for candidate in candidates:
            if candidate and candidate not in deduped:
                deduped.append(candidate)
        return deduped

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
        if version not in self._installed_solc_versions():
            logger.warning(f"Solidity {version} is not installed")
            return False
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
        preferred_versions = [self.version]
        env_version = os.environ.get("SOLC_VERSION")
        if env_version:
            preferred_versions.insert(0, env_version)
        if self._ensure_local_solc_selected(preferred_versions):
            try:
                result = subprocess.run(
                    [self.solc_path, "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                if result.returncode == 0:
                    version_line = result.stdout.split("\n")[0] if result.stdout else "Unknown"
                    return True, version_line
            except Exception as e:
                logger.warning(f"Local solc version check failed: {str(e)}")
        try:
            docker_errors = []
            for image in self._docker_image_candidates():
                result = subprocess.run(
                    [
                        "docker",
                        "run",
                        "--rm",
                        image,
                        "--version",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if result.returncode == 0:
                    version_line = result.stdout.split("\n")[0] if result.stdout else image
                    return True, f"docker:{version_line}"
                docker_errors.append(result.stderr or result.stdout or image)
            return False, "; ".join([msg for msg in docker_errors if msg]) or "docker solc unavailable"
        except FileNotFoundError:
            return False, "solc not found and docker fallback is unavailable"
        except subprocess.TimeoutExpired:
            return False, "solc and docker fallback timed out"
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

        preferred_versions = [self.version]
        env_version = os.environ.get("SOLC_VERSION")
        if env_version:
            preferred_versions.insert(0, env_version)
        source_version = None
        try:
            with open(contract_path, "r") as source_file:
                source_version = self.extract_pragma_version(source_file.read())
        except Exception:
            source_version = None
        if source_version and source_version not in preferred_versions:
            preferred_versions.insert(0, source_version)

        try:
            # 确保使用指定版本的 Solidity 编译器
            logger.info(
                "Switching to Solidity version candidates: %s",
                ", ".join([v for v in preferred_versions if v]),
            )
            local_solc_ready = self._ensure_local_solc_selected(preferred_versions)

            # Compile with combined-json output for ABI and bytecode
            cmd = [
                self.solc_path,
                contract_path,
                "--evm-version",
                self.evm_version,
                "--combined-json", "abi,bin,metadata"
            ]
            if self.optimize:
                cmd.extend(
                    [
                        "--optimize",
                        "--optimize-runs",
                        str(self.optimize_runs),
                    ]
                )

            logger.info(f"Compiling contract: {contract_path}")
            logger.info(f"Command: {' '.join(cmd)}")
            logger.info(
                "Solidity optimizer enabled=%s runs=%s",
                self.optimize,
                self.optimize_runs,
            )

            result = None
            compile_errors = []
            if local_solc_ready:
                try:
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        timeout=60,
                        cwd=os.path.dirname(contract_path) or "."
                    )
                except PermissionError as exc:
                    compile_errors.append(str(exc))
                    logger.warning(f"Local solc permission error: {exc}")
                except subprocess.TimeoutExpired as exc:
                    compile_errors.append("local solc timed out")
                    logger.warning("Local solc compilation timed out")
                except Exception as exc:
                    compile_errors.append(str(exc))
                    logger.warning(f"Local solc compile failed: {exc}")

            if result is None or result.returncode != 0:
                if result is not None and result.returncode != 0:
                    compile_errors.append(result.stderr or "local solc returned non-zero")
                try:
                    result = self._run_docker_solc(contract_path)
                except Exception as exc:
                    compile_errors.append(f"docker fallback failed: {exc}")
                    return 1, {}, "; ".join([err for err in compile_errors if err])

            # 只在出错时打印详细输出
            if result.returncode != 0:
                logger.error(f"✗ Compilation failed!")
                logger.error(f"Stderr: {result.stderr}")
                if result.stdout:
                    logger.error(f"Stdout: {result.stdout}")
                return result.returncode, {}, result.stderr or "; ".join(compile_errors)

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
