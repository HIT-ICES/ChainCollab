import React from "react";
import { Button, Table, TableProps } from "antd";
import { useAppSelector } from "@/redux/hooks";
import { useNavigate } from "react-router-dom";

import { useERCListData } from "./hooks";

interface ERCType {
  id: string;
  name: string;
  token_type: string;
  chaincode_content: string;
  ffi_content: string;
  installed: boolean;
  firefly_url?: string;
}

const ERCList: React.FC = () => {
  const currentConsortiumId = useAppSelector(
    (state) => state.consortium.currentConsortiumId
  );

  // 使用 react-query 风格的 Hook
  const [ercData, status, refetch] = useERCListData(currentConsortiumId);

  const navigate = useNavigate();

  const columns: TableProps<ERCType>["columns"] = [
    {
      title: "ERC Name",
      dataIndex: "name",
      key: "name",
      align: "center",
    },
    {
      title: "ERC Id",
      dataIndex: "id",
      key: "id",
      align: "center",
    },
    {
      title: "Token Type",
      dataIndex: "token_type",
      key: "token_type",
      align: "center",
    },
    {
      title: "Installed",
      dataIndex: "installed",
      key: "installed",
      align: "center",
      render: (val: boolean) => (val ? "✅ Yes" : "❌ No"),
    },
    {
      title: "Action",
      key: "action",
      align: "center",
      render: (_, record: ERCType) => {
        return (
          <div style={{ display: "flex" }}>
            <Button
              type="primary"
              onClick={() => {
                console.log("click ERC detail", record);
                // navigate(`/erc/${record.id}`) // 可跳转详情页
              }}
            >
              Detail
            </Button>
            <Button
              type="primary"
              style={{ marginLeft: 10, background: "red" }}
              onClick={() => {
                const element = document.createElement("a");
                const file = new Blob([record.chaincode_content], {
                  type: "text/plain",
                });
                element.href = URL.createObjectURL(file);
                element.download = `${record.name}_chaincode.go`;
                document.body.appendChild(element);
                element.click();
              }}
            >
              Export Chaincode
            </Button>
            <Button
              type="primary"
              style={{ marginLeft: 10, background: "green" }}
              onClick={() => {
                const element = document.createElement("a");
                const file = new Blob([record.ffi_content], {
                  type: "text/plain",
                });
                element.href = URL.createObjectURL(file);
                element.download = `${record.name}_ffi.json`;
                document.body.appendChild(element);
                element.click();
              }}
            >
              Export FFI
            </Button>
          </div>
        );
      },
    },
  ];

  return (
    <div>
      <Button type="primary" onClick={() => navigate("/erc/create")}>
        Create New ERC
      </Button>
      <Button
        style={{ marginLeft: 10 }}
        onClick={() => {
          refetch(); // react-query 风格刷新数据
        }}
      >
        Refresh
      </Button>

      {/* 可选：加载或错误状态提示 */}
      {status.isLoading && <p>Loading ERC List...</p>}
      {status.isError && <p>Error loading ERC List.</p>}

      <Table
        columns={columns}
        dataSource={ercData ? ercData.map((item) => ({ ...item, key: item.id })) : []}
        scroll={{ y: 640 }}
        loading={status.isLoading} // Table 内置 loading
      />
    </div>
  );
};

export default ERCList;
