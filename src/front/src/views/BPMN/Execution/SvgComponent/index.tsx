import { useEffect, useRef, useState } from "react";
import { css } from "@emotion/css";
import { Button, Input, Form, Upload, Tag, Typography, Table } from "antd";
import { UploadOutlined } from "@ant-design/icons";
import { useLocation } from "react-router-dom";
import { useBPMNIntanceDetailData, useBPMNDetailData } from "./hook";
import { getFireflyWithMSP } from '@/api/externalResource.ts'
import JSZip from "jszip";
const TestMode = true;

// 定义Flex容器样式
const flexContainerStyle = css`
  display: flex;
  align-items: center;
  flex-direction: column;
  justify-content: flex-start; // Adjusted for a more consistent alignment
  gap: 10px; // Spacing between form items
  flex-wrap: wrap; // Allow wrapping for smaller screens or many items
`;
const sleep = async (ms) => {
    return new Promise(resolve => setTimeout(resolve, ms));
}

import {
    invokeEventAction, invokeGatewayAction,
    fireflyFileTransfer, fireflyDataTransfer, invokeMessageAction
} from '@/api/executionAPI.ts'

import TestComponent from '../../testComponent.tsx'

const InputComponentForMessage = (
    {
        currentElement,
        contractName,
        coreURL,
        bpmnName,
        Identity,
        contractMethodDes,
        bpmn,
        bpmnInstance
    }
) => {
    // debugger;
    const format = JSON.parse(currentElement.format);

    const transValue = (key, value) => {
        if (format.properties[key].type === "string") return value;
        if (format.properties[key].type === "number") return parseInt(value);
        if (format.properties[key].type === "boolean") return value === "true";
    }

    const formRef = useRef(null);
    const isSender = currentElement.state === 1;
    const methodName = currentElement.messageID + (isSender ? "_Send" : "_Complete");



    const confirmMessage = async () => {
        const res = await invokeMessageAction(coreURL,
            contractName
            , methodName, {});
    }
    const [messageToConfirm, setMessageToConfirm] = useState([]);

    const TestResultColumns = [
        {
            title: 'Index',
            dataIndex: 'index',
            key: 'index',
        },
        {
            title: "fileCostTime",
            dataIndex: 'fileCostTime',
            key: 'fileCostTime',
            render: (text, record, index) => {
                // show list
                return <div>
                    {
                        text.map((item, index) => {
                            return <Tag key={index} color="blue">{item}</Tag>
                        })
                    }
                </div>
            }
        },
        {
            title: "messageCostTime",
            dataIndex: 'messageCostTime',
            key: 'messageCostTime',
        },
        {
            title: "chainCodeCostTime",
            dataIndex: 'chainCodeCostTime',
            key: 'chainCodeCostTime',
        }
    ]

    const TestConfirmResultColumns = [
        {
            title: 'Index',
            dataIndex: 'index',
            key: 'index',
        },
        {
            title: 'TimeCost',
            dataIndex: 'timeCost',
            key: 'timeCost',
        }
    ]

    useEffect(() => {
        if (isSender) {
            // setMessageToConfirm("Please confirm the message to send");
            return;
        }
        const fetchData = async () => {
            //http://127.0.0.1:5000/api/v1/namespaces/default/messages/{currentElement.fireflyTranID}/data

            const res = await axios.get(`${coreURL}/api/v1/namespaces/default/messages/${currentElement.fireflyTranID}/data`);
            const messageToShow = res.data.map(
                (item) => {
                    return Object.keys(item.value).map(key => ({ name: key, value: item.value[key] }));
                }
            ).reduce((acc, cur) => {
                return [...acc, ...cur];
            });
            setMessageToConfirm(messageToShow);
        }
        fetchData();
    }
        , [currentElement])

    if (!isSender) {
        return (
            <div style={{
                display: "flex",
                flexDirection: "column",
            }} >
                {/* Status */}
                <Typography.Text>{
                    messageToConfirm.map(
                        (item) => {
                            return <Tag color="green" >{item.name}: {item.value.toString()}</Tag>
                        }
                    )
                }</Typography.Text>
                <Button
                    style={{ backgroundColor: 'mediumspringgreen', marginTop: "10px" }}
                    onClick={() => { confirmMessage() }}
                >Confirm</Button>
                <TestComponent
                    bpmn={bpmn}
                    bpmnInstance={bpmnInstance}
                    testFunction={async () => {

                        const theRes = {}
                        // const observer = new PerformanceObserver(list => {
                        //     list.getEntries().forEach(
                        //         (entry) => {
                        //             if (entry.name.includes("_Complete")) {
                        //                 theRes["timeCost"] = entry.responseStart - entry.requestStart;
                        //             }
                        //         }
                        //     );
                        // });
                        // observer.observe({ entryTypes: ["resource"] });
                        await confirmMessage();
                        await sleep(300);
                        // observer.disconnect();
                        return { ...theRes }
                    }}
                    columns={TestConfirmResultColumns}
                />
            </div>
        );
    }

    function generateRandomString(length) {
        const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
        let result = '';
        for (let i = 0; i < length; i++) {
            result += characters.charAt(Math.floor(Math.random() * characters.length));
        }
        return result;
    }

    function generateRandomFile(sizeInMB) {
        function generateRandomString(length) {
          let result = '';
          const characters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
          for (let i = 0; i < length; i++) {
            result += characters.charAt(Math.floor(Math.random() * characters.length));
          }
          return result;
        }
    
        const sizeInBytes = sizeInMB * 1024 * 1024;
        const randomString = generateRandomString(sizeInBytes);
        const blob = new Blob([randomString], { type: 'text/plain' });
        const file = new File([blob], `randomFile_${sizeInMB}MB.txt`, { type: 'text/plain' });
        return file;
      }

    const handleTest = async () => {
        const values = {};
        const theRes = {
            fileCostTime: [],
            messageCostTime: 0,
            chainCodeCostTime: 0
        };
        // const observer = new PerformanceObserver(list => {
        //     list.getEntries().forEach(
        //         (entry) => {
        //             if (entry.name.includes("private")) {
        //                 theRes["messageCostTime"] = entry.responseStart - entry.requestStart;
        //             }
        //             if (entry.name.includes("invoke/Message")) {
        //                 theRes["chainCodeCostTime"] = entry.responseStart - entry.requestStart;
        //             }
        //             if (entry.name.includes("default/data")){
        //                 // console.log(entry)
        //                 theRes["fileCostTime"].push(entry.responseStart - entry.requestStart);
        //             }
        //         }
        //     );
        // });
        // observer.observe({ entryTypes: ["resource"] });
        for (let key in format.properties) {
            values[key] = generateRandomString(10);
        }
        
        for (let key in format.files) {
            // generate file
            // 1, 5 , 10, 50, 100
            values[key] ={file:generateRandomFile(100)} 
        }
        await onHandleMessage(values);
        await sleep(500);
        // observer.disconnect();
        return theRes;
    }


    const onHandleMessage = async (values) => {
        // 0. get Identity to send message

        const msp = currentElement.receiveMspID
        const mspData = await getFireflyWithMSP(msp)
        const Identity = "did:firefly:org/" + mspData.data.org_name;

        // 1. check type
        // debugger;
        // 2. upload file if exists
        let file_ids = [];
        for (let key in format.files) {
            const file = values[key];
            if (file) {
                const res = await fireflyFileTransfer(coreURL, file.file);
                file_ids.push(res.id);

            }
        }
        if (file_ids) {
            await new Promise(resolve => setTimeout(resolve, 2000));
        }
        // // 3. send firefly message if exists

        const datatype = {
            name: bpmnName + "_" + currentElement.messageID,
            version: '1'
        };
        let value = {}
        for (let key in format.properties) {
            value[key] = transValue(key, values[key])
        }
        // debugger;
        const dataItem1 = {
            datatype: datatype,
            value: value,
            validator: 'json'
        };
        let dataItem2 = file_ids.map(
            (id) => {
                return {
                    id: id
                }
            }
        )
        const data = {
            data: [dataItem1, ...dataItem2],
            group: {
                members: [
                    {
                        identity: Identity
                    }
                ]
            },
            header: {
                tag: "private",
                topics: [
                    bpmnName + "_" + currentElement.messageID
                ]
            }
        };
        const res = await fireflyDataTransfer(coreURL, data);
        const fireflyMessageID = res.header.id;
        // // 4. use firefly message id to send contract message
        // const fireflyMessageID = "534a8bd7-4d3f-42a9-86b4-8248a2c3164e"
        const methodParams = contractMethodDes.methods.find(
            (item) => {
                return item.name === methodName
            }
        ).params.filter((item) => { return item.name !== "fireflyTranID" })
        const otherKeyValuePair = methodParams.map((item) => {
            return {
                [item.name]: transValue(item.name, values[item.name])
            }
        }
        ).reduce((acc, cur) => {
            return { ...acc, ...cur }
        }, {})
        const res2 = await invokeMessageAction(coreURL,
            contractName
            , methodName, {
            "input": {
                "fireflyTranID": fireflyMessageID,
                ...otherKeyValuePair
            }
        });
    }

    return (
        <div style={{
            display: "flex",
            flexDirection: "column",
        }} >
            <Form
                layout="horizontal"
                className={flexContainerStyle}
                labelCol={{ span: 8 }}
                wrapperCol={{ span: 16 }}
                ref={formRef}
                onFinish={onHandleMessage}
            >
                {
                    Object.keys(format.properties).map((key) => {
                        return (
                            <Form.Item
                                label={key}
                                name={key}
                                key={key}
                                rules={
                                    [
                                        {
                                            required: format.required.includes(key),
                                            message: `${key} is required!`
                                        }
                                    ]
                                }
                            >
                                <Input placeholder={format.properties[key].description} />
                            </Form.Item>
                        )
                    })
                }
                {
                    Object.keys(format.files).map((key) => {
                        return (
                            <Form.Item
                                label={key}
                                name={key}
                                key={key}
                                rules={
                                    [
                                        {
                                            required: format["file required"].includes(key),
                                            message: `${key} is required!`
                                        }
                                    ]
                                }
                            >
                                <Upload beforeUpload={(file) => { return false }}>
                                    <Button icon={<UploadOutlined />}>Upload</Button>
                                </Upload>
                            </Form.Item>
                        )
                    })
                }
                <Form.Item>
                    <Button
                        style={{ backgroundColor: 'mediumspringgreen' }}
                        htmlType="submit"
                    >Submit</Button>
                </Form.Item>
            </Form>
            {TestMode ? < TestComponent
                bpmn={bpmn}
                bpmnInstance={bpmnInstance}
                testFunction={async () => {
                    const res = await handleTest()
                    return { ...res }
                }}
                columns={TestResultColumns}
            />
                : null}
        </div>
    )

}

