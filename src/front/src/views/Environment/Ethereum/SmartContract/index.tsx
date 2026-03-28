import React, { useEffect, useState } from "react";
import {
  Button,
  Form,
  Input,
  message,
  Modal,
  Select,
  Space,
  Table,
  Tag,
  Upload,
} from "antd";
import { UploadOutlined } from "@ant-design/icons";
import type { TableProps, UploadFile, UploadProps } from "antd";

import { useAppSelector } from "@/redux/hooks";
import {
  getEthContractDetail,
  getEthContractList,
  installEthContract,
} from "@/api/resourceAPI";

interface ContractRow {
  key: string;
  id: string;
  name: string;
  version: string;
  language: string;
  creator: string;
  filename: string;
  status: string;
  contract_address: string;
  deployment_tx_hash: string;
  create_time: string;
}

const compilerVersionOptions = [
  "0.8.24",
  "0.8.23",
  "0.8.22",
  "0.8.21",
  "0.8.20",
  "0.8.19",
  "0.8.18",
  "0.8.17",
  "0.8.16",
  "0.8.15",
  "0.7.6",
  "0.6.12",
].map((version) => ({
  label: version,
  value: version,
}));

const extractErrorMessage = (error: any, fallback: string) => {
  return (
    error?.data?.msg ||
    error?.data?.message ||
    error?.data?.detail ||
    error?.response?.data?.msg ||
    error?.response?.data?.message ||
    error?.response?.data?.detail ||
    error?.message ||
    fallback
  );
};

const toStatusTag = (status: string | null | undefined) => {
  const normalized = String(status || "NO").toUpperCase();
  if (["SUCCESS", "SUCCEEDED", "DEPLOYED", "COMPILED", "ACTIVATED"].includes(normalized)) {
    return <Tag color="green">{normalized}</Tag>;
  }
  if (["PENDING", "RUNNING", "STARTED", "PROCESSING", "UPLOADED"].includes(normalized)) {
    return <Tag color="processing">{normalized}</Tag>;
  }
  if (["FAILED", "ERROR"].includes(normalized)) {
    return <Tag color="red">{normalized}</Tag>;
  }
  return <Tag>{normalized}</Tag>;
};

