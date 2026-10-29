function Activity_0fbi09z(uint256 instanceId) external onlyInitialized {
    Instance storage inst = _getInstance(instanceId);
    BusinessRule storage br = inst.businessRules[BusinessRuleKey.Activity_0fbi09z];
    require(br.exists, "business rule not set");
    require(br.state == ElementState.ENABLED, "business rule not enabled");
    _checkBusinessRuleCaller(inst, br);

    string memory inputBody = "";
    inputBody = _jsonAppendField(
        inputBody,
        _jsonField(
            "amount",
        _jsonInt(inst.stateMemory.Amount)
        )
    );
    inputBody = _jsonAppendField(
        inputBody,
        _jsonField(
            "Self_pickup",
        _jsonBool(inst.stateMemory.Self_pickup)
        )
    );
    string memory inputData = _jsonObject(inputBody);
    IDmnLite dmnLite = IDmnLite(inst.dmnLiteAddress);
    require(bytes(br.dmnCid).length != 0, "dmn cid not set");
    bytes32 requestId = dmnLite.requestDMNDecision(
        inst.dmnEvalUrl,
        br.dmnCid,
        br.decisionId,
        inputData
    );
    require(requestId != bytes32(0), "dmn request failed");
    br.requestId = requestId;
    br.requestedAt = block.timestamp;
    br.fulfilledAt = 0;
    br.lastRawResult = "";
    br.state = ElementState.WAITING_FOR_CONFIRMATION;
    emit BusinessRuleRequested(instanceId, BusinessRuleKey.Activity_0fbi09z, requestId);
}

function Activity_0fbi09z_Continue(uint256 instanceId) external onlyInitialized {
    Instance storage inst = _getInstance(instanceId);
    BusinessRule storage br = inst.businessRules[BusinessRuleKey.Activity_0fbi09z];
    require(br.exists, "business rule not set");
    require(br.state == ElementState.WAITING_FOR_CONFIRMATION, "business rule not waiting");
    require(br.requestId != bytes32(0), "business rule not requested");
    _checkBusinessRuleCaller(inst, br);

    IDmnLite dmnLite = IDmnLite(inst.dmnLiteAddress);
    (
        uint8 requestState,
        address requester,
        ,
        uint256 fulfilledAt,
        bool exists
    ) = dmnLite.getRequestStatus(br.requestId);
    require(exists, "dmn request missing");
    require(requester == address(this), "unexpected dmn requester");
    require(requestState == DMN_REQUEST_FULFILLED, "dmn result not ready");

    string memory raw = dmnLite.getRawByRequestId(br.requestId);
    br.lastRawResult = raw;
    br.fulfilledAt = fulfilledAt;
    inst.stateMemory.Deliver = _extractJsonBool(raw, "deliver");
    br.state = ElementState.COMPLETED;
    inst.gateways[GatewayKey.Gateway_11hmo2k].state = ElementState.ENABLED;

    emit BusinessRuleCompleted(instanceId, BusinessRuleKey.Activity_0fbi09z, br.requestId);
}
