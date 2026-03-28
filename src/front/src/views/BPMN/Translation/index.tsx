import React, { useState } from "react";
import { Button, Input, Table, TableProps, Modal, message } from "antd";
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

  const navigate = useNavigate()

  const onClickExecute = (record: expendDataType) => {
    navigate(`/bpmn/execution/${record.id}`);
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
                // Jump To Execution Page with param in url
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
import { importInitialBPMNs, updateBPMN } from "@/api/externalResource.ts";

const Translation: React.FC = () => {
  const [bpmnData, syncBpmnData] = useBPMNListData();
  const currentConsortiumId = useAppSelector((state) => state.consortium.currentConsortiumId);

  const currentEnvId = useAppSelector((state) => state.env.currentEnvId);
  const currenEnvName = useAppSelector((state) => state.env.currentEnvName);
  const navigate = useNavigate();
  const [isBindingOpen, setIsBindingOpen] = useState(false);


  const [currentBpmnId, setCurrentBpmnId] = useState("");
  const [isEditOpen, setIsEditOpen] = useState(false);
  const [editingRecord, setEditingRecord] = useState<DataType | null>(null);
  const [editingName, setEditingName] = useState("");
  const [editingContent, setEditingContent] = useState("");
  const [isSavingEdit, setIsSavingEdit] = useState(false);
  const [isImportingSeed, setIsImportingSeed] = useState(false);

  const openEditModal = (record: DataType) => {
    setEditingRecord(record);
    setEditingName(record.name || "");
    setEditingContent(record.bpmnContent || "");
    setIsEditOpen(true);
  };

  const handleSaveEdit = async () => {
    if (!editingRecord) return;
    if (!editingName.trim()) {
      message.error("BPMN name is required");
      return;
    }
    if (!editingContent.trim()) {
      message.error("BPMN content is required");
      return;
    }
    setIsSavingEdit(true);
    try {
      const res = await updateBPMN(
        editingRecord.id,
        {
          name: editingName.trim(),
          bpmnContent: editingContent,
        },
        currentConsortiumId || "1",
      );
      if (!res) {
        message.error("Failed to update BPMN");
        return;
      }
      message.success("BPMN updated");
      setIsEditOpen(false);
      syncBpmnData();
    } finally {
      setIsSavingEdit(false);
    }
  };

  const handleImportInitial = async () => {
    if (!currentConsortiumId) {
      message.warning("Please select a consortium first");
      return;
    }
    setIsImportingSeed(true);
    try {
      const res = await importInitialBPMNs(currentConsortiumId);
      if (!res?.data) {
        message.error("Failed to import initial BPMN files");
        return;
      }
      const info = res.data;
      message.success(
        `Initial BPMN loaded: imported=${info.imported}, skipped=${info.skipped}, failed=${info.failed}`,
      );
      syncBpmnData();
    } finally {
      setIsImportingSeed(false);
    }
  };


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
            <Button
              type="default"
              style={{ marginLeft: 10 }}
              onClick={() => {
                openEditModal(record);
              }}
            >
              Edit BPMN
            </Button>
          </div>
        );
      },
    },
  ];

  const [activeExpRows, setActiveExpRows] = useState([]);

  return (
    <div>
      <div style={{ marginBottom: 12 }}>
        <Button
          type="primary"
          loading={isImportingSeed}
          onClick={handleImportInitial}
        >
          Load Initial BPMN From Folder
        </Button>
      </div>
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
      <ParticipantDmnBindingModal
        open={isBindingOpen}
        setOpen={setIsBindingOpen}
        bpmnId={currentBpmnId}
        syncExternalData={syncBpmnData}
      />
      <Modal
        title={editingRecord ? `Edit BPMN: ${editingRecord.name}` : "Edit BPMN"}
        open={isEditOpen}
        onCancel={() => setIsEditOpen(false)}
        onOk={handleSaveEdit}
        confirmLoading={isSavingEdit}
        width={980}
        okText="Save"
      >
        <div style={{ marginBottom: 12 }}>
          <div style={{ marginBottom: 6 }}>Name</div>
          <Input
            value={editingName}
            onChange={(e) => setEditingName(e.target.value)}
            placeholder="BPMN Name"
          />
        </div>
        <div>
          <div style={{ marginBottom: 6 }}>BPMN XML Content</div>
          <Input.TextArea
            value={editingContent}
            onChange={(e) => setEditingContent(e.target.value)}
            rows={22}
            style={{ fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace" }}
          />
        </div>
      </Modal>
    </div>
  );
};

export default Translation;