const ControlPanel = ({
    currentElement,
    contractName,
    coreURL,
    bpmnName,
    contractMethodDes,
    bpmnInstance,
    bpmn
}) => {
    const location = useLocation();
    const queryParams = new URLSearchParams(location.search);
    const msp = queryParams.get("msp");
    const type = currentElement?.type;
    const Identity = queryParams.get("identity");
    const isYourTurn = (() => {
        if (type === "event") return currentElement?.eventState === 1;
        if (type === "gateway") return currentElement?.gatewayState === 1;
        if (type === "message") return currentElement?.msgState === 1 && currentElement?.sendMspID === msp ||
            currentElement?.msgState === 2 && currentElement?.receiveMspID === msp;
    })()
    const showTransactionId = (() => {
        if (type === "message") return currentElement?.msgState === 2 && currentElement?.receiveMspID === msp;
        return false;
    })()

    if (!isYourTurn) return null;

    const TestResultColumns = [
        {
            title: 'Index',
            dataIndex: 'index',
            key: 'index',
        },
        {
            title: 'TimeCost',
            dataIndex: 'timeCost',
            key: 'timeCost',
        }
    ]

    // EVENT

    const onHandleEvent = () => {
        invokeEventAction(coreURL,
            contractName
            , currentElement.eventID);
    }

    if (type === "event")
        return (
            <div style={{
                display: "flex",
                flexDirection: "column",

            }} >
                <Button
                    style={{ backgroundColor: 'mediumspringgreen' }}
                    onClick={() => { onHandleEvent() }}
                >Next</Button>
                {TestMode ?
                    <TestComponent
                        bpmn={bpmn}
                        bpmnInstance={bpmnInstance}
                        testFunction={async () => {
                            const theRes = {}
                            // const observer = new PerformanceObserver(list => {
                            //     list.getEntries().forEach(
                            //         (entry) => {
                            //             if (entry.name.includes("invoke/Event")) {
                            //                 theRes["timeCost"] = entry.responseStart - entry.requestStart;
                            //             }
                            //         }
                            //     );
                            // });
                            // observer.observe({ entryTypes: ["resource"] });
                            await invokeEventAction(coreURL,
                                contractName
                                , currentElement.eventID);
                            await sleep(300);
                            // observer.disconnect();
                            return { ...theRes }
                        }}
                        columns={TestResultColumns}
                    />
                    : null}
            </div>
        );

    const onHandleGateway = () => {
        invokeGatewayAction(coreURL,
            contractName
            , currentElement.gatewayID);
    }



    if (type === "gateway")
        return (
            <div style={{
                display: "flex",
                flexDirection: "column",

            }} >
                <Button
                    style={{ backgroundColor: 'mediumspringgreen' }}
                    onClick={() => {
                        onHandleGateway()
                    }}
                >Next</Button>
                {TestMode ? <TestComponent
                    bpmn={bpmn}
                    bpmnInstance={bpmnInstance}
                    testFunction={async () => {
                        const theRes = {}
                        // const observer = new PerformanceObserver(list => {
                        //     list.getEntries().forEach(
                        //         (entry) => {
                        //             if (entry.name.includes("invoke/Gateway")) {
                        //                 theRes["timeCost"] = entry.responseStart - entry.requestStart;
                        //             }
                        //         }
                        //     );
                        // });
                        // observer.observe({ entryTypes: ["resource"] });
                        await invokeGatewayAction(coreURL,
                            contractName
                            , currentElement.gatewayID);
                        await sleep(300);
                        // observer.disconnect();
                        return { ...theRes }
                    }}
                    columns={TestResultColumns} />
                    : null}
            </div>
        );



    if (type === "message")
        return (
            <div>
                {showTransactionId ? <div>Transaction ID: {currentElement.fireflyTranID}</div> : null}
                <InputComponentForMessage
                    currentElement={currentElement}
                    contractName={contractName}
                    coreURL={coreURL}
                    bpmnName={bpmnName}
                    Identity={Identity}
                    contractMethodDes={contractMethodDes}
                    bpmn={bpmn}
                    bpmnInstance={bpmnInstance}
                />
            </div>

        );
}

