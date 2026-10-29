from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from datetime import datetime
import asyncio
import json
import re
import sys
from pathlib import Path
import uvicorn
from pydantic import BaseModel
from typing import Dict, Any, Optional
from fastapi.middleware.cors import CORSMiddleware
from textx import metamodel_from_file

if __package__ in (None, ""):
    _CURRENT_DIR = Path(__file__).resolve().parent
    _PACKAGE_ROOT = _CURRENT_DIR.parent
    if str(_PACKAGE_ROOT) not in sys.path:
        sys.path.insert(0, str(_PACKAGE_ROOT))
    from generator.translator import GoChaincodeTranslator, SolidityContractTranslator  # type: ignore
    from generator.parser.dmn_parser.parser import DMNParser  # type: ignore
    from generator.parser.choreography_parser.parser import Choreography  # type: ignore
    from generator.parser.choreography_parser.elements import NodeType  # type: ignore
    _CODEGEN_ROOT = _PACKAGE_ROOT / "CodeGenerator"
else:
    from ..generator.translator import GoChaincodeTranslator, SolidityContractTranslator
    from ..generator.parser.dmn_parser.parser import DMNParser
    from ..generator.parser.choreography_parser.parser import Choreography
    from ..generator.parser.choreography_parser.elements import NodeType
    _PACKAGE_ROOT = Path(__file__).resolve().parent.parent
    _CODEGEN_ROOT = _PACKAGE_ROOT / "CodeGenerator"

_GO_CODEGEN_ROOT = _CODEGEN_ROOT / "b2cdsl-go"
_SOL_CODEGEN_ROOT = _CODEGEN_ROOT / "b2cdsl-solidity"
for _path in (_GO_CODEGEN_ROOT, _SOL_CODEGEN_ROOT):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from b2cdsl_go import DSLContractAdapter as GoDSLContractAdapter, GoChaincodeRenderer, TEMPLATE_ENV as GO_TEMPLATE_ENV, CONTRACT_TEMPLATE as GO_CONTRACT_TEMPLATE
from b2cdsl_solidity import DSLContractAdapter as SolidityDSLContractAdapter, SolidityRenderer, TEMPLATE_ENV as SOL_TEMPLATE_ENV, CONTRACT_TEMPLATE as SOL_CONTRACT_TEMPLATE

_B2C_METAMODEL = None
_RUNTIME_TRANSLATOR_DIR = _PACKAGE_ROOT.parent / "runtime" / "newTranslator"


def _load_b2c_metamodel():
    global _B2C_METAMODEL
    if _B2C_METAMODEL is None:
        grammar_path = _PACKAGE_ROOT / "DSL" / "B2CDSL" / "b2cdsl" / "b2c.tx"
        _B2C_METAMODEL = metamodel_from_file(str(grammar_path))
    return _B2C_METAMODEL


def _safe_artifact_name(name: Optional[str], fallback: str) -> str:
    candidate = (name or "").strip() or fallback
    sanitized = re.sub(r"[^A-Za-z0-9_.-]+", "_", candidate).strip("._")
    return sanitized or fallback


def _persist_runtime_artifacts(
    *,
    target: str,
    artifact_name: Optional[str],
    dsl_content: str = "",
    contract_content: str = "",
    ffi_content: str = "",
) -> Dict[str, str]:
    timestamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S-%f")
    safe_name = _safe_artifact_name(artifact_name, f"{target}-artifact")
    output_dir = _RUNTIME_TRANSLATOR_DIR / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)

    written: Dict[str, str] = {}
    if dsl_content:
        dsl_path = output_dir / f"{safe_name}.b2c"
        dsl_path.write_text(dsl_content, encoding="utf-8")
        written["dslPath"] = str(dsl_path)
    if contract_content:
        suffix = ".sol" if target == "solidity" else ".go"
        contract_path = output_dir / f"{safe_name}{suffix}"
        contract_path.write_text(contract_content, encoding="utf-8")
        written["artifactPath"] = str(contract_path)
    if ffi_content:
        ffi_path = output_dir / f"{safe_name}.ffi.json"
        ffi_path.write_text(ffi_content, encoding="utf-8")
        written["ffiPath"] = str(ffi_path)
    written["outputDir"] = str(output_dir)
    return written

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChaincodeGenerateParams(BaseModel):
    bpmnContent: str
    artifactName: Optional[str] = None
    persist_to_runtime: bool = False


class ChaincodeGenerateResponse(BaseModel):
    bpmnContent: str
    ffiContent: str
    timecost: str = None
    outputDir: Optional[str] = None
    artifactPath: Optional[str] = None
    dslPath: Optional[str] = None
    ffiPath: Optional[str] = None


@app.post("/api/v1/chaincode/generate")
async def generate_chaincode(params: ChaincodeGenerateParams):
    translator: GoChaincodeTranslator = GoChaincodeTranslator(params.bpmnContent)
    chaincode = translator.generate_chaincode(contract_name=params.artifactName)
    ffi = translator.generate_ffi()
    persist_result = {}
    if params.persist_to_runtime:
        persist_result = _persist_runtime_artifacts(
            target="go",
            artifact_name=params.artifactName,
            dsl_content=chaincode,
            ffi_content=ffi,
        )
    return ChaincodeGenerateResponse(
        bpmnContent=chaincode,
        ffiContent=ffi,
        outputDir=persist_result.get("outputDir"),
        artifactPath=persist_result.get("artifactPath"),
        dslPath=persist_result.get("dslPath"),
        ffiPath=persist_result.get("ffiPath"),
    )


class EthContractGenerateParams(BaseModel):
    bpmnContent: str
    artifactName: Optional[str] = None
    persist_to_runtime: bool = False


