import { useEffect, useState, useMemo, useRef } from "react"
import { Card, Row, Col, Button, Steps, Modal, Table, Select, Input, Checkbox, Progress } from "antd"
import { useLocation, useNavigate } from "react-router-dom";
import { retrieveBPMN, packageBpmn, packageERC, updateBPMNStatus, updateBpmnEnv, updateBPMNFireflyUrl, updateBpmnEvents, retrieveERCChaincode, updateERCChaincodeFireflyUrl } from "@/api/externalResource"
import { generateChaincode, getMessagesByBpmnContent } from "@/api/translator"
import { checkERCinstall, useAvaliableEnvs, useBpmnDetailData } from "./hooks"
import axios, { isCancel } from "axios"

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
import { getAllMessages, registerDataType, initLedger, invokeFireflyListeners, invokeFireflySubscriptions } from "@/api/executionAPI"
import { current_ip } from "@/api/apiConfig";
import { eventNames } from "process";
import { update } from "lodash";

const BPMNOverview = () => {

    const location = useLocation();
    const bpmnId = location.pathname.split("/").pop();
    // const bpmnInstanceId = location.pathname.split("/").pop();
    const [isBindingModelOpen, setIsBindingModelOpen] = useState(false);
    const [isEnvModalOpen, setIsEnvModalOpen] = useState(false);
    const currentOrgId = useAppSelector((state) => state.org.currentOrgId);
    const [buttonLoading, setButtonLoading] = useState(false);
    const [isModifyModalOpen, setIsModifyModalOpen] = useState(false);
    const [chainCodeContentForModify, setChainCodeContentForModify] = useState("");
    const [ffiContentForModify, setFFIContentForModify] = useState("");
    const [defaultChainCodeERC20, setDefaultChainCodeERC20] = useState("");
    const [defaultChainCodeERC721, setDefaultChainCodeERC721] = useState("");
    const [defaultChainCodeERC1155, setDefaultChainCodeERC1155] = useState("");
    const [defaultFFIERC20, setDefaultFFIERC20] = useState("");
    const [defaultFFIERC721, setDefaultFFIERC721] = useState("");
    const [defaultFFIERC1155, setDefaultFFIERC1155] = useState("");
    const navigate = useNavigate();
    const [bpmn, { isLoading, isError, isSuccess }, refetchBpmn] = useBpmnDetailData(bpmnId);
    //用来控制reftokens清空标志的
    const [isClearing, setIsClearing] = useState(false);

    const [buttonText, setButtonText] = useState<string>("");
    //进度条
    const [progressList, setProgressList] = useState<
        { name: string; index: number; total: number; status: "packaging" | "success" | "failed"; message?: string }[]
    >([]);

    const [isProgressModalOpen, setIsProgressModalOpen] = useState(false);
    //tokens
    const [ercTokens, setErcTokens] = useState<any[]>([]);
    const ercTokensRef = useRef(ercTokens);
    // 页面初始化时尝试恢复
    useEffect(() => {
        const saved = localStorage.getItem("ercTokens");
        if (saved) {
            setErcTokens(JSON.parse(saved));
        }
    }, []);

    // 每次更新时保存到 localStorage
    useEffect(() => {
    if (isClearing) {
        // 用户主动清空缓存
        localStorage.removeItem("ercTokens");
        ercTokensRef.current = [];
        console.log("🧹 已清空缓存");

        // 清空后自动恢复状态，防止误触发
        setIsClearing(false);
        return;
    }

    if (ercTokens.length > 0) {
        ercTokensRef.current = ercTokens;
        localStorage.setItem("ercTokens", JSON.stringify(ercTokens));
        console.log("更新ercTokensRef.current", ercTokensRef.current);
    }
}, [ercTokens, isClearing]);

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

    const ModifyModal = () => {

        const [tokens, setTokens] = useState([
            { name: "", type: "", chainCode: "", ffi: "默认ffi", installed: false },
        ]);

        const [isChainModalOpen, setIsChainModalOpen] = useState(false);
        const [editingChainIndex, setEditingChainIndex] = useState<number | null>(null);
        const [editingChainContent, setEditingChainContent] = useState("");

        const [editingFFIIndex, setEditingFFIIndex] = useState<number | null>(null);
        const [editingFFIContent, setEditingFFIContent] = useState("");
        const [isFFIModalOpen, setIsFFIModalOpen] = useState(false);

        useEffect(() => {
            const loadChainCodes = async () => {
                try {
                    const res20 = await fetch("/ERC/ERC20.go");
                    const text20 = await res20.text();

                    const res721 = await fetch("/ERC/ERC721.go");
                    const text721 = await res721.text();

                    const res1155 = await fetch("/ERC/ERC1155.go");
                    const text1155 = await res1155.text();
                    setDefaultChainCodeERC20(text20);
                    setDefaultChainCodeERC721(text721);
                    setDefaultChainCodeERC1155(text1155);
                     const ffi20 = await fetch("/ERC/ERC20.json");
                     const ffiText20 = await ffi20.text();
                    setDefaultFFIERC20(ffiText20);

                    const ffi721 = await fetch("/ERC/ERC721.json");
                    const ffiText721 = await ffi721.text();
                    setDefaultFFIERC721(ffiText721);
                    
                    const ffi1155 = await fetch("/ERC/ERC1155.json");
                    const ffiText1155 = await ffi1155.text();
                    setDefaultFFIERC1155(ffiText1155);
                    // 初始化 tokens，默认一行 ERC20
                    //setTokens([{ name: "", type: "", chainCode: "", ffi: "", installed: false }]);
                } catch (err) {
                    console.error("Failed to load chaincode:", err);
                }
            };
            loadChainCodes();
        }, []);
        useEffect(() => {
            const tokenCount = countUniqueTokenNames(chainCodeContentForModify);
            const newTokens = Array.from({ length: tokenCount }, (_, i) => {
                return {
                    name: "",
                    type: "ERC721",
                    chainCode: defaultChainCodeERC721,
                    ffi: defaultFFIERC721,
                    installed: false
                };
            });
            setTokens(newTokens);
        }, [chainCodeContentForModify]);
        const onModify = async () => {
            setProgressList([]); // 清空进度
            setIsProgressModalOpen(true); // 打开进度弹窗

            // ----------------- 打包 BPMN -----------------
            setProgressList((prev) => [...prev, { name: "BPMN", index: 0, total: 1, status: "packaging" as const, message: "Packaging BPMN..." }]);
            await packageBpmn(chainCodeContentForModify, ffiContentForModify, currentOrgId, bpmnId);
            const updatedBpmn = await retrieveBPMN(bpmnId);
            if (updatedBpmn.status == "Generated") {
                setProgressList((prev) => prev.map(item => item.name === "BPMN" ? { ...item, index: 1, status: "success" as const, message: "BPMN packaged" } : item));
            }
            else {
                setProgressList((prev) => prev.map(item => item.name === "BPMN" ? { ...item, index: 1, status: "failed" as const, message: "BPMN packaged" } : item));
            }
            //打包ERC
            const { resulttokens: updatedTokens, results } = await packageERC(
                tokens,
                currentEnvId,
                currentOrgId,
                "1",
                (progress) => {
                    setProgressList((prev) => {
                        const existsIndex = prev.findIndex(p => p.name === progress.name);
                        if (existsIndex >= 0) {
                            const newList = [...prev];
                            newList[existsIndex] = progress; // 覆盖同名 token
                            return newList;
                        } else {
                            return [...prev, progress]; // 新增 token
                        }
                    });
                }
            );
            if(updatedTokens.length==0)
            {
                setIsClearing(true)
            }
            setErcTokens(updatedTokens)
            // console.log(updatedTokens)
            refetchBpmn()
            setButtonLoading(false);
        }

        const handleAddToken = (index: number, type: string = "ERC20") => {
            const defaultChainCode = type === "ERC20" ? defaultChainCodeERC20 : type==="ERC721"? defaultChainCodeERC721:type==="ERC1155"?defaultChainCodeERC1155:null;
            const defaultFFI = type === "ERC20" ? defaultFFIERC20 :type==="ERC721" ?defaultFFIERC721:type==="ERC1155"?defaultFFIERC1155:null;
            const newToken = { name: "", type: "", chainCode: "", ffi: "", installed: false };
            const newTokens = [...tokens];
            newTokens.splice(index + 1, 0, newToken);
            setTokens(newTokens);
        };

        const handleChangeToken = (index: number, key: string, value: string) => {
            const newTokens = [...tokens];
            newTokens[index][key] = value;

            if (key === "type") {
                newTokens[index].chainCode =
                    value === "ERC20" ? defaultChainCodeERC20 :value==="ERC721"? defaultChainCodeERC721:value==="ERC1155"?defaultChainCodeERC1155:null;
                newTokens[index].ffi = value === "ERC20" ? defaultFFIERC20 : value==="ERC721"? defaultFFIERC721:value==="ERC1155"?defaultFFIERC1155:null;
            }

            setTokens(newTokens);
        };

        const handleRemoveToken = (index: number) => {
            const newTokens = tokens.filter((_, i) => i !== index);
            setTokens(newTokens);
        };

        const handleViewChainCode = (index: number) => {
            setEditingChainIndex(index);
            setEditingChainContent(tokens[index].chainCode);
            setIsChainModalOpen(true);
        };

        const handleViewFFI = (index: number) => {
            setEditingFFIIndex(index);
            setEditingFFIContent(tokens[index].ffi || "");
            setIsFFIModalOpen(true);
        };

        // 保存链码内容
        const handleSaveChainCode = () => {
            if (editingChainIndex === null) return;
            const newTokens = [...tokens];
            newTokens[editingChainIndex].chainCode = editingChainContent;
            setTokens(newTokens);
            setIsChainModalOpen(false);
        };

        const handleSaveFFI = () => {
            if (editingFFIIndex === null) return;
            const newTokens = [...tokens];
            newTokens[editingFFIIndex].ffi = editingFFIContent;
            setTokens(newTokens);
            setIsFFIModalOpen(false);
        };

        //校验
        const validateTokens = (): boolean => {
            for (let i = 0; i < tokens.length; i++) {
                const token = tokens[i];
                if (!token.name || token.name.trim() === "") {
                    alert(`Token name  cannot be empty`);
                    return false;
                }
                if (!token.type || token.type.trim() === "") {
                    alert(`Token type  cannot be empty`);
                    return false;
                }
            }
            return true;
        };

        //正则匹配
        function countUniqueTokenNames(code: string): number {
            const regex = /cc\.CreateTokenElement\([^`]+`({.*?})`/gs;
            const matches = code.matchAll(regex);

            const tokenNames = new Set<string>();

            for (const match of matches) {
                try {
                    const obj = JSON.parse(match[1]);
                    if (obj.tokenName) {
                        tokenNames.add(obj.tokenName);
                    }
                } catch (e) {
                    console.warn("JSON parse error:", e);
                }
            }

            return tokenNames.size;
        }
        return (
            <Modal
                title="Modify"
                open={isModifyModalOpen}
                onCancel={async () => {
                    setButtonLoading(false);
                    setIsModifyModalOpen(false);
                }}
                onOk={async () => {
                    if (!validateTokens()) return;
                    onModify();
                    setIsModifyModalOpen(false);
                }}
                width={'40%'}
            >
                <h1>ChainCode</h1>
                <Input.TextArea
                    value={chainCodeContentForModify}
                    onChange={(e) => {
                        setChainCodeContentForModify(e.target.value);
                    }}
                    style={{
                        width: "1000px",
                        height: "300px",
                    }}
                />
                <h2>FFI</h2>
                <Input.TextArea
                    value={ffiContentForModify}
                    onChange={(e) => {
                        setFFIContentForModify(e.target.value);
                    }}
                    style={{
                        width: "1000px",
                        height: "300px",
                    }}
                />

                <h2>Token ERC Chaincode</h2>
                {tokens.map((token, index) => (
                    <div
                        key={index}
                        style={{ display: "flex", gap: "10px", marginBottom: "10px", alignItems: "center" }}
                    >

                        <Checkbox
                            checked={token.installed || false}
                            onChange={(e) => {
                                const newTokens = [...tokens];
                                newTokens[index].installed = e.target.checked;
                                setTokens(newTokens);
                            }}
                        >
                            installed
                        </Checkbox>

                        <Input
                            placeholder="Chaincode name"
                            value={token.name}
                            onChange={(e) => handleChangeToken(index, "name", e.target.value)}
                            style={{ flex: 1 }}
                        />


                        <Select
                            value={token.type}
                            onChange={(value) => handleChangeToken(index, "type", value)}
                            style={{ width: 150 }}
                        >
                            <Select.Option value="ERC20">ERC20</Select.Option>
                            <Select.Option value="ERC721">ERC721</Select.Option>
                            <Select.Option value="ERC1155">ERC1155</Select.Option>
                        </Select>


                        {!token.installed && (
                            <Button size="small" onClick={() => handleViewChainCode(index)}>
                                code
                            </Button>
                        )}

                        {!token.installed && (
                            <Button size="small" onClick={() => handleViewFFI(index)}>
                                ffi
                            </Button>
                        )}

                        {/* <div style={{ display: "flex", gap: "5px" }}>
                            <Button type="dashed" size="small" onClick={() => handleAddToken(index, token.type)}>+</Button>
                            <Button size="small" onClick={() => handleRemoveToken(index)}>-</Button>
                        </div> */}
                    </div>
                ))}
                {/* <Button
                    type="dashed"
                    block
                    style={{ fontSize: 12 }}
                    onClick={() => handleAddToken(tokens.length - 1, "ERC20")}
                >
                    + add new ERC chaincode
                </Button> */}


                <Modal
                    title="ChainCode 内容"
                    open={isChainModalOpen}
                    onCancel={() => setIsChainModalOpen(false)}
                    onOk={handleSaveChainCode}
                    width="50%"
                >
                    <Input.TextArea
                        value={editingChainContent}
                        onChange={(e) => setEditingChainContent(e.target.value)}
                        style={{ width: "100%", height: "300px" }}
                    />
                </Modal>

                <Modal
                    title="FFI 内容"
                    open={isFFIModalOpen}
                    onCancel={() => setIsFFIModalOpen(false)}
                    onOk={handleSaveFFI}
                    width="50%"
                >
                    <Input.TextArea
                        value={editingFFIContent}
                        onChange={(e) => setEditingFFIContent(e.target.value)}
                        style={{ width: "100%", height: "300px" }}
                    />
                </Modal>
            </Modal>
        )
    }
    const ProgressModal = () => {
        const total = progressList.length > 0 ? progressList[0].total : 0;
        const done = progressList.length;
        const columns = [
            { title: "Token", dataIndex: "name" },
            { title: "Progress", render: (_, record) => `${record.index}/${record.total}` },
            {
                title: "Status",
                render: (_, record) => {
                    if (record.status === "packaging") return "⏳ Packaging...";
                    if (record.status === "success") return "✅ Success";
                    if (record.status === "failed") return "❌ Failed";
                    return "";
                },
            },
            { title: "Message", dataIndex: "message" },
            {
                title: "Action",
                render: (_, record) => {
                    if (record.status === "success") {
                        return (
                            <Button
                                type="link"
                                onClick={() => {
                                    navigate(`/orgs/${currentOrgId}/consortia/${currentConsortiumId}/envs/${currentEnvId}/fabric/chaincode`);
                                }}
                            >
                                install
                            </Button>
                        );
                    }
                    return null;
                },
            },
        ];
        return (
            <Modal
                title="Packaging Progress"
                open={isProgressModalOpen}
                onCancel={() => {
                    if (done < total) return;
                    setIsProgressModalOpen(false);
                    refetchBpmn();
                }}
                footer={[
                    <Button
                        key="close"
                        type="primary"
                        onClick={() => {
                            setIsProgressModalOpen(false);
                            refetchBpmn();
                        }}
                        disabled={done < total}
                    >
                        {done < total ? "Processing..." : "Close"}
                    </Button>
                ]}
                width="60%"
            >
                <Progress
                    percent={total > 0 ? Math.round((done / total) * 100) : 0}
                    status={done === total ? "success" : "active"}
                />
                <Table
                    dataSource={progressList}
                    rowKey="name"
                    pagination={false}
                    columns={columns}
                    style={{ marginTop: 20 }}
                />
            </Modal>
        );
    }

    const onGenerate = async () => {
        try {
            setButtonLoading(true);
            const bpmn = await retrieveBPMN(bpmnId);
            const res = await generateChaincode(bpmn.bpmnContent);
            const chaincode_content = res.bpmnContent;
            const ffi_content = res.ffiContent;
            setChainCodeContentForModify(chaincode_content);
            setFFIContentForModify(ffi_content);
            setIsModifyModalOpen(true);
            // await packageBPMN(chaincode_content, ffi_content, bpmnInstanceId, currentOrgId);
            // syncInstance()
            // setButtonLoading(false);
        } catch (e) {
            console.log(e);
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

            console.log("ercTokens 注册:", ercTokensRef.current);
            if (ercTokensRef.current.length > 0) {
                await Promise.all(
                    ercTokensRef.current.map(token => _registerERC(token, current_ip))
                );
            }

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
        async function _registerERC(ercToken: typeof ercTokens[0], current_ip: string) {
            if (!ercToken.ercId) {
                console.error("ERC token has no ercId");
                return;
            }
            try {

                const erc = await retrieveERCChaincode(ercToken.ercId);
                if (!erc) {
                    console.error("ERC not found");
                    return;
                }

                const chaincodeName = erc.name;
                const parsedFFIContent = JSON.parse(erc.ffi_content);
                const chaincodeIdPrefix = chaincodeName + "-" + erc.id.substring(0, 6);
                parsedFFIContent.name = chaincodeIdPrefix;
                const fireflyUrlForRegister = `${current_ip}:5000`;

                const interfaceResponse = await axios.post(
                    `${fireflyUrlForRegister}/api/v1/namespaces/default/contracts/interfaces`,
                    parsedFFIContent
                );
                await new Promise(resolve => setTimeout(resolve, 2000));
                const interfaceId = interfaceResponse.data.id;

                const location = { channel: "default", chaincode: chaincodeName };
                const apiData = {
                    name: interfaceResponse.data.name,
                    interface: { id: interfaceId },
                    location
                };
                await new Promise(resolve => setTimeout(resolve, 4000));
                const apiResponse = await axios.post(
                    `${fireflyUrlForRegister}/api/v1/namespaces/default/apis`,
                    apiData
                );
                const fireflyUrl = apiResponse.data.urls.ui;

                if (parsedFFIContent.events) {
                    for (const event of parsedFFIContent.events) {
                        const listenerRes = await invokeFireflyListeners(fireflyUrlForRegister, chaincodeName, event.name, interfaceId);
                        await invokeFireflySubscriptions(fireflyUrlForRegister, `${event.name}-${chaincodeName}`, listenerRes.id);
                        await new Promise(resolve => setTimeout(resolve, 300));
                    }
                }

                await updateERCChaincodeFireflyUrl(erc.id, fireflyUrl)

                console.log(`ERC ${erc.name} registered to Firefly successfully!`);
            } catch (error) {
                console.error("Error registering ERC to Firefly:", error);
            }
        }
    }

    const currentEnvId = useAppSelector((state) => state.env.currentEnvId);
    const currentConsortiumId = useAppSelector((state) => state.consortium.currentConsortiumId);

    useEffect(() => {
        const getButtonText = async () => {
            if (status === "Installed") {
                if (ercTokensRef.current.length > 0) {
                    const flag = await checkERCinstall(currentConsortiumId, ercTokensRef.current);
                    setButtonText(flag ? "Register" : "Install");
                }
                else if(ercTokensRef.current.length==0)
                {
                    setButtonText("Register");
                }
            } else if (status === "Initiated") {
                setButtonText("Deploy to Env");
            } else if (status === "Generated") {
                setButtonText("Install");
            } else if (status === "DeployEnved") {
                setButtonText("Generate");
            } else if (status === "Registered") {
                setButtonText("Execute");
            }
        };

        getButtonText();
    }, [status, currentConsortiumId, ercTokensRef.current]);

    return (
        <>
            <Card title="Overview" style={{ width: "100%" }}>
                <Card.Grid style={{ width: "100%", height: "100%" }}>
                    <Row
                        justify="end"
                        style={{ width: "100%", height: "100%" }}
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
                                            if (status == 'Generated') {
                                                navigate(`/orgs/${currentOrgId}/consortia/${currentConsortiumId}/envs/${currentEnvId}/fabric/chaincode`)
                                            } else if (status == 'Installed') {
                                                if (ercTokensRef.current.length > 0) {
                                                    const flag = await checkERCinstall(currentConsortiumId, ercTokensRef.current);
                                                    if (flag == true) {
                                                        onRegister();
                                                    }
                                                    else { navigate(`/orgs/${currentOrgId}/consortia/${currentConsortiumId}/envs/${currentEnvId}/fabric/chaincode`) }
                                                }
                                                else onRegister();
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
                                marginLeft: "40px",
                                width: "100%",
                                marginTop: "10px",
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
            {
                ModifyModal()
            }
            {
                <EnvModal open={isEnvModalOpen} setOpen={setIsEnvModalOpen} />
            }
            {ProgressModal()}
        </>


    )

}


export default BPMNOverview;