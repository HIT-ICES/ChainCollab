import { Modal, Table, Select, Button } from "antd"
import { useState, useEffect } from "react"
import { Binding, retrieveBPMN } from "@/api/externalResource"
import { useBusinessRulesDataByBpmn } from "./hooks"
import { useDmnListData } from "../../../Dmn/hooks"
import { useAppSelector } from "@/redux/hooks"

export const BindingDmnModal = ({
    bpmnId
}) => {

    const currentConsortiumId = useAppSelector((state) => state.consortium.currentConsortiumId)

    const [businessRules, { }, syncbusinessRules] = useBusinessRulesDataByBpmn(bpmnId)
    const [dmns, { }, syncDmns] = useDmnListData(currentConsortiumId)


    const [bindings, setBindings] = useState<{}>({})

    const handleBinding = () => {
        // Promise.all(
        //     Object.keys(bindings).map((participant) => {
        //         return Binding(bpmnInstanceId, participant, bindings[participant])
        //     })
        // ).then(() => {
        //     setOpen(false)
        //     syncAll()
        // })
    }

    const binding = (businessRuleId: string, dmnId: string) => {
        setBindings({ ...bindings, [businessRuleId]: dmnId })
    }

    const colums = [
        {
            title: "BusinessRuleTask Name",
            dataIndex: "businessRuleName",
            key: "businessRuleName",
        },
        {
            title: "dmnName",
            dataIndex: "dmn",
            key: "dmn",
            render: (text, record) => {
                return (
                    <Select
                        style={{ width: "100%" }}
                        defaultValue={text}
                        onChange={(value) => {
                            binding(
                                record.businessRuleId,
                                value
                            )
                        }}
                    >
                        {
                            dmns.map((dmn) => {
                                return < Select.Option value={dmn.id} key={dmn.id} >
                                    {dmn.name}
                                </Select.Option>
                            }
                            )
                        }
                    </Select >
                )
            }
        }
    ]

    const data = Object.entries(businessRules).map(([businessRuleId, value]) => {
        return {
            businessRuleName: value.name,
            businessRuleId: businessRuleId,
            documentation: value.documentation,
            dmn: bindings[businessRuleId] ? bindings[businessRuleId] : ""
        }
    })


    return (
        <Table
            columns={colums}
            dataSource={data}
            pagination={false}
        />
    )
}