import { useAllFireflyData } from './hook'
import axios from "axios";
import { includes } from "lodash";

const ExecutionPage = (props) => {
    const bpmnInstanceId = window.location.pathname.split("/").pop();
    const location = useLocation();
    const queryParams = new URLSearchParams(location.search);
    const coreUrl = 'http://' + queryParams.get("coreUrl");
    const participant = queryParams.get("participant");

    const [bpmnInstance, bpmnInstanceReady, syncBpmnInstance] = useBPMNIntanceDetailData(bpmnInstanceId);

    const [bpmnData, bpmnReady, syncBpmn] = useBPMNDetailData(bpmnInstance.bpmn);

    const getParticipantName = (participant) => {
        if (!bpmnReady) return "";
        const mapping = JSON.parse(bpmnReady ? bpmnData.participants : "[]");
        return mapping.find((item) => {
            return item.id === participant
        }
        ).name;
    }

    const contractMethodDes = JSON.parse(bpmnInstanceReady ? bpmnInstance.ffiContent : "{ }");

    const svgRef = useRef(null);
    const [svgContent, setSvgContent] = useState(null);
    const [svgStyle, setSvgStyle] = useState({});

    useEffect(() => {
        // set content to svgRef element
        if (svgRef.current && bpmnReady) {
            svgRef.current.innerHTML = bpmnData.svgContent;
        }
        return () => {
            // cleanup
        }
    }, [bpmnInstanceId, svgRef.current, bpmnReady])

    const [instance, instanceReady, syncInstance] = useBPMNIntanceDetailData(bpmnInstanceId);
    const contractName = instanceReady ? instance.chaincode_name + instance.chaincode_id.substring(0, 6) : "";
    const [allEvents, allGateways, allMessages, fireflyDataReady, syncFireflyData] = useAllFireflyData(coreUrl, contractName);

    const currentElements = [...allMessages, ...allEvents, ...allGateways].filter((msg) => {
        return msg.state === 1 || msg.state === 2;
    })

    const renderSvg = () => {
        const updatedMsgList = [...allMessages, ...allEvents, ...allGateways].map((msg) => {
            let color = "";
            // msgState, gatewayState, eventState;
            // State: 0: disabled, 1: enabled, 2: wait for confirm, 3: completed
            switch (msg.state) {
                case 0:
                    color = "unColored";
                    break;
                case 1:
                    color = "green";
                    break;
                case 2:
                    color = "red";
                    break;
                case 3:
                    color = "blue";
                    break;
                default:
                    color = "";
            }
            return { ...msg, color };
        });


        const generateStylesWithMsgList = (msgList) => {
            let styles = { "& svg": {} };
            msgList.forEach((msg) => {
                if (msg.color === "unColored" && msg.color === "") return;

                const selector = (() => {
                    if (msg.type === "event") return `& g[data-element-id="${msg.eventID}"]`
                    if (msg.type === "gateway") return `& g[data-element-id="${msg.gatewayID}"]`
                    if (msg.type === "message") return `& g[data-element-id="${msg.messageID}"]`
                })()
                styles["& svg"][selector] = {
                    "& path": {
                        fill: `${msg.color} !important`,
                    },
                    "& polygon": {
                        fill: `${msg.color} !important`,
                    },
                    "& circle": {
                        fill: `${msg.color} !important`,
                    },
                };
            });
            return styles;
        }
        const newStyles = generateStylesWithMsgList(
            updatedMsgList
        )
        setSvgStyle(newStyles);
    }


    useEffect(() => {
        renderSvg();
    }
        , [fireflyDataReady])


    // useEffect(() => {
    //     const task = setInterval(() => {
    //         syncFireflyData();
    //     }, 3000);
    //     return () => {
    //         clearInterval(task);
    //     }
    // }
    //     , []);

    return (
        <div className="Execution">

            <div
                dangerouslySetInnerHTML={{ __html: svgContent }}
                ref={svgRef}
                className={css(svgStyle)}
            />
            <Tag color="blue">Participant: {" " + getParticipantName(participant)}</Tag>

            <div style={{ display: "flex", marginTop: "20px" }}>
                {
                    currentElements.map((currentElement) => {
                        return <ControlPanel currentElement={currentElement}
                            contractName={contractName}
                            coreURL={coreUrl}
                            bpmnName={bpmnData.name}
                            contractMethodDes={contractMethodDes}
                            bpmn={bpmnData}
                            bpmnInstance={bpmnInstance}
                        />
                    }
                    )
                }
            </div>
            < Button
                onClick={() => {
                    syncFireflyData();
                }}
            >Refresh</Button>
        </div>
    );
};

export default ExecutionPage;