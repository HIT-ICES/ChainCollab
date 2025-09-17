import React, { useEffect, useState } from "react";
import { Table, Select } from "antd";
import { useTaskDataByBpmn } from "./hooks";
import { useERCListData } from "../../../ERC/hooks";

interface BindingTaskERCProps {
    bpmnId: string;
    taskERCMap?: Record<string, any>;
    setTaskERCMap?: React.Dispatch<React.SetStateAction<Record<string, any>>>;
}

export const BindingTaskERC: React.FC<BindingTaskERCProps> = ({ bpmnId, taskERCMap: parentMap, setTaskERCMap: setParentMap }) => {
    const [tasks, { isLoading }] = useTaskDataByBpmn(bpmnId);
    const [ercList] = useERCListData(bpmnId);


    const [localMap, setLocalMap] = useState<Record<string, any>>({});
    const taskERCMap = parentMap ?? localMap;
    const setTaskERCMap = setParentMap ?? setLocalMap;


    useEffect(() => {
        const newMap: Record<string, any> = {};

        Array.from(tasks.keys()).forEach((taskId: string) => {
            const oldValue = taskERCMap[taskId] || {}; // 保留已有值
            const task = Array.isArray(tasks)
                ? tasks.find((t: any) => t.id === taskId)
                : (tasks as Map<string, any>).get(taskId);

            newMap[taskId] = {
                [taskId + "_ERCID"]: oldValue[taskId + "_ERCID"] || "",
                [taskId + "_ERCName"]: oldValue[taskId + "_ERCName"] || "",
                tokenName: oldValue.tokenName || parseTokenName(task?.documentation),
                isBinded: oldValue.isBinded || false,
            };
        });

        setTaskERCMap(newMap);
    }, [tasks]);


    const parseTokenName = (documentation: any) => {
        if (!documentation) return "";
        try {
            const docObj =
                typeof documentation === "string"
                    ? JSON.parse(documentation.replace(/\n/g, "").trim())
                    : documentation;
            return docObj?.tokenName || "";
        } catch (err) {
            console.warn("Failed to parse documentation:", documentation, err);
            return "";
        }
    };
    const handleSelectChange = (taskId: string, ercId: string, ercName: string) => {
        setTaskERCMap((prev) => ({
            ...prev,
            [taskId]: {
                ...(prev[taskId] || {}),
                [taskId + "_ERCID"]: ercId,
                [taskId + "_ERCName"]: ercName,
                isBinded: !!ercId,
                tokenName: prev[taskId]?.tokenName || "",
            },
        }));
    };



    const columns = [
        {
            title: "TokenElement Name",
            dataIndex: "name",
            key: "name",
        },
        {
            title: "Token",
            dataIndex: "tokenName",
            key: "tokenName",
        },
        {
            title: "binding ERC",
            dataIndex: "id",
            key: "erc",
            render: (taskId: string, record: any) => {
                // record 就是当前行的数据，包含 { id, name, tokenName, ... }
                const filteredERCs = ercList.filter((erc) => {
                    return !erc.token || erc.token === record.tokenName;
                });

                return (
                    <Select
                        style={{ width: "100%" }}
                        value={taskERCMap[taskId]?.[taskId + "_ERCID"] || ""}
                        onChange={(value) => {
                            const selectedERC = filteredERCs.find((erc) => erc.id === value);
                            handleSelectChange(taskId, value, selectedERC?.name || "");
                        }}
                        options={filteredERCs.map((erc) => ({
                            value: erc.id,
                            label: erc.name,
                        }))}
                        allowClear
                    />
                );
            },
        },
    ];

    const dataSource = Array.isArray(tasks)
        ? tasks.map((task: any) => ({
            id: task.id,
            name: task.name,
            tokenName: parseTokenName(task.documentation),
            ...task,
        }))
        : Array.from((tasks as Map<string, any>).entries()).map(([id, info]) => ({
            id,
            name: info.name,
            tokenName: parseTokenName(info.documentation),
            ...info,
        }));


    return <Table dataSource={dataSource} columns={columns} rowKey="id" loading={isLoading} pagination={false} />;
};
