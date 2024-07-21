import { Modal, Table, Select, Button, Typography, Flex } from "antd"
const { Text } = Typography
import { useState, useEffect } from "react"
import { Binding, retrieveBPMN } from "@/api/externalResource"
import { useBusinessRulesDataByBpmn } from "./hooks"
import { useDmnListData } from "../../../Dmn/hooks"
import { useAppSelector } from "@/redux/hooks"
import { useDecisions } from "./hooks"
import { Tab } from "@mui/material"



const DmnBindingBlock = (
    {
        businessRuleToFullfill,
        isHandle,
        unSetHandle,
        getActivity,
        setActivity,
        unSetActivity,
        close
    }

) => {
    const currentConsortiumId = useAppSelector((state) => state.consortium.currentConsortiumId)
    const [dmns, { }, syncDmns] = useDmnListData(currentConsortiumId)
    const [dmnId, setDmnId] = useState<string>("")

    const dmnToUse = dmns.filter((dmn) => dmn.id === dmnId)
    const [decisions, { }, refreshDecisions] = useDecisions(dmnToUse.length > 0 ? dmnToUse[0].dmnContent : "")
    const mainDecision = decisions.find((decision) => decision.is_main)
    const availableInput = mainDecision?.inputs ?? []
    const availableOutput = mainDecision?.outputs ?? []

    const [currentParamMapping, setCurrentParamMapping] = useState({})

    useEffect(() => {

        if (!businessRuleToFullfill) {
            return
        }

        // init currentParamMapping based on businessRuleToFullfill'input and outputs, but not always empty
        const content = businessRuleToFullfill ? JSON.parse(businessRuleToFullfill.documentation) : {
            inputs: [], outputs: []
        }

        if (getActivity(businessRuleToFullfill.businessRuleId)) {
            const activity = getActivity(businessRuleToFullfill.businessRuleId)
            setCurrentParamMapping(activity.paramMapping)
            setDmnId(activity.dmnId)
            return
        }

        const newMap = {}
        content.inputs.map((input) => {
            newMap[input.name] = ""
        })
        setCurrentParamMapping(newMap)
    }, [businessRuleToFullfill])

    const checkParamMappingFullfill = () => {
        const content = businessRuleToFullfill ? JSON.parse(businessRuleToFullfill.documentation) : {
            inputs: [], outputs: []
        }
        const inputs = content.inputs
        const outputs = content.outputs
        const inputsFullfill = inputs.every((input) => {
            return currentParamMapping[input.name] !== ""
        })
        const outputsFullfill = outputs.every((output) => {
            return currentParamMapping[output.name] !== ""
        })

        return inputsFullfill && outputsFullfill
    }

    const handleOk = () => {
        if (!checkParamMappingFullfill()) {
            alert("Please fullfill the param mapping")
            return
        }
        setActivity(
            businessRuleToFullfill.businessRuleId,
            dmnId,
            mainDecision.id,
            swapMappingKeyValue(currentParamMapping),
            dmnToUse[0].dmnContent
        )
        close()

    }

    const handleCancel = () => {
        unSetHandle()
    }

    const handleReset = () => {
        unSetActivity(businessRuleToFullfill.businessRuleId)
    }

    const inputColumns = [
        // activity slot

        {
            title: "Activity Slot",
            dataIndex: "activitySlot",
            key: "activitySlot",
            render: (text, record) => {
                return (
                    <>
                        <Text>{record.activitySlot.name}</Text>
                        <br />
                        <Text>{"type: " + record.activitySlot.type}</Text>
                    </>
                )
            }
        },
        // available input choice in Select
        {
            title: "Available Input",
            dataIndex: "availableInput",
            key: "availableInput",
            render: (text, record) => {
                return (
                    <Select
                        style={{ width: "200px" }}
                        value={
                            currentParamMapping[record.activitySlot.name]
                        }
                        onChange={
                            (value) => {
                                setCurrentParamMapping({
                                    ...currentParamMapping,
                                    [record.activitySlot.name]: value
                                })
                            }
                        }
                    >
                        {
                            record.availableInput.map((input) => {
                                return (
                                    <Select.Option value={input.text}>{input.text + " type: " + input.typeRef}</Select.Option>
                                )
                            })
                        }
                    </Select>
                )
            }
        },
    ]

    const outPutColumns = [
        // activity slot

        {
            title: "Activity Slot",
            dataIndex: "activitySlot",
            key: "activitySlot",
            render: (text, record) => {
                return (
                    <>
                        <Text>{record.activitySlot.name}</Text>
                        <br />
                        <Text>{"type: " + record.activitySlot.type}</Text>
                    </>
                )
            }
        },
        // available input choice in Select
        {
            title: "Available Output",
            dataIndex: "availableInput",
            key: "availableInput",
            render: (text, record) => {
                return (
                    <Select
                        style={{ width: "200px" }}
                        value={
                            currentParamMapping[record.activitySlot.name]
                        }
                        onChange={
                            (value) => {
                                setCurrentParamMapping({
                                    ...currentParamMapping,
                                    [record.activitySlot.name]: value
                                })
                            }
                        }
                    >
                        {
                            record.availableInput.map((input) => {
                                return (
                                    <Select.Option value={input.name}>{input.name + " type:" + input.type}</Select.Option>
                                )
                            })
                        }
                    </Select>
                )
            }
        },
    ]



    const content = businessRuleToFullfill ? JSON.parse(businessRuleToFullfill.documentation) : {
        inputs: [], outputs: []
    }

    const inputDataSource = content.inputs.map((item) => {
        return {
            activitySlot: item,
            availableInput: availableInput
        }
    })

    const outputDataSource = content.outputs.map((item) => {
        return {
            activitySlot: item,
            availableInput: availableOutput
        }
    })


    return (
        <div style={{ width: "100%", display: isHandle ? "block" : "none" }}>
            {/* Dmn File Choose File */}
            <div style={{ display: 'flex', gap: '20px', alignContent: "center", justifyContent: "flex-start" }}>
                <Text style={{ width: '200px', display: 'inline-block' }} type="secondary" strong>Field Name</Text>
                <Select
                    style={{ width: '200px' }}
                    onChange={(value) => {
                        setDmnId(value)
                    }}
                >
                    {
                        dmns.map((dmn) => {
                            return (
                                <Select.Option value={dmn.id}>{dmn.name}</Select.Option>
                            )
                        })
                    }
                </Select>

            </div>
            {/* input and output; outer and inner */}
            {/*  */}
            <Text style={{ width: '200px', display: 'inline-block' }} type="secondary" strong>Input</Text>
            <Table columns={inputColumns} dataSource={
                inputDataSource
            }
                pagination={false}
            />
            <Table columns={outPutColumns} dataSource={
                outputDataSource
            }
                pagination={false}
            />

            {/* Ok Button And Cancel Button */}
            <div style={{ width: "100%", display: "flex", justifyContent: "flex-end", gap: "10px" }}>
                <Button type="primary" onClick={handleOk}>Ok</Button>
                <Button onClick={handleCancel}>Cancel</Button>
                <Button onClick={handleReset}>Reset</Button>
            </div>

        </div>
    )

    function swapMappingKeyValue(originMapping) {
        const swappedParamMapping = {}

        for (const key in originMapping) {
            const value = originMapping[key]
            swappedParamMapping[value] = key
        }
        return swappedParamMapping
    }
}


