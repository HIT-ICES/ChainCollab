from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from datetime import datetime
import asyncio
import uvicorn
from translator import GoChaincodeTranslator
from pydantic import BaseModel
from typing import Dict, Any
import json
from fastapi.middleware.cors import CORSMiddleware
from dmn_parser.parser import DMNParser
from choreography_parser.parser import Choreography
from choreography_parser.elements import NodeType

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChaincodeGenerateParams(BaseModel):
    bpmnContent: str


class ChaincodeGenerateResponse(BaseModel):
    bpmnContent: str
    ffiContent: str
    timecost: str = None


@app.post("/api/v1/chaincode/generate")
async def generate_chaincode(params: ChaincodeGenerateParams):
    translator: GoChaincodeTranslator = GoChaincodeTranslator(params.bpmnContent)
    chaincode = translator.generate_chaincode()
    ffi = translator.generate_ffi()
    return ChaincodeGenerateResponse(bpmnContent=chaincode, ffiContent=ffi)


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
