import { useState } from "react"
import { Card, Row, Col, Button, Steps, Modal, Select, Tag, Collapse, Typography, Tabs } from "antd"
import { useLocation, useNavigate } from "react-router-dom";
import { retrieveBPMN, packageBpmn, uploadEthContract, compileEthContract, deployEthContract, updateBPMNStatus, updateBpmnEnv, updateBPMNFireflyUrl, updateBpmnEvents } from "@/api/externalResource"
import { generateChaincode, getMessagesByBpmnContent } from "@/api/translator"
import { useAvaliableEnvs, useBpmnDetailData } from "./hooks"
import axios from "axios"
import api from "@/api/apiConfig"

// Fabric environment steps
const fabricSteps = [
    {
        title: "Initiated",
    },
    {
        title: 'DeployEnved',
    },
    {
        title: 'Generated',
    },
    {
        title: 'Installed',
    },
    {
        title: 'Registered',
    },
];

// Ethereum environment steps (includes Compiled)
const ethereumSteps = [
    {
        title: "Initiated",
    },
    {
        title: 'DeployEnved',
    },
    {
        title: 'Generated',
    },
    {
        title: 'Compiled',
    },
    {
        title: 'Installed',
    },
    {
        title: 'Registered',
    },
];

import { useAppSelector } from "@/redux/hooks";
import { registerDataType, initLedger, invokeFireflyListeners, invokeFireflySubscriptions } from "@/api/executionAPI"
import { current_ip } from "@/api/apiConfig";

