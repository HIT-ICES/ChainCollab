import { useEffect, useState } from "react"
import { Card, Row, Col, Button, Typography, Steps, Modal, TableProps, Table, Select, Input, Tag } from "antd"
import { useLocation, useNavigate } from "react-router-dom";
import { BindingModal } from "./bindingModel"
import { getMapInfoofBPMNInstance, generateChaincode, retrieveBPMN, packageBPMN, updateBPMNInstanceStatus, updateBPMNInstanceFireflyUrl } from "@/api/externalResource"
import { useAvailableMembers } from "./hooks"
import axios from "axios"
const steps = [
    {
        title: "Initiated",
    },
    {
        title: 'Fullfilled',
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

import { useBPMNIntanceDetailData } from './hooks'
import { useAppSelector } from "@/redux/hooks";
import { useFireflyData } from "./hooks";

import { getAllMessages, registerDataType, initLedger } from "@/api/executionAPI"
import { useBPMNBindingDataReverse } from './hooks'
// import TestModal from "./test";
import JSZip from 'jszip';
import { current_ip } from "@/api/apiConfig";

const MembershipModal = ({
    open, setOpen, envId, bpmnInstanceId
}) => {
    const navigate = useNavigate();
    const [members, syncMembers] = useAvailableMembers(envId);
    const [currentMembership, setCurrentMembership] = useState<any>({
        membershipId: "",
        membershipName: "",
        resourceSetId: "",
        msp: "",
    })
    const currentOrgId = useAppSelector((state) => state.org.currentOrgId);
    const [fireflyData, syncFireflyData] = useFireflyData(
        envId,
        currentOrgId,
        currentMembership.membershipId
    );
    const [bindingData, syncBindingData] = useBPMNBindingDataReverse(bpmnInstanceId);

    const participant = bindingData?.[currentMembership.membershipName];
    // debugger;
    const coreUrl = fireflyData?.coreURL;
    const orgName = fireflyData?.orgName;
    const msp = currentMembership?.msp;

    return (
        <Modal
            title="Select Membership"
            open={open}
            onOk={() => {
                navigate(`/bpmn/execution/${bpmnInstanceId}?coreUrl=${coreUrl}&msp=${msp}&identity=did:firefly:org/${orgName}&participant=${participant}`)
            }}
            onCancel={() => setOpen(false)}
        >
            <Select
                style={{ width: "100%" }}
                placeholder="Select a membership"
                optionFilterProp="children"
                onChange={
                    (value) => {
                        setCurrentMembership(members.find((member) => member.membershipId == value))
                    }
                }
            >
                {members.map((member) => (
                    <Select.Option value={member.membershipId}
                    >{member.membershipName}</Select.Option>
                ))}
            </Select>
        </Modal>
    )
}


const BPMNInstanceOverview = () => {

    const location = useLocation();
    const bpmnInstanceId = location.pathname.split("/").pop();
    const [isBindingModelOpen, setIsBindingModelOpen] = useState(false);
    const navigate = useNavigate();


    const [instance, syncInstance] = useBPMNIntanceDetailData(bpmnInstanceId)
    const status = instance.status;
    const currentNumber = ((status: string) => {
        switch (status) {
            case "Initiated":
                return 0;
            case "Fullfilled":
                return 1;
            case "Generated":
                return 2;
            case "Installed":
                return 3;
            case "Registered":
                return 4;
        }
    })(status);
    const currentOrgId = useAppSelector((state) => state.org.currentOrgId);

    const [buttonLoading, setButtonLoading] = useState(false);
    const [isExecuteModalOpen, setIsExecuteModalOpen] = useState(false);
    const onExecute = () => {
        setIsExecuteModalOpen(true);
    }
    const [isModifyModalOpen, setIsModifyModalOpen] = useState(false);
    const [chainCodeContentForModify, setChainCodeContentForModify] = useState("");
    const [ffiContentForModify, setFFIContentForModify] = useState("");
    const ModifyModal = () => {

        const onModify = async () => {
            await packageBPMN(chainCodeContentForModify, ffiContentForModify, bpmnInstanceId, currentOrgId);
            syncInstance()
            setButtonLoading(false);
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
            </Modal>
        )
    }

    const onGenerate = async () => {
        try {
            setButtonLoading(true);
            const mapInfo = await getMapInfoofBPMNInstance(bpmnInstanceId);
            const mapInfoString = JSON.stringify(mapInfo);
            const bpmn = await retrieveBPMN(instance.bpmn);
            const res = await generateChaincode(bpmn.bpmnContent, mapInfoString);
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

    const onTestGenerate = async () => {
        const mapInfo = await getMapInfoofBPMNInstance(bpmnInstanceId);
        const mapInfoString = JSON.stringify(mapInfo);
        const bpmn = await retrieveBPMN(instance.bpmn);

        const record = []
        for (let i = 0; i < 50; i++) {
            // var start = performance.now();
            const res = await generateChaincode(bpmn.bpmnContent, mapInfoString);
            // var end = performance.now();
            // var timeCost = end - start;
            record.push({ index: i + 1, timeCost: res.timeCost });
        }
        let csvContent = "index,timeCost\n";
        record.forEach((record) => {
            csvContent += record.index + "," + record.timeCost + "\n";
        });

        const zip = new JSZip();
        zip.file("records.csv", csvContent);
        console.log(record)
        zip.generateAsync({ type: "blob" }).then((content) => {
            var a = document.createElement('a');
            document.body.appendChild(a);
            var url = window.URL.createObjectURL(content);
            a.href = url;
            a.download = bpmn.name + bpmnInstanceId + "_records.zip";
            a.click();
            window.URL.revokeObjectURL(url);
        });

    }




    const onRegister = async () => {
        try {
            setButtonLoading(true);
            const bpmn = await retrieveBPMN(instance.bpmn)
            const bpmnId = bpmn.id
            const ffiContent = instance.ffiContent
            const parsedFFIContent = JSON.parse(ffiContent);
            const chaincodeIdPrefix = instance.chaincode_name + instance.chaincode_id.substring(0, 6);
            parsedFFIContent.name = chaincodeIdPrefix
            const response = await axios.post(`http://${current_ip}:5000/api/v1/namespaces/default/contracts/interfaces`,
                parsedFFIContent)
            const interfaceid = response.data.id;
            const location = {
                channel: "default",        //写死在后端
                chaincode: instance.chaincode_name
            };
            const jsonData = {
                name: response.data.name,  //接口id名字改为bpmninstanceid
                interface: {
                    id: interfaceid
                },
                location: location
            };
            await new Promise(resolve => setTimeout(resolve, 4000));
            const response2 = await axios.post(`http://${current_ip}:5000/api/v1/namespaces/default/apis`,
                jsonData)
            const fireflyUrl = response2.data.urls.ui
            await new Promise(resolve => setTimeout(resolve, 4000));
            const fireflyUrlForRegister = `http://${current_ip}:5000`
            await initLedger(fireflyUrlForRegister, chaincodeIdPrefix);
            await new Promise(resolve => setTimeout(resolve, 4000));
            const messages = await getAllMessages(fireflyUrlForRegister, chaincodeIdPrefix);

            const all_requests = messages ? messages.map(
                (msg) => {
                    console.log()
                    const data1 = {
                        "$id": "https://example.com/widget.schema.json",
                        "$schema": "https://json-schema.org/draft/2020-12/schema",
                        "title": "Widget",
                        "type": "object"
                    }
                    let data2 = {}
                    try {
                        data2 = JSON.parse(msg.format)
                        data2 = {
                            "properties": data2["properties"],
                            "required": data2["required"],
                        }
                    } catch (e) {
                        console.log(e)
                        return;
                    }

                    const mergeData = {
                        "name": bpmn.name + "_" + msg.messageID,
                        "version": "1",
                        "value": {
                            ...data1,
                            ...data2
                        }
                    }
                    return registerDataType(
                        fireflyUrlForRegister,
                        mergeData
                    )
                }
            ) : [];
            const res2 = await Promise.all(all_requests)
            await updateBPMNInstanceFireflyUrl(bpmnInstanceId, bpmnId, fireflyUrl);
            const res = await updateBPMNInstanceStatus(bpmnInstanceId, bpmnId, "Registered");
            syncInstance()
            setButtonLoading(false);
        } catch (error) {
            console.error("Error occurred while making post request:", error);
        }
    }

    const currentEnvId = useAppSelector((state) => state.env.currentEnvId);
    const currentConsortiumId = useAppSelector((state) => state.consortium.currentConsortiumId);

    const buttonText = (() => {
        if (status == 'Installed') {
            return 'Register';
        } else if (status == 'Registered') {
            return 'Execute';
        } else {
            return status == 'Generated' ? 'Install' : 'Generate';
        }
    })()

    const [isTestOpen, setIsTestOpen] = useState(false)
    const onTest = () => {
        setIsTestOpen(true);
    };
    const handleTestCancel = () => {
        setIsTestOpen(false);
    };

    return (
        <>        <Card title="Overview" style={{ width: "100%" }}>
            <Card.Grid style={{ width: "100%", height: "100%" }}>
                <Row
                    justify="end"
                    style={{ width: "100%", height: "100%" }}
                >
                    <Col
                        flex="auto"
                        style={{ textAlign: "right", marginRight: "0px" }}
                    >
                        <Button type="primary"
                            style={{ marginRight: "10px", display: status == "Initiated" ? "" : "none" }}
                            onClick={() => {
                                setIsBindingModelOpen(true);
                            }} >BINDING</Button>
                        <Button type="primary" disabled={status == 'Initiated'}
                            loading={buttonLoading}
                            onClick={() => {
                                if (status == 'Generated') {
                                    navigate(`/orgs/${currentOrgId}/consortia/${currentConsortiumId}/envs/${currentEnvId}/fabric/chaincode`)
                                } else if (status == 'Installed') {
                                    onRegister();
                                } else if (status == 'Registered') {
                                    // navigate(`/bpmn/execution`);
                                    onExecute();
                                } else {
                                    onGenerate();
                                    // onTestGenerate();
                                }
                            }} >{buttonText}</Button>
                        <Button type="primary" style={{ marginLeft: "10px", display: status == "Registered" ? "" : "none" }} onClick={() => {
                            onTest()
                        }}>Test</Button>
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
                instance.environment_id ?
                    (<BindingModal bpmnInstanceId={bpmnInstanceId} open={isBindingModelOpen} setOpen={setIsBindingModelOpen}
                        envId={instance.environment_id} bpmnId={instance.bpmn} syncExternalData={() => {
                            syncInstance()
                        }}
                    />) : null
            }
            {
                instance.environment_id && instance.bpmn ?
                    (<MembershipModal open={isExecuteModalOpen} setOpen={setIsExecuteModalOpen} envId={instance.environment_id}
                        bpmnInstanceId={instance.id}
                    />) : null
            }
            <Modal
                title="TestModel"
                open={isTestOpen}
                onCancel={handleTestCancel}
                style={{ width: '100%' }}
                width={' 85%'}>
                {/* <TestModal
                    envId={instance.environment_id}
                    bpmnInstanceId={instance.id} /> */}
            </Modal>
            {
                ModifyModal()
            }
        </>


    )

}


export default BPMNInstanceOverview;