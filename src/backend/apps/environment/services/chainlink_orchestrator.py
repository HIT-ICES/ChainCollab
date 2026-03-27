from __future__ import annotations

import json
import logging
import os
import subprocess
from pathlib import Path

import requests
from django.utils import timezone

from apps.environment.models import EthEnvironment
from apps.environment.services.chainlink_client import (
    auth_session as chainlink_auth_session,
    resolve_chainlink_credentials,
    resolve_chainlink_nodes,
    resolve_chainlink_root,
)
from apps.environment.services.task_runtime import (
    _append_task_log,
    _read_task_log_tail,
    _stream_process_output,
    _task_log_path,
)


class ChainlinkOrchestrator:
    def __init__(
        self,
        *,
        logger: logging.Logger,
        eth_system_account: str,
        set_task_step,
        resolve_system_rpc_url,
    ):
        self.log = logger
        self.eth_system_account = eth_system_account
        self.set_task_step = set_task_step
        self.resolve_system_rpc_url = resolve_system_rpc_url

    def resolve_chainlink_scripts(self) -> dict:
        chainlink_root = resolve_chainlink_root(Path(__file__))
        oracle_root = chainlink_root.parent / "04-dmn-ocr"
        return {
            "oracle_root": oracle_root,
            "chainlink_root": chainlink_root,
            "lite": oracle_root / "run-setup-lite.sh",
            "full": oracle_root / "run-setup.sh",
        }

    def resolve_chainlink_credentials(self) -> tuple[str, str]:
        scripts = self.resolve_chainlink_scripts()
        return resolve_chainlink_credentials(Path(scripts["chainlink_root"]))

    def resolve_chainlink_nodes(self) -> list[dict]:
        return resolve_chainlink_nodes(logger=self.log)

    def chainlink_auth_session(self, node_url: str) -> requests.Session:
        email, password = self.resolve_chainlink_credentials()
        return chainlink_auth_session(node_url, email=email, password=password, timeout=10)

    def sync_chainlink_cluster(
        self,
        env: EthEnvironment,
        persist: bool = True,
        include_jobs: bool = True,
    ) -> dict:
        nodes = self.resolve_chainlink_nodes()
        node_states = []
        healthy_count = 0

        for node in nodes:
            item = {
                "name": node["name"],
                "url": node["url"],
                "healthy": False,
                "job_count": 0,
                "job_ids": [],
                "error": None,
            }
            try:
                session = self.chainlink_auth_session(node["url"])
                jobs_resp = session.get(f"{node['url']}/v2/jobs", timeout=12)
                jobs_resp.raise_for_status()
                payload = jobs_resp.json()
                jobs = payload.get("data") if isinstance(payload, dict) else []
                if not isinstance(jobs, list):
                    jobs = []
                item["healthy"] = True
                item["job_count"] = len(jobs)
                if include_jobs:
                    item["job_ids"] = [
                        str(j.get("id")) for j in jobs if isinstance(j, dict) and j.get("id")
                    ]
                healthy_count += 1
            except Exception as exc:
                item["error"] = str(exc)
            node_states.append(item)

        snapshot = {
            "synced_at": timezone.now().isoformat(),
            "node_count": len(nodes),
            "healthy_count": healthy_count,
            "all_healthy": healthy_count == len(nodes) and len(nodes) > 0,
            "nodes": node_states,
        }

        if persist:
            detail = env.chainlink_detail or {}
            if not isinstance(detail, dict):
                detail = {}
            detail["cluster_sync"] = snapshot
            env.chainlink_detail = detail

            update_fields = ["chainlink_detail"]
            if env.chainlink_status != "SETTINGUP":
                next_status = env.chainlink_status
                if healthy_count > 0:
                    next_status = "STARTED"
                elif env.chainlink_status == "STARTED":
                    next_status = "FAILED"
                if next_status != env.chainlink_status:
                    env.chainlink_status = next_status
                    update_fields.append("chainlink_status")
            env.save(update_fields=update_fields)

        return snapshot

    def run_chainlink_setup(
        self,
        env_id: str,
        mode: str = "lite",
        task_id: str | None = None,
    ) -> dict:
        env = EthEnvironment.objects.get(pk=env_id)
        env.chainlink_status = "SETTINGUP"
        env.save(update_fields=["chainlink_status"])

        self.set_task_step(task_id, "RESOLVE_SCRIPT")
        log_path = _task_log_path(task_id) if task_id else None
        scripts = self.resolve_chainlink_scripts()
        script = scripts.get(mode) if mode in ["lite", "full"] else scripts["lite"]
        if not script.exists():
            env.chainlink_status = "FAILED"
            env.save(update_fields=["chainlink_status"])
            raise FileNotFoundError(f"Chainlink setup script not found: {script}")

        env_vars = {
            "ORACLE_ROOT": str(scripts["oracle_root"]),
            "CHAINLINK_ROOT": str(scripts["chainlink_root"]),
            "DEPLOYER_ACCOUNT": str(self.eth_system_account),
        }
        try:
            env_vars["RPC_URL"] = self.resolve_system_rpc_url(env)
        except Exception as exc:
            self.log.warning("Chainlink action=resolve_rpc_failed env=%s error=%s", env_id, exc)
        if mode == "lite":
            env_vars["DMN_MODE"] = "lite"

        self.log.info(
            "Chainlink action=setup_start env=%s mode=%s script=%s",
            env_id,
            mode,
            script,
        )
        try:
            self.set_task_step(task_id, "RUN_SCRIPT")
            process = subprocess.Popen(
                ["bash", str(script)],
                cwd=str(scripts["chainlink_root"]),
                env={
                    **os.environ,
                    **env_vars,
                    "LANG": "C.UTF-8",
                    "LC_ALL": "C.UTF-8",
                    "PYTHONIOENCODING": "UTF-8",
                },
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
            if log_path:
                _append_task_log(log_path, f"run: bash {script}")
            _stream_process_output(process, log_path)
            returncode = process.wait()
            if returncode != 0:
                self.log.warning("Chainlink script exited with code=%s", returncode)
        except Exception:
            env.chainlink_status = "FAILED"
            env.save(update_fields=["chainlink_status"])
            raise

        if returncode != 0:
            env.chainlink_status = "FAILED"
            env.save(update_fields=["chainlink_status"])
            raise RuntimeError(
                f"Chainlink setup failed (code={returncode}). "
                f"See task log: {log_path}"
            )

        self.set_task_step(task_id, "PROCESS_RESULT")
        payload = {
            "mode": mode,
            "script": str(script),
            "returncode": returncode,
            "log_tail": _read_task_log_tail(log_path) if log_path else "",
        }

        self.set_task_step(task_id, "UPDATE_STATUS")
        env.chainlink_status = "STARTED"
        try:
            payload_detail = self.load_chainlink_deployments()
            chainlink = payload_detail.get("chainlink_deployment") or {}
            dmn = payload_detail.get("dmn_deployment") or {}
            previous_chainlink = env.chainlink_detail or {}
            merged_chainlink = {**previous_chainlink, **chainlink} if chainlink else previous_chainlink
            env.chainlink_detail = merged_chainlink or None
            env.dmn_detail = dmn or None
            env.save(update_fields=["chainlink_status", "chainlink_detail", "dmn_detail"])
        except Exception:
            env.save(update_fields=["chainlink_status"])
            self.log.exception("Chainlink action=store_deployment_failed env=%s", env_id)
        return payload

    def run_chainlink_create_job(
        self,
        env_id: str,
        recreate: bool = False,
        external_job_id: str | None = None,
        sync_onchain: bool = True,
        job_kind: str = "dmn",
        data_source_url: str | None = None,
        data_source_method: str = "GET",
        task_id: str | None = None,
    ) -> dict:
        env = EthEnvironment.objects.get(pk=env_id)
        if env.chainlink_status != "STARTED":
            raise RuntimeError("Chainlink is not started, install chainlink first")
        normalized_kind = (
            "datasource"
            if str(job_kind or "").lower() in ["datasource", "data_source", "source"]
            else "dmn"
        )

        self.set_task_step(task_id, "RESOLVE_SCRIPT")
        log_path = _task_log_path(task_id) if task_id else None
        scripts = self.resolve_chainlink_scripts()
        chainlink_root = Path(scripts["chainlink_root"])
        oracle_root = Path(scripts["oracle_root"])
        create_job_script = oracle_root / "create-dmn-directrequest-job.js"
        set_job_script = oracle_root / "set-dmn-job-id.js"
        if not create_job_script.exists():
            raise FileNotFoundError(f"Chainlink create job script not found: {create_job_script}")

        env_vars = {
            "ORACLE_ROOT": str(oracle_root),
            "CHAINLINK_ROOT": str(chainlink_root),
            "CHAINLINK_TASK_KIND": normalized_kind,
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PYTHONIOENCODING": "UTF-8",
        }
        if recreate:
            env_vars["RECREATE_JOB"] = "1"
        if external_job_id:
            env_vars["EXTERNAL_JOB_ID"] = str(external_job_id)
        contract_addr = (env.dmn_detail or {}).get("contractAddress")
        if contract_addr:
            env_vars["DMN_REQUEST_CONTRACT_ADDRESS"] = str(contract_addr)
        if normalized_kind == "datasource" and data_source_url:
            env_vars["DATA_SOURCE_URL"] = str(data_source_url)
        if normalized_kind == "datasource":
            env_vars["DATA_SOURCE_HTTP_METHOD"] = str(data_source_method or "GET").upper()
        try:
            env_vars["RPC_URL"] = self.resolve_system_rpc_url(env)
        except Exception as exc:
            self.log.warning(
                "Chainlink action=create_job_resolve_rpc_failed env=%s error=%s", env_id, exc
            )

        if log_path:
            _append_task_log(log_path, f"run: node {create_job_script}")

        self.set_task_step(task_id, "CREATE_JOB")
        process = subprocess.Popen(
            ["node", str(create_job_script)],
            cwd=str(chainlink_root),
            env={**os.environ, **env_vars},
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        _stream_process_output(process, log_path)
        returncode = process.wait()
        if returncode != 0:
            raise RuntimeError(
                f"Chainlink create job failed (code={returncode}). "
                f"See task log: {log_path}"
            )

        created_job_id = None
        try:
            deployment_data = self.load_chainlink_deployments().get("chainlink_deployment") or {}
            if normalized_kind == "datasource":
                created_job_id = (
                    deployment_data.get("datasourceJobId")
                    or deployment_data.get("dataSourceJobId")
                    or (deployment_data.get("datasourceJobIds") or {}).get("chainlink1")
                    or (deployment_data.get("dataSourceJobIds") or {}).get("chainlink1")
                )
            else:
                created_job_id = deployment_data.get("dmnJobId") or (
                    deployment_data.get("dmnJobIds") or {}
                ).get("chainlink1")
        except Exception as exc:
            self.log.warning(
                "Chainlink action=resolve_created_job_failed env=%s error=%s", env_id, exc
            )

        if sync_onchain:
            if not set_job_script.exists():
                raise FileNotFoundError(f"setJobId script not found: {set_job_script}")
            if normalized_kind == "datasource" and not created_job_id:
                raise RuntimeError("Datasource job created but jobId not found in deployment file")
            if log_path:
                _append_task_log(log_path, f"run: node {set_job_script}")
            self.set_task_step(task_id, "SET_JOB_ID")
            set_job_env = {**os.environ, **env_vars, "DMN_MODE": os.environ.get("DMN_MODE", "lite")}
            if created_job_id:
                set_job_env["DMN_JOB_ID"] = str(created_job_id)
            set_process = subprocess.Popen(
                ["node", str(set_job_script)],
                cwd=str(chainlink_root),
                env=set_job_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
            )
            _stream_process_output(set_process, log_path)
            set_returncode = set_process.wait()
            if set_returncode != 0:
                raise RuntimeError(
                    f"Chainlink setJobId failed (code={set_returncode}). "
                    f"See task log: {log_path}"
                )

        self.set_task_step(task_id, "PROCESS_RESULT")
        payload_detail = self.load_chainlink_deployments()
        chainlink = payload_detail.get("chainlink_deployment") or {}
        dmn = payload_detail.get("dmn_deployment") or {}
        previous_chainlink = env.chainlink_detail or {}
        merged_chainlink = {**previous_chainlink, **chainlink} if chainlink else previous_chainlink
        update_fields = ["chainlink_detail"]
        env.chainlink_detail = merged_chainlink or None
        if dmn:
            env.dmn_detail = dmn
            update_fields.append("dmn_detail")
        env.save(update_fields=update_fields)

        return {
            "job_kind": normalized_kind,
            "recreate": recreate,
            "sync_onchain": sync_onchain,
            "external_job_id": external_job_id,
            "data_source_url": data_source_url,
            "data_source_method": str(data_source_method or "GET").upper(),
            "created_job_id": created_job_id,
            "chainlink_detail": env.chainlink_detail,
            "dmn_detail": env.dmn_detail,
            "log_tail": _read_task_log_tail(log_path) if log_path else "",
        }

    def redeploy_dmn_contract(
        self,
        env_id: str,
        contract_name: str,
        task_id: str | None = None,
    ) -> dict:
        env = EthEnvironment.objects.get(pk=env_id)
        if env.chainlink_status != "STARTED":
            raise RuntimeError("Chainlink is not started, install chainlink first")

        self.set_task_step(task_id, "RESOLVE_SCRIPT")
        log_path = _task_log_path(task_id) if task_id else None
        scripts = self.resolve_chainlink_scripts()
        chainlink_root = Path(scripts["chainlink_root"])
        deploy_script = chainlink_root / "scripts" / "deploy-contract.js"
        if not deploy_script.exists():
            raise FileNotFoundError(f"DMN deploy script not found: {deploy_script}")

        env_vars = {
            "ORACLE_ROOT": str(scripts["oracle_root"]),
            "CHAINLINK_ROOT": str(chainlink_root),
            "DEPLOYER_ACCOUNT": str(self.eth_system_account),
            "FORCE_DMN_CONTRACT": "1",
            "DMN_CONTRACT_NAME": contract_name,
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PYTHONIOENCODING": "UTF-8",
        }
        try:
            env_vars["RPC_URL"] = self.resolve_system_rpc_url(env)
        except Exception as exc:
            self.log.warning(
                "Chainlink action=redeploy_dmn_resolve_rpc_failed env=%s error=%s",
                env_id,
                exc,
            )

        self.log.info(
            "Chainlink action=redeploy_dmn_start env=%s contract=%s script=%s",
            env_id,
            contract_name,
            deploy_script,
        )
        self.set_task_step(task_id, "RUN_SCRIPT")
        if log_path:
            _append_task_log(log_path, f"run: node {deploy_script}")
        process = subprocess.Popen(
            ["node", str(deploy_script)],
            cwd=str(chainlink_root),
            env={**os.environ, **env_vars},
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        _stream_process_output(process, log_path)
        returncode = process.wait()
        if returncode != 0:
            raise RuntimeError(
                f"DMN contract redeploy failed (code={returncode}). "
                f"See task log: {log_path}"
            )

        self.set_task_step(task_id, "PROCESS_RESULT")
        payload_detail = self.load_chainlink_deployments()
        chainlink = payload_detail.get("chainlink_deployment") or {}
        dmn = payload_detail.get("dmn_deployment") or {}
        previous_chainlink = env.chainlink_detail or {}
        if not isinstance(previous_chainlink, dict):
            previous_chainlink = {}
        merged_chainlink = {**previous_chainlink, **chainlink} if chainlink else previous_chainlink
        env.chainlink_detail = merged_chainlink or None
        env.dmn_detail = dmn or None
        env.save(update_fields=["chainlink_detail", "dmn_detail"])
        return {
            "contract_name": contract_name,
            "chainlink_detail": env.chainlink_detail,
            "dmn_detail": env.dmn_detail,
            "log_tail": _read_task_log_tail(log_path) if log_path else "",
        }

    def run_oracle_task_suite_setup(
        self,
        env_id: str,
        task_id: str | None = None,
    ) -> dict:
        env = EthEnvironment.objects.get(pk=env_id)
        if env.chainlink_status != "STARTED":
            raise RuntimeError("Chainlink is not started, install chainlink first")

        self.set_task_step(task_id, "RESOLVE_SCRIPT")
        log_path = _task_log_path(task_id) if task_id else None
        scripts = self.resolve_chainlink_scripts()
        chainlink_root = Path(scripts["chainlink_root"])
        deploy_script = chainlink_root / "scripts" / "deploy-oracle-task-suite.js"
        if not deploy_script.exists():
            raise FileNotFoundError(
                f"Oracle task suite deploy script not found: {deploy_script}"
            )

        env_vars = {
            "ORACLE_ROOT": str(scripts["oracle_root"]),
            "CHAINLINK_ROOT": str(chainlink_root),
            "DEPLOYER_ACCOUNT": str(self.eth_system_account),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PYTHONIOENCODING": "UTF-8",
        }
        try:
            env_vars["RPC_URL"] = self.resolve_system_rpc_url(env)
        except Exception as exc:
            self.log.warning(
                "Chainlink action=oracle_task_suite_resolve_rpc_failed env=%s error=%s",
                env_id,
                exc,
            )

        self.set_task_step(task_id, "DEPLOY_SUITE")
        if log_path:
            _append_task_log(log_path, f"run: node {deploy_script}")
        process = subprocess.Popen(
            ["node", str(deploy_script)],
            cwd=str(chainlink_root),
            env={**os.environ, **env_vars},
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        _stream_process_output(process, log_path)
        returncode = process.wait()
        if returncode != 0:
            raise RuntimeError(
                f"Oracle task suite setup failed (code={returncode}). "
                f"See task log: {log_path}"
            )

        self.set_task_step(task_id, "PROCESS_RESULT")
        payload_detail = self.load_chainlink_deployments()
        suite = payload_detail.get("oracle_task_suite") or {}
        previous_chainlink = env.chainlink_detail or {}
        if not isinstance(previous_chainlink, dict):
            previous_chainlink = {}
        merged_chainlink = {
            **previous_chainlink,
            "oracle_task_suite": suite,
        }
        env.chainlink_detail = merged_chainlink
        env.save(update_fields=["chainlink_detail"])

        return {
            "oracle_task_suite": suite,
            "log_tail": _read_task_log_tail(log_path) if log_path else "",
        }

    def relayer_node_url(self) -> str:
        return str(os.environ.get("RELAYER_NODE_URL", "http://127.0.0.1:8082")).rstrip("/")

    def relayer_node_ui_url(self) -> str:
        value = os.environ.get("RELAYER_NODE_UI")
        if value:
            return str(value).rstrip("/")
        return self.relayer_node_url()

    def relayer_node_status(self) -> dict:
        base_url = self.relayer_node_url()
        status_payload = {
            "node_url": base_url,
            "ui_url": self.relayer_node_ui_url(),
            "reachable": False,
            "healthy": False,
            "running": False,
            "error": None,
        }
        try:
            health = requests.get(f"{base_url}/health", timeout=6)
            status_payload["reachable"] = health.status_code == 200
            status_payload["healthy"] = (
                health.status_code == 200 and (health.json() or {}).get("status") == "ok"
            )
        except Exception as exc:
            status_payload["error"] = str(exc)
            return status_payload

        try:
            control = requests.get(f"{base_url}/control/status", timeout=6)
            if control.status_code == 200:
                payload = control.json() or {}
                status_payload["running"] = bool(payload.get("running"))
        except Exception as exc:
            status_payload["error"] = str(exc)
        return status_payload

    def control_relayer_node(self, action: str) -> dict:
        command = str(action or "").lower().strip()
        if command not in ["start", "stop"]:
            raise ValueError("action must be start or stop")

        base_url = self.relayer_node_url()
        response = requests.post(f"{base_url}/control/{command}", timeout=8)
        response.raise_for_status()
        payload = response.json() if response.content else {}
        status_payload = self.relayer_node_status()
        return {
            "action": command,
            "result": payload,
            "status": status_payload,
        }

    def run_relayer_adapter_setup(
        self,
        env_id: str,
        task_id: str | None = None,
    ) -> dict:
        env = EthEnvironment.objects.get(pk=env_id)
        if env.chainlink_status != "STARTED":
            raise RuntimeError("Chainlink is not started, install chainlink first")

        self.set_task_step(task_id, "RESOLVE_SCRIPT")
        log_path = _task_log_path(task_id) if task_id else None
        scripts = self.resolve_chainlink_scripts()
        chainlink_root = Path(scripts["chainlink_root"])
        deploy_script = chainlink_root / "scripts" / "deploy-relayer-adapter.js"
        if not deploy_script.exists():
            raise FileNotFoundError(
                f"Relayer adapter deploy script not found: {deploy_script}"
            )

        env_vars = {
            "CHAINLINK_ROOT": str(chainlink_root),
            "DEPLOYER_ACCOUNT": str(self.eth_system_account),
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PYTHONIOENCODING": "UTF-8",
        }
        if os.environ.get("RELAYER_SIGNERS"):
            env_vars["RELAYER_SIGNERS"] = os.environ["RELAYER_SIGNERS"]
        if os.environ.get("RELAYER_THRESHOLD"):
            env_vars["RELAYER_THRESHOLD"] = os.environ["RELAYER_THRESHOLD"]
        try:
            env_vars["RPC_URL"] = self.resolve_system_rpc_url(env)
        except Exception as exc:
            self.log.warning(
                "Chainlink action=relayer_setup_resolve_rpc_failed env=%s error=%s",
                env_id,
                exc,
            )

        self.set_task_step(task_id, "DEPLOY_RELAYER_ADAPTER")
        if log_path:
            _append_task_log(log_path, f"run: node {deploy_script}")
        process = subprocess.Popen(
            ["node", str(deploy_script)],
            cwd=str(chainlink_root),
            env={**os.environ, **env_vars},
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        _stream_process_output(process, log_path)
        returncode = process.wait()
        if returncode != 0:
            raise RuntimeError(
                f"Relayer adapter setup failed (code={returncode}). "
                f"See task log: {log_path}"
            )

        self.set_task_step(task_id, "PROCESS_RESULT")
        payload_detail = self.load_chainlink_deployments()
        relayer = payload_detail.get("relayer_deployment") or {}
        previous_chainlink = env.chainlink_detail or {}
        if not isinstance(previous_chainlink, dict):
            previous_chainlink = {}
        merged_chainlink = {
            **previous_chainlink,
            "relayer": relayer,
        }
        env.chainlink_detail = merged_chainlink
        env.save(update_fields=["chainlink_detail"])

        return {
            "relayer": relayer,
            "node_status": self.relayer_node_status(),
            "log_tail": _read_task_log_tail(log_path) if log_path else "",
        }

    def load_chainlink_deployments(self) -> dict:
        scripts = self.resolve_chainlink_scripts()
        chainlink_root = Path(scripts["chainlink_root"])
        deployment_dir = chainlink_root / "deployment"
        chainlink_deploy = deployment_dir / "chainlink-deployment.json"
        dmn_deploy = deployment_dir / "deployment.json"
        oracle_task_suite = deployment_dir / "oracle-task-suite.json"
        relayer_deploy = deployment_dir / "relayer-adapter.json"
        compiled = deployment_dir / "compiled.json"

        def _load_json(path: Path):
            if path.exists():
                return json.loads(path.read_text())
            return None

        return {
            "chainlink_root": str(chainlink_root),
            "deployment_dir": str(deployment_dir),
            "chainlink_deployment": _load_json(chainlink_deploy),
            "dmn_deployment": _load_json(dmn_deploy),
            "oracle_task_suite": _load_json(oracle_task_suite),
            "relayer_deployment": _load_json(relayer_deploy),
            "compiled": _load_json(compiled),
        }