const BPMNOverview = () => {

    const location = useLocation();
    const bpmnId = location.pathname.split("/").pop();
    // const bpmnInstanceId = location.pathname.split("/").pop();
    const [isBindingModelOpen, setIsBindingModelOpen] = useState(false);
    const [isEnvModalOpen, setIsEnvModalOpen] = useState(false);
    const currentOrgId = useAppSelector((state) => state.org.currentOrgId);
    const [buttonLoading, setButtonLoading] = useState(false);
    const [dslContentForModify, setDslContentForModify] = useState("");
    const [chainCodeContentForModify, setChainCodeContentForModify] = useState("");
    const [ffiContentForModify, setFFIContentForModify] = useState("");
    const [showArtifacts, setShowArtifacts] = useState(false);
    const [editorOpen, setEditorOpen] = useState(false);
    const [editorKey, setEditorKey] = useState<"dsl" | "chaincode" | "ffi">("dsl");
    const [activeTabKey, setActiveTabKey] = useState<"dsl" | "chaincode">("dsl");


    const navigate = useNavigate();
    const [bpmn, { isLoading, isError, isSuccess }, refetchBpmn] = useBpmnDetailData(bpmnId);
    const currentEnvId = useAppSelector((state) => state.env.currentEnvId);
    const currentConsortiumId = useAppSelector((state) => state.consortium.currentConsortiumId);
    const currentEnvType = useAppSelector((state) => state.env.currentEnvType);

    const status = bpmn.status;

    // Use different steps based on environment type
    const steps = currentEnvType === 'Ethereum' ? ethereumSteps : fabricSteps;

    const currentNumber = ((status: string, envType: string) => {
        if (envType === 'Ethereum') {
            switch (status) {
                case "Initiated":
                    return 0;
                case "DeployEnved":
                    return 1;
                case "Generated":
                    return 2;
                case "Compiled":
                    return 3;
                case "Installed":
                    return 4;
                case "Registered":
                    return 5;
            }
        } else {
            switch (status) {
                case "Initiated":
                    return 0;
                case "DeployEnved":
                    return 1;
                case "Generated":
                    return 2;
                case "Installed":
                    return 3;
                case "Registered":
                    return 4;
            }
        }
    })(status, currentEnvType);


    const EnvModal = ({
        open, setOpen
    }) => {
        const [envId, setEnvId] = useState("");
        const [envType, setEnvType] = useState("");
        const [envs, refetchEnvs] = useAvaliableEnvs(currentConsortiumId);

        return (
            <Modal
                title="Select Env"
                open={open}
                onOk={async () => {
                    await updateBpmnEnv(bpmnId, envId, envType);
                    await updateBPMNStatus(bpmnId, "DeployEnved");
                    refetchBpmn()
                    setButtonLoading(false);
                    setOpen(false)
                }}
                onCancel={() => {
                    setButtonLoading(false);
                    setOpen(false)
                }}
            >
                <Select
                    style={{ width: "100%" }}
                    placeholder="Select a env to deploy"
                    optionFilterProp="children"
                    onChange={
                        (value) => {
                            const selectedEnv = envs.find((env) => env.id == value);
                            setEnvId(selectedEnv.id);
                            setEnvType(selectedEnv.type);
                        }
                    }
                >
                    {envs.map((env) => (
                        <Select.Option value={env.id}>{env.name} ({env.type})</Select.Option>
                    ))}
                </Select>
            </Modal>
        )
    }

    const { Title, Text } = Typography;
    const statusColorMap: Record<string, string> = {
        Initiated: "blue",
        DeployEnved: "gold",
        Generated: "cyan",
        Compiled: "orange",
        Installed: "purple",
        Registered: "green",
    };

    const onGenerate = async () => {
        try {
            setButtonLoading(true);
            const bpmn = await retrieveBPMN(bpmnId);
            // 根据环境类型调用不同的生成 API
            const target = currentEnvType === 'Ethereum' ? 'solidity' : 'go';
            const res = await generateChaincode(bpmn.bpmnContent, target);
            const chaincode_content = res.bpmnContent;
            const ffi_content = res.ffiContent;
            setDslContentForModify(res.dslContent || "");
            setChainCodeContentForModify(chaincode_content);
            setFFIContentForModify(ffi_content);
            setShowArtifacts(true);
            setButtonLoading(false);
            // await packageBPMN(chaincode_content, ffi_content, bpmnInstanceId, currentOrgId);
            // syncInstance()
            // setButtonLoading(false);
        } catch (e) {
            console.log(e);
            setButtonLoading(false);
        }
    }

    const onDeployEnv = async () => {
        try {
            setButtonLoading(true);
            setIsEnvModalOpen(true);
        } catch (e) {
            console.log(e);
        }
    }

    const onRegister = async () => {
        try {
            setButtonLoading(true);
            const bpmn = await retrieveBPMN(bpmnId)
            console.log("BPMN data:", bpmn);

            const contractName = bpmn.name.replace(".bpmn", "")

            // Determine if it's Fabric or Ethereum environment
            const isEthereum = currentEnvType === 'Ethereum';

            let ffiContent = bpmn.ffiContent;
            let parsedFFIContent;

            // For Ethereum, generate FFI if not already present
            if (isEthereum && (!ffiContent || ffiContent.trim() === '')) {
                console.log("FFI content is empty for Ethereum, generating FFI...");

                // Get contract ABI
                const contractAbi = bpmn.ethereum_contract?.abi;
                if (!contractAbi) {
                    throw new Error("Contract ABI not found. Please ensure the contract is compiled.");
                }

                // Call FireFly API to generate FFI
                const fireflyUrlForRegister = `${current_ip}:5000`;
                const generateUrl = `${fireflyUrlForRegister}/api/v1/namespaces/default/contracts/interfaces/generate`;

                const payload = {
                    name: contractName,
                    version: "1.0",
                    input: {
                        abi: contractAbi
                    }
                };

                console.log("Calling FireFly to generate FFI:", generateUrl);
                const ffiResponse = await axios.post(generateUrl, payload);

                if (ffiResponse.status === 200) {
                    parsedFFIContent = ffiResponse.data;
                    ffiContent = JSON.stringify(parsedFFIContent, null, 2);
                    console.log("FFI generated successfully:", parsedFFIContent);

                    // Save FFI content to backend using api instance
                    await api.put(`/consortiums/1/bpmns/${bpmnId}`, {
                        ffiContent: ffiContent
                    });
                    console.log("FFI content saved to backend");
                } else {
                    throw new Error(`Failed to generate FFI: ${ffiResponse.statusText}`);
                }
            } else {
                // For Fabric or if FFI already exists, parse it
                if (!ffiContent || ffiContent.trim() === '') {
                    throw new Error("FFI content is empty. Please ensure the contract was compiled successfully and FFI was generated.");
                }
                parsedFFIContent = JSON.parse(ffiContent);
            }

            console.log("FFI Content:", parsedFFIContent);

            // For Ethereum, use contract address; for Fabric, use chaincode ID
            let contractIdPrefix;
            if (isEthereum) {
                // For Ethereum, use contract ID from ethereum_contract
                contractIdPrefix = contractName + "-" + (bpmn.ethereum_contract?.id || bpmn.id).substring(0, 6);
            } else {
                // For Fabric, use chaincode ID
                contractIdPrefix = contractName + "-" + bpmn.chaincode.id.substring(0, 6);
            }

            parsedFFIContent.name = contractIdPrefix;
            const fireflyUrlForRegister = `${current_ip}:5000`

            // register interface
            const response = await axios.post(`${current_ip}:5000/api/v1/namespaces/default/contracts/interfaces`,
                parsedFFIContent)
            const interfaceid = response.data.id;
            console.log("Interface registered with ID:", interfaceid);

            // Wait for interface to be fully created (FireFly processes this asynchronously)
            console.log("Waiting for interface to be fully created...");
            let interfaceReady = false;
            let retries = 0;
            const maxRetries = 10;

            while (!interfaceReady && retries < maxRetries) {
                try {
                    const checkResponse = await axios.get(
                        `${current_ip}:5000/api/v1/namespaces/default/contracts/interfaces/${interfaceid}`
                    );
                    if (checkResponse.status === 200 && checkResponse.data) {
                        interfaceReady = true;
                        console.log("Interface is ready:", checkResponse.data);
                    }
                } catch (error) {
                    console.log(`Interface not ready yet, retry ${retries + 1}/${maxRetries}`);
                    retries++;
                    await new Promise(resolve => setTimeout(resolve, 2000)); // Wait 2 seconds before retry
                }
            }

            if (!interfaceReady) {
                throw new Error("Interface creation timeout. Please try again later.");
            }

            // register api with different location for Ethereum vs Fabric
            let location;
            if (isEthereum) {
                // For Ethereum, use contract address
                const contractAddress = bpmn.ethereum_contract?.contract_address;
                if (!contractAddress) {
                    // If contract address is not found, log a warning but continue with a placeholder
                    console.warn("Contract address not found, using placeholder. This may cause issues with contract invocation.");
                    // Use a placeholder address or skip registration
                    location = {
                        address: "0x0000000000000000000000000000000000000000" // Placeholder address
                    };
                } else {
                    location = {
                        address: contractAddress
                    };
                }
            } else {
                // For Fabric, use channel and chaincode
                location = {
                    channel: "default",
                    chaincode: contractName
                };
            }

            const jsonData = {
                name: response.data.name,
                interface: {
                    id: interfaceid
                },
                location: location
            };

            await new Promise(resolve => setTimeout(resolve, 4000));
            const response2 = await axios.post(`${current_ip}:5000/api/v1/namespaces/default/apis`,
                jsonData)
            const fireflyUrl = response2.data.urls.ui

            // sleep 4s 否则没法调用Init ledger
            await new Promise(resolve => setTimeout(resolve, 4000));

            // Init ledger (only for Fabric)
            if (!isEthereum) {
                await initLedger(fireflyUrlForRegister, contractIdPrefix);
            }

            // Register datatypes
            await _registerDatatypes(bpmn, contractName, fireflyUrlForRegister);

            await updateBPMNFireflyUrl(bpmnId, fireflyUrl);

            // 获取 events 字段
            await _register_listeners(parsedFFIContent, fireflyUrlForRegister, contractName, interfaceid, isEthereum);

            const res = await updateBPMNStatus(bpmnId, "Registered");
            refetchBpmn()
            setButtonLoading(false);
        } catch (error) {
            console.error("Error occurred while making post request:", error);
            // Show user-friendly error message
            if (error instanceof Error) {
                alert(`Register failed: ${error.message}\n\nPlease check:\n1. Contract was compiled successfully\n2. FFI was generated during compilation\n3. FireFly is running and accessible`);
            }
            setButtonLoading(false);
        }

        async function _register_listeners(parsedFFIContent: any, fireflyUrlForRegister: string, contractName: any, interfaceid: string, isEthereum: boolean) {
            const events = parsedFFIContent.events;

            // 输出 events 字段
            console.log(events);

            // 获取合约地址（仅用于 Ethereum）
            const contractAddress = isEthereum ? bpmn.ethereum_contract?.contract_address : undefined;

            if (isEthereum && !contractAddress) {
                console.error("Contract address not found for Ethereum environment");
                throw new Error("Contract address is required for Ethereum listeners");
            }

            // 访问每个 event 的 name
            events.forEach(async (event) => {
                const res = await invokeFireflyListeners(
                    fireflyUrlForRegister,
                    contractName,
                    event.name,
                    interfaceid,
                    contractAddress  // 传递合约地址
                );
                const listener_id = res.id;
                await invokeFireflySubscriptions(fireflyUrlForRegister, event.name + "-" + contractName, listener_id);
            });
            await updateBpmnEvents(bpmnId, events.map((event) => event.name).join(","));
        }

        async function _registerDatatypes(bpmn: any, chaincodeName: any, fireflyUrlForRegister: string) {
            const messages = await getMessagesByBpmnContent(bpmn.bpmnContent);
            // 目前无法通过getAllMessage获取所有的message,因为需要实例ID查询消息。此处应该通过BPMN内容提取出所有消息的properties字段
            const all_requests = messages ? Object.entries(messages).map(
                ([key, msg]) => {
                    const data1 = {
                        "$id": "https://example.com/widget.schema.json",
                        "$schema": "https://json-schema.org/draft/2020-12/schema",
                        "title": "Widget",
                        "type": "object"
                    };
                    let data2 = {};
                    try {
                        data2 = JSON.parse(msg.documentation);
                        data2 = {
                            "properties": data2["properties"],
                            "required": data2["required"],
                        };
                    } catch (e) {
                        console.log(e);
                        return;
                    }

                    const mergeData = {
                        "name": chaincodeName + "_" + key,
                        "version": "1",
                        "value": {
                            ...data1,
                            ...data2
                        }
                    };
                    return registerDataType(
                        fireflyUrlForRegister,
                        mergeData
                    );
                }
            ) : [];
            await Promise.all(all_requests)
        }
    }

    const buttonText = (() => {
        if (status == 'Installed') {
            return 'Register';
        }
        // else if (status == 'Registered') {
        //     return 'Execute';
        // }
        else if (status == 'Initiated') {
            return 'Deploy to Env';
        } else if (status == 'Compiled') {
            // Compiled 状态显示 Install 按钮
            return 'Install';
        } else if (status == 'Generated') {
            // Generated 状态：Fabric 显示 Install，Ethereum 显示 Upload & Compile
            return currentEnvType === 'Ethereum' ? 'Upload & Compile' : 'Install'
        } else if (status == 'DeployEnved') {
            return 'Generate';
        }
    })()

    const handlePackage = async () => {
        setButtonLoading(true);
        try {
            if (currentEnvType === 'Ethereum') {
                // Ethereum环境：上传并编译合约
                // 1. 先上传合约
                const uploadResult = await uploadEthContract(
                    chainCodeContentForModify, // 传递合约代码内容
                    currentOrgId,
                    bpmnId,
                    currentConsortiumId || "1"
                );

                if (uploadResult && uploadResult.data) {
                    // 2. 上传成功后立即编译
                    const contractId = uploadResult.data.contract_id;
                    await compileEthContract(
                        contractId,
                        currentOrgId,
                        bpmnId,
                        currentConsortiumId || "1"
                    );
                }
            } else {
                // Fabric环境：打包链码
                await packageBpmn(
                    chainCodeContentForModify,
                    ffiContentForModify,
                    currentOrgId,
                    bpmnId,
                    currentConsortiumId || "1"
                );
            }
            refetchBpmn();
        } catch (error) {
            console.error('Package/Upload/Compile failed:', error);
        } finally {
            setButtonLoading(false);
        }
    };

    const CodeEditor = ({
        value,
        onChange,
        minRows = 8,
    }: {
        value: string;
        onChange: (next: string) => void;
        minRows?: number;
    }) => {
        const lines = Math.max(value.split("\n").length, minRows);
        return (
            <div
                style={{
                    display: "flex",
                    borderRadius: 12,
                    border: "1px solid #e2e8f0",
                    background: "linear-gradient(145deg, #0f172a, #111827)",
                    color: "#e2e8f0",
                    overflow: "hidden",
                }}
            >
                <div
                    style={{
                        padding: "12px 10px",
                        background: "rgba(15,23,42,0.8)",
                        borderRight: "1px solid rgba(148,163,184,0.2)",
                        textAlign: "right",
                        fontFamily: "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
                        fontSize: 12,
                        lineHeight: 1.6,
                        color: "#94a3b8",
                        userSelect: "none",
                        minWidth: 44,
                    }}
                >
                    {Array.from({ length: lines }).map((_, index) => (
                        <div key={`line-${index + 1}`}>{index + 1}</div>
                    ))}
                </div>
                <textarea
                    value={value}
                    onChange={(e) => onChange(e.target.value)}
                    rows={lines}
                    style={{
                        flex: 1,
                        border: "none",
                        outline: "none",
                        padding: "12px 14px",
                        background: "transparent",
                        color: "#e2e8f0",
                        fontFamily: "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
                        fontSize: 13,
                        lineHeight: 1.6,
                        resize: "vertical",
                    }}
                />
            </div>
        );
    };

    const PreviewBlock = ({
        value,
        onClick,
    }: {
        value: string;
        onClick: () => void;
    }) => {
        const lines = value.split("\n").slice(0, 10).join("\n");
        return (
            <div>
                <div
                    role="button"
                    tabIndex={0}
                    onClick={onClick}
                    onKeyDown={(event) => {
                        if (event.key === "Enter" || event.key === " ") {
                            onClick();
                        }
                    }}
                    style={{
                        position: "relative",
                        borderRadius: 12,
                        border: "1px solid #e2e8f0",
                        background: "linear-gradient(145deg, #0f172a, #111827)",
                        color: "#e2e8f0",
                        padding: "12px 14px",
                        fontFamily:
                            "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
                        fontSize: 12,
                        lineHeight: 1.6,
                        cursor: "pointer",
                        maxHeight: 220,
                        overflow: "hidden",
                    }}
                >
                    <pre style={{ margin: 0, whiteSpace: "pre-wrap" }}>{lines || "// empty"}</pre>
                </div>
            </div>
        );
    };

    return (
        <>
            <Card
                title="BPMN Deploy Overview"
                style={{ width: "100%" }}
                headStyle={{ borderBottom: "1px solid #e2e8f0", fontWeight: 600 }}
                bodyStyle={{ padding: 20 }}
            >
                <Card.Grid style={{ width: "100%", height: "100%" }}>
                    <Row justify="space-between" align="middle">
                        <Col>
                            <Title level={4} style={{ margin: 0 }}>
                                {bpmn?.name || "BPMN"}
                            </Title>
                            <Text type="secondary">
                                部署流程状态与生成结果会在这里展示。
                            </Text>
                        </Col>
                        <Col>
                            <Tag color={statusColorMap[status] || "default"}>{status}</Tag>
                        </Col>
                    </Row>
                    <Row
                        justify="end"
                        style={{ width: "100%", height: "100%", marginTop: 16 }}
                    >
                        <Col
                            flex="auto"
                            style={{ textAlign: "right", marginRight: "0px" }}
                        >
                            {/* <Button type="primary"
                            style={{ marginRight: "10px", display: status == "Initiated" ? "" : "none" }}
                            onClick={() => {
                                setIsBindingModelOpen(true);
                            }} >BINDING</Button> */}
                            {
                                status !== 'Registered' ?
                                    <Button type="primary"
                                        // disabled={status == 'Initiated'}
                                        loading={buttonLoading}
                                        onClick={async () => {
                                            if (status == 'Compiled') {
                                                // Compiled 状态：调用部署方法
                                                try {
                                                    setButtonLoading(true);
                                                    const contractId = bpmn.ethereum_contract?.id;
                                                    if (contractId) {
                                                        await deployEthContract(
                                                            contractId,
                                                            currentEnvId,
                                                            "default", // namespace
                                                            [] // constructor_args
                                                        );
                                                        // 部署成功后更新 BPMN 状态为 Installed
                                                        await updateBPMNStatus(bpmnId, "Installed");
                                                        refetchBpmn();
                                                    } else {
                                                        console.error('Contract not found for this BPMN');
                                                    }
                                                } catch (error) {
                                                    console.error('Deploy failed:', error);
                                                } finally {
                                                    setButtonLoading(false);
                                                }
                                            } else if (status == 'Generated') {
                                                // Generated 状态：根据环境类型执行不同操作
                                                if (currentEnvType === 'Ethereum') {
                                                    // Ethereum 环境：上传并编译（不部署）
                                                    // 这部分逻辑已经在 handlePackage 中处理
                                                    handlePackage();
                                                } else {
                                                    // Fabric环境跳转到Package页面
                                                    navigate(`/orgs/${currentOrgId}/consortia/${currentConsortiumId}/envs/${currentEnvId}/fabric/chaincode`)
                                                }
                                            } else if (status == 'Installed') {
                                                onRegister();
                                            } else if (status == 'Initiated') {
                                                onDeployEnv();
                                            } else if (status == 'DeployEnved') {
                                                onGenerate();
                                            }
                                        }} >{buttonText}</Button> : null
                            }
                        </Col>
                    </Row>
                    <Row>
                        <Col
                            style={{
                                width: "100%",
                                marginTop: "16px",
                            }}
                        >
                            <Steps
                                current={currentNumber}
                                items={steps}
                            />
                        </Col>
                    </Row>
                </Card.Grid>
            </Card>
            {/* 只有在状态未达到 Generated 时才显示 Generated Artifacts */}
            {status !== 'Generated' && status !== 'Installed' && status !== 'Registered' && showArtifacts ? (
                <Card
                    title="Generated Artifacts"
                    style={{ width: "100%", marginTop: 16 }}
                    headStyle={{ borderBottom: "1px solid #e2e8f0", fontWeight: 600 }}
                    bodyStyle={{ padding: 20 }}
                    extra={
                        status !== 'Generated' && status !== 'Installed' && status !== 'Registered' ? (
                            <Button type="primary" onClick={handlePackage} loading={buttonLoading}>
                                {currentEnvType === 'Ethereum' ? 'Upload' : 'Package'}
                            </Button>
                        ) : null
                    }
                >
                    <Tabs
                        defaultActiveKey="dsl"
                        onChange={(key) => setActiveTabKey(key as "dsl" | "chaincode")}
                        tabBarExtraContent={
                            <Button
                                type="primary"
                                size="small"
                                onClick={() => {
                                    setEditorKey(activeTabKey);
                                    setEditorOpen(true);
                                }}
                            >
                                Edit
                            </Button>
                        }
                        items={[
                            {
                                key: "dsl",
                                label: "DSL",
                                children: (
                                    <PreviewBlock
                                        value={dslContentForModify}
                                        onClick={() => {
                                            setEditorKey("dsl");
                                            setEditorOpen(true);
                                        }}
                                    />
                                ),
                            },
                            {
                                key: "chaincode",
                                label: "Chaincode",
                                children: (
                                    <PreviewBlock
                                        value={chainCodeContentForModify}
                                        onClick={() => {
                                            setEditorKey("chaincode");
                                            setEditorOpen(true);
                                        }}
                                    />
                                ),
                            },
                        ]}
                    />
                    <Collapse
                        style={{ marginTop: 16 }}
                        items={[
                            {
                                key: "ffi",
                                label: "FFI",
                                children: (
                                    <PreviewBlock
                                        value={ffiContentForModify}
                                        onClick={() => {
                                            setEditorKey("ffi");
                                            setEditorOpen(true);
                                        }}
                                    />
                                ),
                            },
                        ]}
                    />
                </Card>
            ) : null}
            <Modal
                open={editorOpen}
                onCancel={() => setEditorOpen(false)}
                onOk={() => setEditorOpen(false)}
                width={980}
                bodyStyle={{ maxHeight: "70vh", overflowY: "auto" }}
                title={
                    editorKey === "dsl"
                        ? "Edit DSL"
                        : editorKey === "chaincode"
                          ? "Edit Chaincode"
                          : "Edit FFI"
                }
            >
                {editorKey === "dsl" ? (
                    <CodeEditor value={dslContentForModify} onChange={setDslContentForModify} minRows={16} />
                ) : null}
                {editorKey === "chaincode" ? (
                    <CodeEditor
                        value={chainCodeContentForModify}
                        onChange={setChainCodeContentForModify}
                        minRows={18}
                    />
                ) : null}
                {editorKey === "ffi" ? (
                    <CodeEditor value={ffiContentForModify} onChange={setFFIContentForModify} minRows={16} />
                ) : null}
            </Modal>
            {
                <EnvModal open={isEnvModalOpen} setOpen={setIsEnvModalOpen} />
            }
        </>


    )

}


export default BPMNOverview;
