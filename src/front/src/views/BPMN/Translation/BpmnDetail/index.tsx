import { useState } from "react"
import { Card, Row, Col, Button, Steps, Modal, Select, Tag, Collapse, Typography, Tabs } from "antd"
import { useLocation, useNavigate } from "react-router-dom";
import { retrieveBPMN, packageBpmn, updateBPMNStatus, updateBpmnEnv, updateBPMNFireflyUrl, updateBpmnEvents } from "@/api/externalResource"
import { generateChaincode, getMessagesByBpmnContent } from "@/api/translator"
import { useAvaliableEnvs, useBpmnDetailData } from "./hooks"
import axios from "axios"
const steps = [
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

    const status = bpmn.status;
    const currentNumber = ((status: string) => {
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
    })(status);


    const EnvModal = ({
        open, setOpen
    }) => {
        const [envId, setEnvId] = useState("");
        const [envs, refetchEnvs] = useAvaliableEnvs(currentConsortiumId);

        return (
            <Modal
                title="Select Env"
                open={open}
                onOk={async () => {
                    await updateBpmnEnv(bpmnId, envId);
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
                            setEnvId(envs.find((env) => env.id == value).id);
                        }
                    }
                >
                    {envs.map((env) => (
                        <Select.Option value={env.id}>{env.name}</Select.Option>
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
        Installed: "purple",
        Registered: "green",
    };

    const onGenerate = async () => {
        try {
            setButtonLoading(true);
            const bpmn = await retrieveBPMN(bpmnId);
            const res = await generateChaincode(bpmn.bpmnContent);
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
            debugger
            const bpmn = await retrieveBPMN(bpmnId)
            const chaincodeName = bpmn.name.replace(".bpmn", "")
            const ffiContent = bpmn.ffiContent
            const parsedFFIContent = JSON.parse(ffiContent);
            const chaincodeIdPrefix = chaincodeName + "-" + bpmn.chaincode.id.substring(0, 6);
            parsedFFIContent.name = chaincodeIdPrefix;
            const fireflyUrlForRegister = `${current_ip}:5000`
            // register interface
            const response = await axios.post(`${current_ip}:5000/api/v1/namespaces/default/contracts/interfaces`,
                parsedFFIContent)
            const interfaceid = response.data.id;
            // register api
            const location = {
                channel: "default",        //写死在后端
                chaincode: chaincodeName
            };
            const jsonData = {
                name: response.data.name,  //接口id名字改为bpmninstanceid
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
            // Init ledger
            await initLedger(fireflyUrlForRegister, chaincodeIdPrefix);
            // Register datatypes
            await _registerDatatypes(bpmn, chaincodeName, fireflyUrlForRegister);

            await updateBPMNFireflyUrl(bpmnId, fireflyUrl);

            // 获取 events 字段
            await _register_listeners(parsedFFIContent, fireflyUrlForRegister, chaincodeName, interfaceid);


            const res = await updateBPMNStatus(bpmnId, "Registered");
            refetchBpmn()
            setButtonLoading(false);
        } catch (error) {
            console.error("Error occurred while making post request:", error);
        }

        async function _register_listeners(parsedFFIContent: any, fireflyUrlForRegister: string, chaincodeName: any, interfaceid: string) {
            const events = parsedFFIContent.events;

            // 输出 events 字段
            console.log(events);

            // 访问每个 event 的 name
            events.forEach(async (event) => {
                const res = await invokeFireflyListeners(fireflyUrlForRegister, chaincodeName, event.name, interfaceid);
                const listener_id = res.id;
                await invokeFireflySubscriptions(fireflyUrlForRegister, event.name + "-" + chaincodeName, listener_id);
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

    const currentEnvId = useAppSelector((state) => state.env.currentEnvId);
    const currentConsortiumId = useAppSelector((state) => state.consortium.currentConsortiumId);

    const buttonText = (() => {
        if (status == 'Installed') {
            return 'Register';
        }
        // else if (status == 'Registered') {
        //     return 'Execute';
        // }
        else if (status == 'Initiated') {
            return 'Deploy to Env';
        } else if (status == 'Generated') {
            return 'Install'
        } else if (status == 'DeployEnved') {
            return 'Generate';
        }
    })()

    const handlePackage = async () => {
        setButtonLoading(true);
        await packageBpmn(
            chainCodeContentForModify,
            ffiContentForModify,
            currentOrgId,
            bpmnId,
            currentConsortiumId || "1"
        );
        refetchBpmn();
        setButtonLoading(false);
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
                                        onClick={() => {
                                            if (status == 'Generated') {
                                                navigate(`/orgs/${currentOrgId}/consortia/${currentConsortiumId}/envs/${currentEnvId}/fabric/chaincode`)
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
            {showArtifacts ? (
                <Card
                    title="Generated Artifacts"
                    style={{ width: "100%", marginTop: 16 }}
                    headStyle={{ borderBottom: "1px solid #e2e8f0", fontWeight: 600 }}
                    bodyStyle={{ padding: 20 }}
                    extra={
                        <Button type="primary" onClick={handlePackage} loading={buttonLoading}>
                            Package
                        </Button>
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