const SmartContract: React.FC = () => {
  const currentEnvId = useAppSelector((state) => state.env.currentEnvId);
  const currentOrgId = useAppSelector((state) => state.org.currentOrgId);
  const [installForm] = Form.useForm();
  const [contracts, setContracts] = useState<ContractRow[]>([]);
  const [listLoading, setListLoading] = useState(false);
  const [installOpen, setInstallOpen] = useState(false);
  const [installLoading, setInstallLoading] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [activeContract, setActiveContract] = useState<any>(null);

  const syncContracts = async () => {
    if (!currentEnvId) {
      setContracts([]);
      return;
    }
    try {
      setListLoading(true);
      const response = await getEthContractList(currentEnvId);
      setContracts(response || []);
    } catch (error: any) {
      message.error(extractErrorMessage(error, "Load smart contract list failed"));
    } finally {
      setListLoading(false);
    }
  };

  useEffect(() => {
    syncContracts();
  }, [currentEnvId]);

  const resetInstallModal = () => {
    setInstallOpen(false);
    setFileList([]);
    installForm.resetFields();
  };

  const openInstallModal = () => {
    installForm.setFieldsValue({
      name: "",
      version: "1.0.0",
      contractName: "",
      compilerVersion: "0.8.19",
      namespace: "default",
      constructorArgsJson: "[]",
    });
    setInstallOpen(true);
  };

  const loadContractDetail = async (contractId: string) => {
    if (!currentEnvId || !contractId) {
      return;
    }
    try {
      setDetailLoading(true);
      const response = await getEthContractDetail(currentEnvId, contractId);
      setActiveContract(response);
      setDetailOpen(true);
    } catch (error: any) {
      message.error(extractErrorMessage(error, "Load smart contract detail failed"));
    } finally {
      setDetailLoading(false);
    }
  };

  const uploadProps: UploadProps = {
    beforeUpload: (file) => {
      setFileList([
        {
          uid: file.uid,
          name: file.name,
          status: "done",
          originFileObj: file,
        },
      ]);
      return false;
    },
    onRemove: () => {
      setFileList([]);
    },
    fileList,
    maxCount: 1,
    accept: ".sol,.zip,.tar,.tgz,.tar.gz",
  };

  const handleInstall = async () => {
    if (!currentEnvId || !currentOrgId) {
      message.error("Environment or organization is missing");
      return;
    }
    if (!fileList.length) {
      message.error("Please upload a Solidity file or archive");
      return;
    }
    try {
      const values = await installForm.validateFields();
      let constructorArgs: any[] = [];
      try {
        constructorArgs = values.constructorArgsJson
          ? JSON.parse(values.constructorArgsJson)
          : [];
      } catch (parseError) {
        message.error("Constructor args must be a valid JSON array");
        return;
      }
      if (!Array.isArray(constructorArgs)) {
        message.error("Constructor args must be a JSON array");
        return;
      }
      setInstallLoading(true);
      const result = await installEthContract({
        envId: currentEnvId,
        orgId: currentOrgId,
        name: values.name,
        version: values.version,
        contractName: values.contractName || undefined,
        compilerVersion: values.compilerVersion,
        namespace: values.namespace,
        constructorArgs,
        file: fileList[0]?.originFileObj as File,
      });
      message.success(
        result?.contract_address
          ? "Smart contract installed successfully"
          : "Smart contract request submitted"
      );
      resetInstallModal();
      await syncContracts();
      if (result?.contract_id) {
        await loadContractDetail(result.contract_id);
      }
    } catch (error: any) {
      if (error?.errorFields) {
        return;
      }
      message.error(extractErrorMessage(error, "Install smart contract failed"));
    } finally {
      setInstallLoading(false);
    }
  };

  const columns: TableProps<ContractRow>["columns"] = [
    {
      title: "Name",
      dataIndex: "name",
      key: "name",
    },
    {
      title: "Version",
      dataIndex: "version",
      key: "version",
    },
    {
      title: "Language",
      dataIndex: "language",
      key: "language",
    },
    {
      title: "Source",
      dataIndex: "filename",
      key: "filename",
      render: (value) => value || "-",
    },
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      render: (value) => toStatusTag(value),
    },
    {
      title: "Address",
      dataIndex: "contract_address",
      key: "contract_address",
      render: (value) => value || "-",
    },
    {
      title: "Creator",
      dataIndex: "creator",
      key: "creator",
    },
    {
      title: "Created At",
      dataIndex: "create_time",
      key: "create_time",
    },
    {
      title: "Action",
      key: "action",
      render: (_, record) => (
        <Space size="middle">
          <a style={{ cursor: "pointer" }} onClick={() => loadContractDetail(record.id)}>
            Detail
          </a>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Button type="primary" onClick={openInstallModal} style={{ marginBottom: 16 }}>
        Add Smart Contract
      </Button>
      <Table columns={columns} dataSource={contracts} loading={listLoading} />

      <Modal
        title="Add Smart Contract"
        open={installOpen}
        onOk={handleInstall}
        okText="Install"
        confirmLoading={installLoading}
        onCancel={resetInstallModal}
        destroyOnClose
      >
        <Form
          form={installForm}
          labelCol={{ span: 7 }}
          wrapperCol={{ span: 17 }}
          layout="horizontal"
          initialValues={{
            version: "1.0.0",
            compilerVersion: "0.8.19",
            namespace: "default",
            constructorArgsJson: "[]",
          }}
        >
          <Form.Item
            label="Name"
            name="name"
            rules={[{ required: true, message: "Please input package name" }]}
          >
            <Input placeholder="MyContractPackage" />
          </Form.Item>
          <Form.Item
            label="Version"
            name="version"
            rules={[{ required: true, message: "Please input version" }]}
          >
            <Input placeholder="1.0.0" />
          </Form.Item>
          <Form.Item
            label="Solidity Contract"
            name="contractName"
            rules={[
              {
                validator: (_, value) => {
                  if (!value || /^[A-Za-z_][A-Za-z0-9_]*$/.test(value)) {
                    return Promise.resolve();
                  }
                  return Promise.reject(
                    new Error("Use letters, numbers and underscores only")
                  );
                },
              },
            ]}
            extra="Optional. Only fill this when the source contains multiple deployable Solidity contracts."
          >
            <Input placeholder="Exact Solidity contract name, e.g. AssetRegistry" />
          </Form.Item>
          <Form.Item
            label="Compiler"
            name="compilerVersion"
            rules={[{ required: true, message: "Please choose a compiler version" }]}
          >
            <Select showSearch options={compilerVersionOptions} optionFilterProp="label" />
          </Form.Item>
          <Form.Item
            label="Namespace"
            name="namespace"
            rules={[{ required: true, message: "Please input FireFly namespace" }]}
          >
            <Input placeholder="default" />
          </Form.Item>
          <Form.Item
            label="Constructor Args"
            name="constructorArgsJson"
            rules={[
              {
                validator: (_, value) => {
                  if (!value) {
                    return Promise.resolve();
                  }
                  try {
                    const parsed = JSON.parse(value);
                    if (!Array.isArray(parsed)) {
                      return Promise.reject(new Error("Use a JSON array"));
                    }
                    return Promise.resolve();
                  } catch (error) {
                    return Promise.reject(new Error("Use valid JSON"));
                  }
                },
              },
            ]}
            extra='JSON array passed to the Solidity constructor, e.g. ["0x0000000000000000000000000000000000000000"]'
          >
            <Input.TextArea rows={3} placeholder='[]' />
          </Form.Item>
          <Form.Item label="Language">
            <Input value="solidity" disabled />
          </Form.Item>
          <Form.Item
            label="Upload"
            required
            extra="Support .sol, .zip, .tar, .tgz, .tar.gz"
          >
            <Upload {...uploadProps}>
              <Button icon={<UploadOutlined />}>Select File</Button>
            </Upload>
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="Smart Contract Detail"
        open={detailOpen}
        onCancel={() => setDetailOpen(false)}
        footer={[
          <Button key="close" onClick={() => setDetailOpen(false)}>
            Return
          </Button>,
        ]}
        width={860}
      >
        <Space direction="vertical" style={{ width: "100%" }}>
          <div>Name: {activeContract?.name || "-"}</div>
          <div>Version: {activeContract?.version || "-"}</div>
          <div>Status: {toStatusTag(activeContract?.status)}</div>
          <div>Language: {activeContract?.language || "-"}</div>
          <div>Source File: {activeContract?.filename || "-"}</div>
          <div>Contract Address: {activeContract?.contract_address || "-"}</div>
          <div>Deployment TX: {activeContract?.deployment_tx_hash || "-"}</div>
          <div>Namespace: {activeContract?.deployment?.namespace || "-"}</div>
          <div>Deployment ID: {activeContract?.deployment?.deployment_id || "-"}</div>
          <div>Deployment Status: {activeContract?.deployment?.status || "-"}</div>
          <div>Created At: {activeContract?.create_ts || "-"}</div>
          <div>Creator: {activeContract?.creator || "-"}</div>
          <div>
            Source Content:
            <pre
              style={{
                marginTop: 8,
                maxHeight: 320,
                overflow: "auto",
                background: "#0f172a",
                color: "#e2e8f0",
                padding: 12,
                borderRadius: 8,
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
              }}
            >
              {detailLoading ? "Loading..." : activeContract?.contract_content || "-"}
            </pre>
          </div>
        </Space>
      </Modal>
    </div>
  );
};

export default SmartContract;
