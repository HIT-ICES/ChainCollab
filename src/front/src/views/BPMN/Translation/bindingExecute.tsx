import { Modal, Table, Select, Button } from "antd"
import { useState, useEffect } from "react"
import { Binding } from "@/api/externalResource"
import { useParticipantsData, useAvailableMembers, useBPMNBindingData } from "./BpmnInstanceDetail/hooks"

export const BindingModal = ({
    bpmnInstanceId, envId, bpmnId,
    open, setOpen, syncExternalData
}) => {

    const [participants, syncParticipants] = useParticipantsData(bpmnId)
    const [members, syncMembers] = useAvailableMembers(envId)
    const [alreadyBindings, syncAlreadyBindings] = useBPMNBindingData(bpmnInstanceId)
    const syncAll = () => {
        syncParticipants()
        syncMembers()
        syncAlreadyBindings()
        syncExternalData()
    }

    let beforedUsedMember = []
    for (let key in alreadyBindings) {
        beforedUsedMember.push(alreadyBindings[key])
    }

    const [bindings, setBindings] = useState<{}>({})

    const [usedMember, setUsedMember] = useState<string[]>([])

    const handleBinding = () => {
        Promise.all(
            Object.keys(bindings).map((participant) => {
                return Binding(bpmnInstanceId, participant, bindings[participant])
            })
        ).then(() => {
            setOpen(false)
            syncAll()
        })
    }

    const binding = (participant: string, membershipId: string) => {
        setBindings({ ...bindings, [participant]: membershipId })
        setUsedMember([...usedMember, membershipId])
    }
    const clear = (participant: string) => {
        setBindings({})
    }

    const colums = [
        {
            title: "Participant",
            dataIndex: "participantName",
            key: "participant",
        },
        {
            title: "membership",
            dataIndex: "membership",
            key: "membership",
            render: (text, record) => {
                if (alreadyBindings[record.participantId]) {
                    return (
                        <span>
                            {alreadyBindings[record.participantId]}
                        </span>
                    )
                }
                return (
                    <Select
                        style={{ width: "100%" }}
                        defaultValue={text}
                        onChange={(value) => {
                            binding(
                                record.participantId,
                                value
                            )
                        }}
                    >
                        {
                            members.filter((item) => {
                                return !beforedUsedMember.includes(item.membershipId) && !usedMember.includes(item.membershipId)
                            }).map((member) => {
                                return (
                                    <Select.Option value={member.membershipId} key={member.membershipId}>
                                        {member.membershipName}
                                    </Select.Option>
                                )
                            })
                        }
                    </Select>
                )
            }
        }
    ]

    const data = participants.map((participant) => {
        return {
            participantName: participant.name,
            participantId: participant.id,
            membership: bindings[participant] ? bindings[participant] : ""
        }
    })


    return (
        <Modal
            title="Binding"
            open={open}
            onCancel={() => setOpen(false)}
            // Button
            onOk={() => { handleBinding() }}
            okText="确认"
            cancelText="取消"
        >
            <Table
                columns={colums}
                dataSource={data}
                pagination={false}
            />
        </Modal>
    )
}