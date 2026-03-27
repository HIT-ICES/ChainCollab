import React, { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Checkbox,
  Form,
  Input,
  Modal,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from "antd";
import { useNavigate, useParams } from "react-router-dom";

import {
  createChainlinkJobForEthEnv,
  createChainlinkPresetJobForEthEnv,
  deleteChainlinkJobForEthEnv,
  getChainlinkJobForEthEnv,
  getChainlinkJobsForEthEnv,
  updateChainlinkJobForEthEnv,
} from "@/api/resourceAPI";
import { useAppSelector } from "@/redux/hooks";

const { Title, Text } = Typography;
const { TextArea } = Input;

const DEFAULT_NODES = ["chainlink1", "chainlink2", "chainlink3", "chainlink4"];

const extractError = (payload: any) => {
  return (
    payload?.data?.message ||
    payload?.data?.detail ||
    payload?.response?.data?.message ||
    payload?.response?.data?.detail ||
    payload?.message ||
    "Request failed"
  );
};

const ChainlinkJobs: React.FC = () => {
  const navigate = useNavigate();
  const params = useParams();
  const currentOrgId = useAppSelector((state) => state.org.currentOrgId);
  const currentConsortiumId = useAppSelector((state) => state.consortium.currentConsortiumId);
  const currentEnvId = useAppSelector((state) => state.env.currentEnvId);
  const envId = currentEnvId || params.env_id || "";

  const [jobs, setJobs] = useState<any[]>([]);
  const [nodeErrors, setNodeErrors] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [filterNode, setFilterNode] = useState<string>("all");

  const [createForm] = Form.useForm();
  const [createLoading, setCreateLoading] = useState(false);
  const [presetForm] = Form.useForm();
  const [presetLoading, setPresetLoading] = useState(false);

  const [replaceForm] = Form.useForm();
  const [replaceLoading, setReplaceLoading] = useState(false);

  const [detailOpen, setDetailOpen] = useState(false);
  const [detailPayload, setDetailPayload] = useState<any>(null);

  const nodeOptions = useMemo(
    () => [{ label: "All Nodes", value: "all" }, ...DEFAULT_NODES.map((n) => ({ label: n, value: n }))],
    []
  );

  const fetchJobs = async () => {
    if (!envId) {
      return;
    }
    setLoading(true);
    try {
      const res = await getChainlinkJobsForEthEnv(envId, filterNode === "all" ? undefined : filterNode);
      setJobs(Array.isArray(res?.items) ? res.items : []);
      setNodeErrors(Array.isArray(res?.errors) ? res.errors : []);
    } catch (error: any) {
      message.error(extractError(error));
      setJobs([]);
      setNodeErrors([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [envId, filterNode]);

  const handleCreate = async () => {
    if (!envId) {
      message.error("Environment is missing");
      return;
    }
    try {
      const values = await createForm.validateFields();
      setCreateLoading(true);
      const payload: any = {
        toml: values.toml,
        all_nodes: !!values.all_nodes,
      };
      if (!values.all_nodes) {
        payload.node = values.node;
      }
      const res = await createChainlinkJobForEthEnv(envId, payload);
      if (Array.isArray(res?.errors) && res.errors.length > 0) {
        message.warning(`Created with partial errors: ${res.errors.length}`);
      } else {
        message.success("Job created");
      }
      await fetchJobs();
    } catch (error: any) {
      message.error(extractError(error));
    } finally {
      setCreateLoading(false);
    }
  };

  const handleCreatePreset = async () => {
    if (!envId) {
      message.error("Environment is missing");
      return;
    }
    try {
      const values = await presetForm.validateFields();
      setPresetLoading(true);
      const payload: any = {
        job_kind: values.job_kind,
        recreate: !!values.recreate,
        sync_onchain: !!values.sync_onchain,
      };
      if (values.external_job_id) {
        payload.external_job_id = values.external_job_id;
      }
      if (values.job_kind === "datasource" && values.data_source_url) {
        payload.data_source_url = values.data_source_url;
      }
      if (values.job_kind === "datasource") {
        payload.data_source_method = values.data_source_method || "GET";
      }
      const res = await createChainlinkPresetJobForEthEnv(envId, payload);
      if (res?.task_id) {
        message.success(`Preset job task started: ${res.task_id}`);
      } else {
        message.success("Preset job request accepted");
      }
    } catch (error: any) {
      message.error(extractError(error));
    } finally {
      setPresetLoading(false);
    }
  };

  const handleDelete = (record: any) => {
    Modal.confirm({
      title: "Delete Chainlink Job",
      content: `Delete job ${record.id} on ${record.node}?`,
      okText: "Delete",
      okButtonProps: { danger: true },
      onOk: async () => {
        try {
          await deleteChainlinkJobForEthEnv(envId, record.id, record.node);
          message.success("Job deleted");
          await fetchJobs();
        } catch (error: any) {
          message.error(extractError(error));
        }
      },
    });
  };

  const handleView = async (record: any) => {
    try {
      const res = await getChainlinkJobForEthEnv(envId, record.id, record.node);
      setDetailPayload(res);
      setDetailOpen(true);
    } catch (error: any) {
      message.error(extractError(error));
    }
  };

  const handleReplace = async () => {
    if (!envId) {
      message.error("Environment is missing");
      return;
    }
    try {
      const values = await replaceForm.validateFields();
      setReplaceLoading(true);
      const res = await updateChainlinkJobForEthEnv(envId, values.job_id, {
        node: values.node,
        toml: values.toml,
      });
      message.success("Job replaced");
      await fetchJobs();
    } catch (error: any) {
      message.error(extractError(error));
    } finally {
      setReplaceLoading(false);
    }
  };

  const columns: any[] = [
    { title: "Node", dataIndex: "node", width: 120, render: (v: string) => <Tag color="blue">{v}</Tag> },
    { title: "Name", dataIndex: "name", ellipsis: true },
    { title: "Job ID", dataIndex: "id", width: 220, ellipsis: true },
    { title: "External Job ID", dataIndex: "externalJobID", width: 280, ellipsis: true },
    { title: "Type", dataIndex: "type", width: 140 },
    { title: "Created", dataIndex: "createdAt", width: 200, ellipsis: true },
    {
      title: "Actions",
      key: "actions",
      width: 220,
      render: (_: any, record: any) => (
        <Space>
          <Button size="small" onClick={() => handleView(record)}>
            View
          </Button>
          <Button
            size="small"
            onClick={() => {
              replaceForm.setFieldsValue({ job_id: record.id, node: record.node });
            }}
          >
            Use in Replace
          </Button>
          <Button size="small" danger onClick={() => handleDelete(record)}>
            Delete
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <Space direction="vertical" style={{ width: "100%" }} size={16}>
      <Space style={{ justifyContent: "space-between", width: "100%" }}>
        <Title level={4} style={{ margin: 0 }}>
          Chainlink Jobs
        </Title>
        <Space>
          <Button
            onClick={() =>
              navigate(`/orgs/${currentOrgId}/consortia/${currentConsortiumId}/envs/${envId}/envdashboard`)
            }
          >
            Back to Overview
          </Button>
          <Button type="primary" onClick={fetchJobs} loading={loading}>
            Refresh
          </Button>
        </Space>
      </Space>

      <Card size="small" title="List / Filter">
        <Space>
          <Text>Node</Text>
          <Select
            style={{ width: 180 }}
            value={filterNode}
            options={nodeOptions}
            onChange={(value) => setFilterNode(value)}
          />
        </Space>
      </Card>

      {nodeErrors.length > 0 ? (
        <Alert
          type="warning"
          showIcon
          message="Some nodes returned errors"
          description={
            <pre style={{ margin: 0, whiteSpace: "pre-wrap" }}>{JSON.stringify(nodeErrors, null, 2)}</pre>
          }
        />
      ) : null}

      <Card size="small" title="Create Preset Task Job">
        <Form
          form={presetForm}
          layout="vertical"
          initialValues={{
            job_kind: "dmn",
            recreate: false,
            sync_onchain: true,
            external_job_id: "",
            data_source_url: "",
            data_source_method: "GET",
          }}
        >
          <Space align="start" style={{ width: "100%" }}>
            <Form.Item name="job_kind" label="Task Kind" rules={[{ required: true }]}>
              <Select
                style={{ width: 200 }}
                options={[
                  { label: "DMN Task", value: "dmn" },
                  { label: "Data Source Task", value: "datasource" },
                ]}
                onChange={(value) => {
                  if (value === "datasource") {
                    presetForm.setFieldsValue({ sync_onchain: false });
                  } else {
                    presetForm.setFieldsValue({ sync_onchain: true });
                  }
                }}
              />
            </Form.Item>
            <Form.Item name="recreate" label="Recreate Existing" valuePropName="checked">
              <Checkbox />
            </Form.Item>
            <Form.Item name="sync_onchain" label="Sync on-chain Job ID" valuePropName="checked">
              <Checkbox />
            </Form.Item>
          </Space>
          <Form.Item name="external_job_id" label="External Job ID (Optional)">
            <Input placeholder="reuse existing externalJobID" />
          </Form.Item>
          <Form.Item noStyle shouldUpdate={(prev, next) => prev.job_kind !== next.job_kind}>
            {({ getFieldValue }) =>
              getFieldValue("job_kind") === "datasource" ? (
                <>
                  <Form.Item name="data_source_url" label="Data Source URL (Optional)">
                    <Input placeholder="https://api.example.com/data (empty => use request payload url)" />
                  </Form.Item>
                  <Form.Item name="data_source_method" label="Data Source Method">
                    <Select
                      style={{ width: 180 }}
                      options={[
                        { label: "GET", value: "GET" },
                        { label: "POST", value: "POST" },
                      ]}
                    />
                  </Form.Item>
                </>
              ) : null
            }
          </Form.Item>
          <Button type="primary" loading={presetLoading} onClick={handleCreatePreset}>
            Create Preset Job
          </Button>
        </Form>
      </Card>

      <Card size="small" title="Create Job">
        <Form
          form={createForm}
          layout="vertical"
          initialValues={{ node: "chainlink1", all_nodes: false, toml: "" }}
        >
          <Space align="start" style={{ width: "100%" }}>
            <Form.Item name="node" label="Node" rules={[{ required: true }]}>
              <Select style={{ width: 180 }} options={DEFAULT_NODES.map((n) => ({ label: n, value: n }))} />
            </Form.Item>
            <Form.Item name="all_nodes" label="All Nodes" valuePropName="checked">
              <Checkbox />
            </Form.Item>
          </Space>
          <Form.Item name="toml" label="TOML" rules={[{ required: true, message: "TOML is required" }]}>
            <TextArea rows={8} placeholder="type = &quot;directrequest&quot; ..." />
          </Form.Item>
          <Button type="primary" loading={createLoading} onClick={handleCreate}>
            Create Job
          </Button>
        </Form>
      </Card>

      <Card size="small" title="Replace Job (Update)">
        <Form form={replaceForm} layout="vertical" initialValues={{ node: "chainlink1", job_id: "", toml: "" }}>
          <Space align="start" style={{ width: "100%" }}>
            <Form.Item name="job_id" label="Job ID" rules={[{ required: true }]}>
              <Input style={{ width: 260 }} placeholder="job id" />
            </Form.Item>
            <Form.Item name="node" label="Node" rules={[{ required: true }]}>
              <Select style={{ width: 180 }} options={DEFAULT_NODES.map((n) => ({ label: n, value: n }))} />
            </Form.Item>
          </Space>
          <Form.Item name="toml" label="New TOML" rules={[{ required: true, message: "TOML is required" }]}>
            <TextArea rows={8} placeholder="new job TOML..." />
          </Form.Item>
          <Button type="primary" loading={replaceLoading} onClick={handleReplace}>
            Replace Job
          </Button>
        </Form>
      </Card>

      <Card size="small" title="Jobs">
        <Table
          rowKey={(record: any) => `${record.node}:${record.id}`}
          loading={loading}
          columns={columns}
          dataSource={jobs}
          pagination={{ pageSize: 10 }}
          scroll={{ x: 1400 }}
        />
      </Card>

      <Modal
        open={detailOpen}
        onCancel={() => setDetailOpen(false)}
        onOk={() => setDetailOpen(false)}
        width={980}
        title="Job Detail"
      >
        <pre style={{ margin: 0, whiteSpace: "pre-wrap", maxHeight: 520, overflow: "auto" }}>
          {JSON.stringify(detailPayload, null, 2)}
        </pre>
      </Modal>
    </Space>
  );
};

export default ChainlinkJobs;
