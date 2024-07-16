import React, { useState } from "react";
import { Button, Input, Table, TableProps, } from "antd";
import { useAppSelector } from "@/redux/hooks.ts";
import { useNavigate } from "react-router-dom";

interface DataType {
  id: string;
  consortium: string;
  organization: string;
  name: string;
  dmnContent: string;
  svgContent: string;
}

import { useDmnListData } from './hooks.ts';

const DmnList: React.FC = () => {
  const currentConsortiumId = useAppSelector((state) => state.consortium.currentConsortiumId);
  const currentEnvId = useAppSelector((state) => state.env.currentEnvId);
  const currenEnvName = useAppSelector((state) => state.env.currentEnvName);
  const [dmnData, { isLoading, isError, isSuccess }, syncBpmnData] = useDmnListData(currentConsortiumId);


  const navigate = useNavigate();

  const [newOne, setNewOne] = useState({
    id: "new",
    name: "name",
    bpmn_id: "",
    status: "",
    environment_id: currentEnvId,
    environment_name: currenEnvName
  });


  const columns: TableProps<DataType>["columns"] = [
    {
      title: "DMN Name",
      dataIndex: "name",
      key: "name",
      align: "center",
    },
    {
      title: "Dmn id",
      dataIndex: "id",
      key: "id",
      align: "center",
    },
    {
      title: "OrgId",
      dataIndex: "organization",
      key: "OrgId",
      align: "center",
      hidden: true,
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
                console.log("click dmn detail", record);
              }}
            >
              Detail
            </Button>
            {/* <Button
              type="primary"
              style={{ marginLeft: 10 }}
              onClick={() => {
                setNewOne({
                  ...newOne,
                  bpmn_id: record.id
                })
                // expand the row
              }}
            >
              Add New Instance
            </Button> */}
            <Button
              type="primary"
              style={{ marginLeft: 10, background: "red" }}
              onClick={() => {
                const element = document.createElement('a');
                const file = new Blob([record.dmnContent], { type: 'text/plain' });
                element.href = URL.createObjectURL(file);
                element.download = "dmn.dmn";
                document.body.appendChild(element);
                element.click();
              }}
            >
              Export DMN
            </Button>
          </div>
        );
      },
    },
  ];

  return (
    <div>
      <Button type="primary" onClick={() => { }}>
        Create New Dmn
      </Button>
      <Table
        columns={columns}
        dataSource={dmnData ? dmnData.map((item) => { return { ...item, key: item.id } }) : null}
        scroll={{ y: 640 }}
      />
    </div>
  );
};

export default DmnList;
