import React, { useState } from "react";
import { Button, Input, Table, TableProps, Modal } from "antd";
import { useAppSelector } from "@/redux/hooks.ts";
import { useNavigate } from "react-router-dom";
import ParticipantDmnBindingModal from "./BpmnInstanceDetail/bindingDmnParticipant/bingingModal-ParticiapantDmn.tsx";

interface DataType {
  id: string;
  consortium_id: string;
  organization_id: string;
  status: string;
  name: string;
  bpmnContent: string;
}

interface expendDataType {
  id: string;
  bpmn_id: string;
  status: string;
  name: string;
  environment_id: string;
  environment_name: string;
}

import { useBPMNInstanceListData } from './hooks.ts';

const ExpandedRowRender = ({ record }) => {

  const onClickExecute = (record: expendDataType) => {
    // navigate(`/bpmn/translation/${record.id}`);
    console.log("click execute", record);
  }

  const [data, syncData] = useBPMNInstanceListData(record.id);

  const expendColumns: TableProps<expendDataType>["columns"] = [
    {
      title: "BPMN Instance",
      dataIndex: "name",
      key: "BPMN Instance",
      align: "center",
    },
    {
      title: "Status",
      dataIndex: "status",
      key: "Status",
      align: "center",
    },
    {
      title: "Action",
      key: "action",
      align: "center",
      render: (_, record: expendDataType) => {
        return (
          <>
            <Button
              type="primary"
              onClick={() => {
                onClickExecute(record);
              }}
            >
              Execute
            </Button>
            {/* <Button
                type="primary"
                style={{ marginLeft: 10, background: "red" }}
                onClick={() => {
                  deleteBPMNInstance(record.id,
                    record.bpmn_id
                  );
                  syncData();
                }}
              >
                Delete
              </Button> */}
          </>)
      },
    }
  ]


  return (
    <Table
      columns={expendColumns}
      dataSource={data}
      pagination={false}
    />
  )
}

import { useBPMNListData } from './hooks.ts';

const Translation: React.FC = () => {
  const [bpmnData, syncBpmnData] = useBPMNListData();

  const currentEnvId = useAppSelector((state) => state.env.currentEnvId);
  const currenEnvName = useAppSelector((state) => state.env.currentEnvName);
  const navigate = useNavigate();
  const [isBindingOpen, setIsBindingOpen] = useState(false);


  const [currentBpmnId, setCurrentBpmnId] = useState("");


  const columns: TableProps<DataType>["columns"] = [
    {
      title: "BPMN",
      dataIndex: "name",
      key: "BPMN",
      align: "center",
    },
    {
      title: "BpmnC",
      dataIndex: "bpmnContent",
      key: "BpmnC",
      align: "center",
      hidden: true
    },
    {
      title: "OrgName",
      dataIndex: "organization_name",
      key: "OrgName",
      align: "center",
    },
    {
      title: "EnvName",
      dataIndex: "environment_name",
      key: "EnvName",
      align: "center",
    },
    {
      title: "Action",
      key: "action",
      align: "center",
      render: (_, record: DataType) => {
        return (
          <div style={{ display: "flex" }} >
            <Button
              type="primary"
              onClick={() => {
                console.log("click bpmn detail", record);
                navigate(`/bpmn/translation/${record.id}`);
              }}
            >
              Detail
            </Button>
            <Button
              type="primary"
              style={{ marginLeft: 10 }}
              disabled={record.status !== "Registered"}
              onClick={() => {
                // setNewOne({
                //   ...newOne,
                //   bpmn_id: record.id
                // })
                setCurrentBpmnId(record.id);
                setIsBindingOpen(true);
                // expand the row
              }}
            >
              Add New Instance
            </Button>
            <Button
              type="primary"
              style={{ marginLeft: 10, background: "red" }}
              onClick={() => {
                const element = document.createElement('a');
                const file = new Blob([record.bpmnContent], { type: 'text/plain' });
                element.href = URL.createObjectURL(file);
                element.download = "bpmn.bpmn";
                document.body.appendChild(element);
                element.click();
              }}
            >
              Export BPMN
            </Button>
          </div>
        );
      },
    },
  ];

  const [activeExpRows, setActiveExpRows] = useState([]);

  return (
    <div>
      <Table
        columns={columns}
        dataSource={bpmnData.map((item) => { return { ...item, key: item.id } })}
        scroll={{ y: 640 }}
        expandable={{
          expandedRowRender: (record: DataType) => {
            return (
              <ExpandedRowRender record={record}
              />
            )
          },
          expandedRowKeys: activeExpRows,
          onExpand: (expanded, record) => {
            const keys = expanded ? [record.id] : [];
            setActiveExpRows(keys);
          }
        }}
      />
      <ParticipantDmnBindingModal open={isBindingOpen} setOpen={setIsBindingOpen} bpmnId={currentBpmnId} />
    </div>
  );
};

export default Translation;
