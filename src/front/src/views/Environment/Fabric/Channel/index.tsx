import React, { useState } from "react";
import { Space, Table, Tag, Button, Modal, Form, Input, Select } from "antd";
import type { TableProps } from "antd";

interface Node {
  key: string;
  name: string;
  type: string;
}
interface DataType {
  key: string;
  name: string;
  network: string;
  // nodes: 包括其中存在的节点信息
  nodes?: Node[];
}
interface Network {
  key :string;
  name :string;
}

const initialData: DataType[] = [
  {
    key: "1",
    name: "Channel 1",
    network: "Network One",
    nodes: [
      {
        key: "1",
        name: "Node 1",
        type: "Peer",
      },
      {
        key: "2",
        name: "Node 2",
        type: "Peer",
      },
    ],
  },
  {
    key: "2",
    name: "Channel 2",
    network: "Network Two",
    nodes: [
      {
        key: "2",
        name: "Node 2",
        type: "Peer",
      },
      {
        key: "3",
        name: "Node 3",
        type: "Orderer",
      },
    ],
  },
  {
    key: "3",
    name: "Channel 3",
    network: "Network Three",
    nodes: [
      {
        key: "3",
        name: "Node 3",
        type: "Orderer",
      },
      {
        key: "4",
        name: "Node 4",
        type: "Orderer",
      },
    ],
  },
];

const initialNodes: Node[] = [
  {
    key: "1",
    name: "Node 1",
    type: "Peer",
  },
  {
    key: "2",
    name: "Node 2",
    type: "Peer",
  },
  {
    key: "3",
    name: "Node 3",
    type: "Orderer",
  },
  {
    key: "4",
    name: "Node 4",
    type: "Orderer",
  },
  {
    key: "5",
    name: "Node 5",
    type: "CA",
  },
  {
    key: "6",
    name: "Node 6",
    type: "CA",
  },
];

const initialNetworks: Network[] = [
  {
    key: "1",
    name: 'Network One'
  },
  {
    key: "2",
    name: 'Network Two'
  },
  {
    key: "3",
    name: 'Network Three'
  },
]

const Channel: React.FC = () => {
  const [data, setData] = useState<DataType[]>(initialData);
  const [selectedChannel, setSelectedChannel] = useState<DataType | null>(null);
  const [isModalVisible, setIsModalVisible] = useState(false);

  const [isAddModalVisible, setIsAddModalVisible] = useState(false);
  const [form] = Form.useForm();

  // 处理打开addchannel
  const handleAddChannel = () => {
    setIsAddModalVisible(true);
  };

  // 处理提交表单
  const handleAddFormSubmit = (values) => {
    const newChannel: DataType = {
      key: `new_${data.length + 1}`,
      name: values.name,
      network: values.network,
      nodes: initialNodes.filter(
        (node) =>
        (values.ordererNodes || []).includes(node.key) ||
        (values.peerNodes || []).includes(node.key) ||
        (values.CANodes || []).includes(node.key)
      ),
    };
    setData([...data, newChannel]);
    setIsAddModalVisible(false);
    form.resetFields();
  };

  // filter不同类型node
  const ordererNodes = initialNodes.filter((node) => node.type === "Orderer");
  const peerNodes = initialNodes.filter((node) => node.type === "Peer");
  const CANodes = initialNodes.filter((node) => node.type === "CA");
  const handleDelete = (key: string) => {
    setData(data.filter((item) => item.key !== key));
  };

  const handleDetails = (channel: DataType) => {
    setSelectedChannel(channel);
    setIsModalVisible(true);
  };

  const handleModalClose = () => {
    setIsModalVisible(false);
  };

  const columns: TableProps<DataType>["columns"] = [
    {
      title: "Name",
      dataIndex: "name",
      key: "name",
      align: "center",
      render: (text) => <a>{text}</a>,
    },
    {
      title: "Network",
      dataIndex: "network",
      key: "network",
      align: "center",
    },
    {
      title: "Action",
      key: "action",
      align: "center",
      render: (_, record: DataType) => (
        <Space size="middle">
          <a
            style={{ cursor: "pointer" }}
            onClick={() => handleDetails(record)}
          >
            Details
          </a>
          <a
            style={{ cursor: "pointer" }}
            onClick={() => handleDelete(record.key)}
          >
            Delete
          </a>
        </Space>
      ),
    },
  ];

  // Optional: Function to handle button click
  const handleAddChaincode = () => {
    // Implement action on button click
  };

  return (
    <div>
      <Button
        type="primary"
        onClick={handleAddChannel}
        style={{ marginBottom: 16 }}
      >
        Add Channel
      </Button>
      <Table columns={columns} dataSource={data} />

      {/* Add Channel */}
      <Modal
        title="Create Channel"
        open={isAddModalVisible}
        onOk={() => form.submit()}
        onCancel={() => setIsAddModalVisible(false)}
      >
        <Form form={form} layout="vertical" onFinish={handleAddFormSubmit}>
          <Form.Item
            name="name"
            label="Name"
            rules={[
              { required: true, message: "Please input the channel name!" },
            ]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            name="ordererNodes"
            label="Orderer Nodes"
            rules={[
              { required: false, message: "Please select orderer nodes!" },
            ]}
          >
            <Select mode="multiple" placeholder="Select orderer nodes">
              {ordererNodes.map((node) => (
                <Select.Option key={node.key} value={node.key}>
                  {node.name}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item
            name="peerNodes"
            label="Peer Nodes"
            rules={[{ required: false, message: "Please select peer nodes!" }]}
          >
            <Select mode="multiple" placeholder="Select peer nodes">
              {peerNodes.map((node) => (
                <Select.Option key={node.key} value={node.key}>
                  {node.name}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item
            name="CANodes"
            label="CA Nodes"
            rules={[{ required: false, message: "Please select CA nodes!" }]}
          >
            <Select mode="multiple" placeholder="Select CA nodes">
              {CANodes.map((node) => (
                <Select.Option key={node.key} value={node.key}>
                  {node.name}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
        </Form>
      </Modal>

      {/* Channel Details */}
      <Modal
        title="Channel Details"
        open={isModalVisible}
        onCancel={handleModalClose}
        footer={null}
      >
        {selectedChannel && (
          <div>
            <p>Name: {selectedChannel.name}</p>
            <p>Network: {selectedChannel.network}</p>
            <p>Nodes:</p>
            {selectedChannel.nodes?.map((node) => (
              <p key={node.key}>{`${node.type} - ${node.name}`}</p>
            ))}
          </div>
        )}
      </Modal>
    </div>
  );
};

export default Channel;
