import React, { useState } from "react";
import { Space, Table, Tag, Button, Modal, Form, Input, Select } from "antd";
import type { TableProps } from "antd";

interface DataType {
  key: string;
  name: string;
  type: string;
  createtime: string;
  state: string;
  creator: string;
}

// 渲染的数据
const initialData: DataType[] = [
  {
    key: "1",
    name: "Next.js",
    type: "peer",
    createtime: "2022-12-22 00:00",
    state: "created",
    creator: "System",
  },
  {
    key: "2",
    name: "Vue",
    type: "orderer",
    createtime: "2022-12-23 01:00",
    state: "created",
    creator: "HIT",
  },
  {
    key: "3",
    name: "Angular",
    type: "peer",
    createtime: "2022-12-24 02:00",
    state: "creating",
    creator: "testMembership",
  },
];

const Node: React.FC = () => {
  const [data, setData] = useState<DataType[]>(initialData);
  const [isModalVisible, setIsModalVisible] = useState(false);
  const [form] = Form.useForm();
  // 当前membership
  const [currentMembership, setCurrentMembership] =
    useState("defaultMembership");

  // 获取当前membership信息
  const getCurrMembership = () => {
    // 请求后端处理逻辑
    setCurrentMembership("");
  };

  const handleDelete = (key: string) => {
    setData(data.filter((item) => item.key !== key));
  };

  const handleAddNode = () => {
    setIsModalVisible(true);
  };

  const handleOk = () => {
    form
      .validateFields()
      .then((values) => {
        // Add new node with creating state
        const newNode: DataType = {
          key: `new_${data.length + 1}`, // Simple key generation, might need a better approach for unique keys
          name: values.name,
          type: values.type,
          createtime: getCurrentDateTime(),
          state: "creating",
          creator: currentMembership,
        };
        setData([...data, newNode]);
        setIsModalVisible(false);

        // Simulate async request and update state to 'created'
        // 使用延时模拟节点的creating过程，后期可以添加api获得返回参数修改
        setTimeout(() => {
          setData((prevData) =>
            prevData.map((item) =>
              item.key === newNode.key ? { ...item, state: "created" } : item
            )
          );
        }, 2000); // Simulating a request with 2 seconds delay
      })
      .catch((info) => {
      });
  };
  // 取消Modal操作
  const handleCancel = () => {
    setIsModalVisible(false);
  };

  //渲染的列表的格式
  const columns: TableProps<DataType>["columns"] = [
    {
      title: "Name",
      dataIndex: "name",
      key: "name",
      render: (text) => <a>{text}</a>,
    },
    {
      title: "Type",
      dataIndex: "type",
      key: "type",
    },
    {
      title: "Createtime",
      dataIndex: "createtime",
      key: "createtime",
    },
    {
      title: "Creator",
      dataIndex: "creator",
      key: "creator",
    },
    {
      title: "State",
      key: "state",
      dataIndex: "state",
      render: (state) => {
        let color = state === "creating" ? "geekblue" : "green";
        return (
          <Tag color={color} key={state}>
            {state}
          </Tag>
        );
      },
    },
    {
      title: "Action",
      key: "action",
      render: (_, record) => (
        <Space size="middle">
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

  return (
    <div>
      <Button
        type="primary"
        onClick={handleAddNode}
        style={{ marginBottom: 16 }}
      >
        Add Node
      </Button>
      <Table columns={columns} dataSource={data} />

      <Modal
        title="Create Node"
        open={isModalVisible}
        onOk={handleOk}
        onCancel={handleCancel}
      >
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="Name"
            rules={[{ required: true, message: "Please input the name!" }]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            name="type"
            label="Type"
            rules={[{ required: true, message: "Please select the type!" }]}
          >
            <Select placeholder="Select a type">
              <Select.Option value="peer">Peer</Select.Option>
              <Select.Option value="orderer">Orderer</Select.Option>
              <Select.Option value="CA">CA</Select.Option>
            </Select>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default Node;

function getCurrentDateTime() {
  const now = new Date();
  const year = now.getFullYear();
  const month = (now.getMonth() + 1).toString().padStart(2, "0");
  const day = now.getDate().toString().padStart(2, "0");
  const hour = now.getHours().toString().padStart(2, "0");
  const minute = now.getMinutes().toString().padStart(2, "0");
  return `${year}-${month}-${day} ${hour}:${minute}`;
}