class EthContractGenerateResponse(BaseModel):
    contractContent: str
    dslContent: str
    ffiContent: str
    outputDir: Optional[str] = None
    artifactPath: Optional[str] = None
    dslPath: Optional[str] = None
    ffiPath: Optional[str] = None
    executionLayout: Dict[str, Any] = {}


@app.post("/api/v1/chaincode/generate-eth")
async def generate_eth_contract(params: EthContractGenerateParams):
    translator = SolidityContractTranslator(params.bpmnContent)
    try:
        contract_content, dsl_content, execution_layout = translator.generate_contract_bundle(
            contract_name=params.artifactName
        )
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"message": str(exc)})
    ffi_content = translator.generate_ffi()
    persist_result = {}
    if params.persist_to_runtime:
        persist_result = _persist_runtime_artifacts(
            target="solidity",
            artifact_name=params.artifactName,
            dsl_content=dsl_content,
            contract_content=contract_content,
            ffi_content=ffi_content,
        )
    return EthContractGenerateResponse(
        contractContent=contract_content,
        dslContent=dsl_content,
        ffiContent=ffi_content,
        outputDir=persist_result.get("outputDir"),
        artifactPath=persist_result.get("artifactPath"),
        dslPath=persist_result.get("dslPath"),
        ffiPath=persist_result.get("ffiPath"),
        executionLayout=execution_layout,
    )


class ChaincodeCompileParams(BaseModel):
    dslContent: str
    target: str = "go"


class ChaincodeCompileResponse(BaseModel):
    chaincodeContent: str
    ffiContent: str
    target: str


@app.post("/api/v1/chaincode/compile")
async def compile_chaincode(params: ChaincodeCompileParams):
    metamodel = _load_b2c_metamodel()
    model = metamodel.model_from_str(params.dslContent)
    if not getattr(model, "contracts", None):
        return JSONResponse(status_code=400, content={"message": "No contracts defined in DSL."})
    contract = model.contracts[0]

    if params.target.lower() == "solidity":
        adapter = SolidityDSLContractAdapter(contract)
        renderer = SolidityRenderer(adapter)
        context = renderer.build_context()
        template = SOL_TEMPLATE_ENV.get_template(SOL_CONTRACT_TEMPLATE)
        rendered = template.render(**context).strip() + "\n"
        return ChaincodeCompileResponse(chaincodeContent=rendered, ffiContent="{}", target="solidity")

    adapter = GoDSLContractAdapter(contract)
    renderer = GoChaincodeRenderer(adapter, GO_TEMPLATE_ENV)
    context = renderer.build_context()
    template = GO_TEMPLATE_ENV.get_template(GO_CONTRACT_TEMPLATE)
    rendered = template.render(**context).strip() + "\n"
    return ChaincodeCompileResponse(chaincodeContent=rendered, ffiContent="{}", target="go")


class ChaincodePartParams(BaseModel):
    bpmnContent: str


class ChaincodePartResponse(BaseModel):
    data: Dict[str, Any]


@app.api_route("/api/v1/chaincode/getPartByBpmnC", methods=["POST"])
async def get_participant_by_bpmn_content(bpmn: ChaincodePartParams):
    translator: GoChaincodeTranslator = GoChaincodeTranslator(bpmn.bpmnContent)
    print(translator.get_participants())
    return JSONResponse(content=translator.get_participants())


@app.api_route("/api/v1/chaincode/getMessagesByBpmnC", methods=["POST"])
async def get_participant_by_bpmn_content(bpmn: ChaincodePartParams):
    translator: GoChaincodeTranslator = GoChaincodeTranslator(bpmn.bpmnContent)
    messages = translator.get_messages()
    # print(messages)
    return JSONResponse(content=translator.get_messages())


@app.api_route("/api/v1/chaincode/getBusinessRulesByBpmnC", methods=["POST"])
async def get_businessRules_by_bpmn_content(bpmn: ChaincodePartParams):
    translator: GoChaincodeTranslator = GoChaincodeTranslator(bpmn.bpmnContent)
    return JSONResponse(content=translator.get_businessrules())


@app.get("/api/v1/ffi/generate")
async def generate_ffi():
    translator = GoChaincodeTranslator()
    return JSONResponse(content={"message": "Hello, world! (async)"})


class GetDecisionsParams(BaseModel):
    dmnContent: str


# 1. return all decisionID， and mark the main one
@app.post("/api/v1/chaincode/getDecisions")
async def get_decisions(params: GetDecisionsParams):
    parser: DMNParser = DMNParser(params.dmnContent)
    returns = [
        {
            "id": decision._id,
            "name": decision._name,
            "is_main": decision.is_main,
            "inputs": [
                {
                    "id": input.id,
                    "label": input.label,
                    "expression_id": input.expression_id,
                    "typeRef": input.typeRef,
                    "text": input.text,
                }
                for input in decision.deep_inputs(parser)
            ],
            "outputs": [
                {
                    "id": output.id,
                    "name": output.name,
                    "label": output.label,
                    "type": output.type,
                }
                for output in decision.outputs
            ],
        }
        for decision in parser.get_all_decisions()
    ]
    return JSONResponse(content=returns)


class GetBusinessRulesParams(BaseModel):
    bpmnContent: str


# 2. return all BPMN BusinessRule Input and Output
@app.post("/api/v1/chaincode/getBusinessRulesByBpmnC")
async def get_businessrules(params: ChaincodePartParams):
    parser: Choreography = Choreography(params.bpmnContent)
    returns = [
        {
            "id": businessrule.id,
            "documentation": businessrule.documentation,
        }
        for businessrule in parser.query_element_with_type(NodeType.BUSINESSRULE)
    ]
    return JSONResponse(content=returns)


# 启动服务器
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9999)
