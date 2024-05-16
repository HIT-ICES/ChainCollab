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

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChaincodeGenerateParams(BaseModel):
    bpmnContent: str
    participantMspMap: str


class ChaincodeGenerateResponse(BaseModel):
    bpmnContent: str
    ffiContent: str
    timecost: str = None


@app.post("/chaincode/generate")
async def generate_chaincode(params: ChaincodeGenerateParams):
    translator: GoChaincodeTranslator = GoChaincodeTranslator(params.bpmnContent)
    chaincode = translator.generate_chaincode(bindings=json.loads(params.participantMspMap))
    ffi = translator.generate_ffi()
    return ChaincodeGenerateResponse(bpmnContent=chaincode, ffiContent=ffi)


class ChaincodePartParams(BaseModel):
    bpmnContent: str

class ChaincodePartResponse(BaseModel):
    data: Dict[str, Any]


@app.api_route("/chaincode/getPartByBpmnC", methods=["POST"])
async def get_participant_by_bpmn_content(bpmn: ChaincodePartParams):
    translator: GoChaincodeTranslator = GoChaincodeTranslator(bpmn.bpmnContent)
    return JSONResponse(content=translator.get_participants())


@app.get("/ffi/generate")
async def generate_ffi():
    translator = GoChaincodeTranslator()
    return JSONResponse(content={"message": "Hello, world! (async)"})


# 启动服务器
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9999)
