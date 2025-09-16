import React, { useEffect, useState } from "react";
import { Button, Input, Modal, Select, Table, TableProps } from "antd";
import { useAppSelector } from "@/redux/hooks";
import { useNavigate } from "react-router-dom";

import { useERCListData } from "./hooks";
import { packageERC } from "@/api/externalResource";

interface ERCType {
  id: string;
  name: string;
  token_type: string;
  chaincode_content: string;
  ffi_content: string;
  installed: boolean;
  firefly_url?: string;
  token?: string;
}

const ERCList: React.FC = () => {
  const currentConsortiumId = useAppSelector(
    (state) => state.consortium.currentConsortiumId
  );
  const currentOrgId = useAppSelector((state) => state.org.currentOrgId);
  const currentEnvId = useAppSelector((state) => state.env.currentEnvId);

  const [ercData, status, refetch] = useERCListData(currentConsortiumId);


  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [tokens, setTokens] = useState([
    { name: "", type: "ERC20", chainCode: "", ffi: "", installed: false },
  ]);

  const [editingChainIndex, setEditingChainIndex] = useState<number | null>(null);
  const [editingChainContent, setEditingChainContent] = useState("");
  const [isChainModalOpen, setIsChainModalOpen] = useState(false);

  const [editingFFIIndex, setEditingFFIIndex] = useState<number | null>(null);
  const [editingFFIContent, setEditingFFIContent] = useState("");
  const [isFFIModalOpen, setIsFFIModalOpen] = useState(false);

  const [defaultChainCodeERC20, setDefaultChainCodeERC20] = useState("");
  const [defaultChainCodeERC721, setDefaultChainCodeERC721] = useState("");
  const [defaultFFIERC20, setDefaultFFIERC20] = useState("");
  const [defaultFFIERC721, setDefaultFFIERC721] = useState("");

  useEffect(() => {
    const loadDefaults = async () => {
      const res20 = await fetch("/ERC/ERC20.go");
      setDefaultChainCodeERC20(await res20.text());

      const res721 = await fetch("/ERC/ERC721.go");
      setDefaultChainCodeERC721(await res721.text());

      const ffi20 = await fetch("/ERC/ERC20.json");
      setDefaultFFIERC20(await ffi20.text());

      const ffi721 = await fetch("/ERC/ERC721.json");
      setDefaultFFIERC721(await ffi721.text());
    };
    loadDefaults();
  }, []);
  const handleChangeToken = (index: number, key, value: any) => {
    const newTokens = [...tokens];
    newTokens[index][key] = value;
    if (key === "type") {
      newTokens[index].chainCode = value === "ERC20" ? defaultChainCodeERC20 : defaultChainCodeERC721;
      newTokens[index].ffi = value === "ERC20" ? defaultFFIERC20 : defaultFFIERC721;
    }
    setTokens(newTokens);
  };

  const handleAddToken = (index: number, type: string = "ERC20") => {
    const newToken = {
      name: "",
      type,
      chainCode: type === "ERC20" ? defaultChainCodeERC20 : defaultChainCodeERC721,
      ffi: type === "ERC20" ? defaultFFIERC20 : defaultFFIERC721,
      installed: false,
    };
    const newTokens = [...tokens];
    newTokens.splice(index + 1, 0, newToken);
    setTokens(newTokens);
  };

  const handleRemoveToken = (index: number) => {
    setTokens(tokens.filter((_, i) => i !== index));
  };

  const handleViewChainCode = (index: number) => {
    setEditingChainIndex(index);
    setEditingChainContent(tokens[index].chainCode);
    setIsChainModalOpen(true);
  };

  const handleSaveChainCode = () => {
    if (editingChainIndex === null) return;
    const newTokens = [...tokens];
    newTokens[editingChainIndex].chainCode = editingChainContent;
    setTokens(newTokens);
    setIsChainModalOpen(false);
  };

  const handleViewFFI = (index: number) => {
    setEditingFFIIndex(index);
    setEditingFFIContent(tokens[index].ffi);
    setIsFFIModalOpen(true);
  };

  const handleSaveFFI = () => {
    if (editingFFIIndex === null) return;
    const newTokens = [...tokens];
    newTokens[editingFFIIndex].ffi = editingFFIContent;
    setTokens(newTokens);
    setIsFFIModalOpen(false);
  };

  const handleCreate = async () => {
    if (tokens.some((t) => !t.name.trim())) {
      alert("Token name cannot be empty");
      return;
    }
    console.log("Created tokens:", tokens); // 调用 API
    setIsCreateModalOpen(false);
    await packageERC(tokens, currentEnvId, currentOrgId, "1");
    setTokens([{ name: "", type: "ERC20", chainCode: defaultChainCodeERC20, ffi: defaultFFIERC20, installed: false }]);
    refetch();
  };

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
      title: "Token",
      dataIndex: "token",
      key: "token",
      align: "center",
      render: (val: string | undefined) => {
        if (!val) return "null";
        return (
          <span
            style={{
              display: "inline-block",
              maxWidth: 150,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
            title={val}
          >
            {val}
          </span>
        );
      },
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
      title: "Firefly URL",
      dataIndex: "firefly_url",
      key: "firefly_url",
      align: "center",
      render: (val: string | undefined) => {
        if (!val) return "null";
        return (
          <a href={val} target="_blank" rel="noopener noreferrer">
            🔗 firefly_url
          </a>
        );
      },
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
                navigate(`/orgs/${currentOrgId}/consortia/${currentConsortiumId}/envs/${currentEnvId}/fabric/chaincode`)//跳转
              }}
            >
              Install
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
      <Button type="primary" onClick={() => setIsCreateModalOpen(true)}>
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
      <Modal
        title="Create ERC Tokens"
        open={isCreateModalOpen}
        onCancel={() => setIsCreateModalOpen(false)}
        onOk={handleCreate}
        width="60%"
      >
        {tokens.map((token, index) => (
          <div
            key={index}
            style={{ display: "flex", gap: 10, marginBottom: 8, alignItems: "center" }}
          >
            <Input
              placeholder="Token Name"
              value={token.name}
              onChange={(e) => handleChangeToken(index, "name", e.target.value)}
              style={{ flex: 1 }}
            />

            <Select
              value={token.type}
              onChange={(value) => handleChangeToken(index, "type", value)}
              style={{ width: 120 }}
            >
              <Select.Option value="ERC20">ERC20</Select.Option>
              <Select.Option value="ERC721">ERC721</Select.Option>
            </Select>

            <Button size="small" onClick={() => handleViewChainCode(index)}>code</Button>
            <Button size="small" onClick={() => handleViewFFI(index)}>ffi</Button>

            <div style={{ display: "flex", gap: 5 }}>
              <Button size="small" type="dashed" onClick={() => handleAddToken(index, token.type)}>+</Button>
              <Button size="small" onClick={() => handleRemoveToken(index)}>-</Button>
            </div>
          </div>
        ))}

        <Button type="dashed" block onClick={() => handleAddToken(tokens.length - 1)}>
          + Add New Token
        </Button>

        {/* ChainCode Modal */}
        <Modal
          title="ChainCode"
          open={isChainModalOpen}
          onCancel={() => setIsChainModalOpen(false)}
          onOk={handleSaveChainCode}
          width="50%"
        >
          <Input.TextArea
            value={editingChainContent}
            onChange={(e) => setEditingChainContent(e.target.value)}
            style={{ width: "100%", height: 300 }}
          />
        </Modal>

        {/* FFI Modal */}
        <Modal
          title="FFI"
          open={isFFIModalOpen}
          onCancel={() => setIsFFIModalOpen(false)}
          onOk={handleSaveFFI}
          width="50%"
        >
          <Input.TextArea
            value={editingFFIContent}
            onChange={(e) => setEditingFFIContent(e.target.value)}
            style={{ width: "100%", height: 300 }}
          />
        </Modal>
      </Modal>

    </div>
  );
};

export default ERCList;