export const BindingDmnModal = ({
    bpmnId,
    DmnBindingInfo,
    setDmnBindingInfo
}) => {

    const [businessRules, { }, syncbusinessRules] = useBusinessRulesDataByBpmn(bpmnId)

    useEffect(() => {
        // Init businessRulesInfo
        const newMap = {}
        Object.keys(businessRules).map((businessRuleId) => {
            newMap[businessRuleId] = {
                [businessRuleId + "_DMNID"]: "",
                [businessRuleId + "_DecisionID"]: "",
                [businessRuleId + "_ParamMapping"]: {},
                [businessRuleId + "_Content"]: "",
                "isBinded": false
            }
        })
        setDmnBindingInfo(newMap)
    }, [businessRules])


    const getActivity = (businessRuleId) => {
        if (!DmnBindingInfo[businessRuleId]) {
            return null
        }
        if (!DmnBindingInfo[businessRuleId]["isBinded"]) {
            return null
        }

        return {
            "dmnId": DmnBindingInfo[businessRuleId][businessRuleId + "_DMNID"],
            "decisionId": DmnBindingInfo[businessRuleId][businessRuleId + "_DecisionID"],
            "paramMapping": DmnBindingInfo[businessRuleId][businessRuleId + "_ParamMapping"],
            "content": DmnBindingInfo[businessRuleId][businessRuleId + "_Content"]
        }
    }


    const setActivity = (businessRuleId, dmnId, decisionId, paramMapping, content) => {
        console.log(
            dmnId, content, decisionId
        )
        setDmnBindingInfo({
            ...DmnBindingInfo,
            [businessRuleId]: {
                ...DmnBindingInfo[businessRuleId],
                [businessRuleId + "_DMNID"]: dmnId,
                [businessRuleId + "_DecisionID"]: decisionId,
                [businessRuleId + "_ParamMapping"]: paramMapping,
                [businessRuleId + "_Content"]: content,
                "isBinded": true
            }
        })
    }
    const unSetActivity = (businessRuleId) => {
        setDmnBindingInfo({
            ...DmnBindingInfo,
            [businessRuleId]: {
                ...DmnBindingInfo[businessRuleId],
                [businessRuleId + "_DMNID"]: "",
                [businessRuleId + "_DecisionID"]: "",
                [businessRuleId + "_ParamMapping"]: {},
                [businessRuleId + "_Content"]: "",
                "isBinded": false
            }
        })
    }

    const [currentBusinessRuleId, setCurrentBusinessRuleId] = useState<string>("")
    const close = () => {
        setCurrentBusinessRuleId("")
    }

    const data = Object.entries(businessRules).map(([businessRuleId, value]) => {
        return {
            businessRuleName: value.name,
            businessRuleId: businessRuleId,
            documentation: value.documentation,
        }
    })

    const colums = [
        {
            title: "BusinessRuleTask Name",
            dataIndex: "businessRuleName",
            key: "businessRuleName",
            render: (text, record) => {
                if (record.businessRuleId === currentBusinessRuleId) {
                    return (
                        <Text type="success">{text}</Text>
                    )
                }

                return (
                    <Text>{text}</Text>
                )
            }
        },
        {
            title: "dmnName",
            dataIndex: "dmn",
            key: "dmn",
            render: (text, record) => {
                return (
                    <Button onClick={() => {
                        setCurrentBusinessRuleId(
                            record.businessRuleId
                        )
                    }} >绑定</Button>
                )
            }
        }
    ]
    const itemToHandle = data.find((item) => item.businessRuleId === currentBusinessRuleId)

    const isHandle = itemToHandle ? true : false
    console.log(DmnBindingInfo)
    return (
        <>
            <Table
                columns={colums}
                dataSource={data}
                pagination={false}
            />
            <DmnBindingBlock
                businessRuleToFullfill={itemToHandle}
                isHandle={isHandle}
                unSetHandle={() => {
                    setCurrentBusinessRuleId("")
                }}
                getActivity={getActivity}
                setActivity={setActivity}
                unSetActivity={unSetActivity}
                close={close}
            />
        </>

    )
}