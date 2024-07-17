import React, { useState } from "react";
import { Button, Input, Table, TableProps, Modal } from "antd";
import { useAppSelector } from "@/redux/hooks.ts";
import { useNavigate } from "react-router-dom";
import ParticipantDmnBindingModal from "./BpmnInstanceDetail/bingingModal-ParticiapantDmn";

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
import { addBPMNInstance, deleteBPMNInstance } from "@/api/externalResource.ts";

const ExpandedRowRender = ({ record, appendedOne, setAppendedOne, submitNewOne }) => {

  const isAppend = record.id === appendedOne.bpmn_id;
  const navigate = useNavigate();
  const onClickViewDetail = (record: expendDataType) => {
    navigate(`/bpmn/translation/${record.id}`);
  }

  const [data, syncData] = useBPMNInstanceListData(record.id);

  const expendColumns: TableProps<expendDataType>["columns"] = [
    {
      title: "BPMN Instance",
      dataIndex: "name",
      key: "BPMN Instance",
      align: "center",
      render: (text, record) => {
        return record.id === "new" ? (
          <Input
            value={appendedOne.name}
            onChange={(e) => {
              setAppendedOne({
                ...appendedOne,
                name: e.target.value
              })
            }}
          />
        ) : (
          <span>{text}</span>
        );
      }
    },
    {
      title: "Environment",
      dataIndex: "environment_name",
      key: "Environment",
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
        return record.id === "new" ? (
          <Button
            type="primary"
            onClick={() => {
              submitNewOne(syncData)
            }}
          >
            Submit
          </Button>
        ) :
          (
            <>
              <Button
                type="primary"
                onClick={() => {
                  onClickViewDetail(record);
                }}
              >
                Detail
              </Button>
              <Button
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
              </Button>
            </>

          );
      },
    }
  ]


  return (
    <Table
      columns={expendColumns}
      dataSource={isAppend ? [...data,
        appendedOne
      ] : data}
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

  const [newOne, setNewOne] = useState({
    id: "new",
    name: "name",
    bpmn_id: "",
    status: "",
    environment_id: currentEnvId,
    environment_name: currenEnvName
  });



  const submitNewOne = async (syncLeaf) => {
    const res = await addBPMNInstance(newOne.bpmn_id, newOne.name, currentEnvId);
    setNewOne({
      id: "new",
      bpmn_id: '',
      name: '',
      status: '',
      environment_id: currentEnvId,
      environment_name: currenEnvName
    })
    syncBpmnData();
    if (syncLeaf)
      syncLeaf();
  }

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
      title: "OrgId",
      dataIndex: "organization_id",
      key: "OrgId",
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
            <Modal
              title="参与方列表"
              open={ParticipantListmodalVisible}
              onCancel={handleModalClose}
              footer={null}
            >
              <ParticipantListModel bpmnId={record.id} />
            </Modal>
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
                appendedOne={newOne}
                setAppendedOne={setNewOne}
                submitNewOne={submitNewOne}
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
