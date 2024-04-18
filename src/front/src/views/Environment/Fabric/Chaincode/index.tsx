import React, { useState } from "react";
import {
  Space,
  Table,
  Tag,
  Button,
  Modal,
  Form,
  Input,
  Upload,
  message,
  Select
} from "antd";
import { UploadOutlined } from "@ant-design/icons";
import type { TableProps } from "antd";
import type { GetProp, UploadFile, UploadProps } from "antd";
import Detail from "./Detail/index";
import { useAppSelector } from "@/redux/hooks";
import { packageChaincode } from '@/api/resourceAPI'
import { useChaincodeData } from './hooks'
interface DataType {
  key: string;
  name: string;
  version: string;
  language: string;
}

const initialData: DataType[] = [
  {
    key: "1",
    name: "Next.js",
    version: "1.0.0",
    language: "C sharp",
  },
  {
    key: "2",
    name: "Vue",
    version: "2.0.0",
    language: "Java",
  },
  {
    key: "3",
    name: "Angular",
    version: "1.1.0",
    language: "Kotlin",
  },
];

const AddChaincodeModel = ({
  isModalVisible,
  setIsModalVisible,
  setSync,
}) => {
  const [form] = Form.useForm();
  const [fileList, setFileList] = useState<UploadFile[]>([]);

  const props: UploadProps = {
    onRemove: (file) => {
      const index = fileList.indexOf(file);
      const newFileList = fileList.slice();
      newFileList.splice(index, 1);
      setFileList(newFileList);
    },
    beforeUpload: (file) => {
      setFileList([...fileList, file]);
      return false;
    },
    fileList,
  };

  const currentEnvId = useAppSelector((state) => state.env.currentEnvId);
  const currentOrgId = useAppSelector((state) => state.org.currentOrgId);

  // 处理模态框的提交
  const handleOk = async () => {
    try {
      const values = await form.validateFields();
      const response = await packageChaincode({
        name: values.name,
        version: values.version,
        language: values.language,
        file: fileList[0],
        env_id: currentEnvId,
        org_id: currentOrgId
      });
      if (response) {
        message.success("Package chaincode successfully");
        setIsModalVisible(false);
        setSync();
      }
    } catch (error) {
      message.error("Package chaincode failed");
    }
  };



  return (
    <Modal
      title="Add Chaincode"
      open={isModalVisible}
      onOk={handleOk}
      onCancel={() => {
        setIsModalVisible(false);
        form.resetFields();
      }}
    >
      <Form
        form={form}
        labelCol={{ span: 8 }}
        wrapperCol={{ span: 16 }}
        layout="horizontal"
      >
        <Form.Item label="Name" name="name" rules={[{ required: true }]}>
          <Input />
        </Form.Item>
        <Form.Item
          label="Version"
          name="version"
          rules={[{ required: true }]}
        >
          <Input />
        </Form.Item>
        <Form.Item
          label="Language"
          name="language"
          rules={[{ required: true }]}
        >
          <Select>
            <Select.Option value="golang">GO</Select.Option>
            <Select.Option value="javascripts">JS</Select.Option>
            <Select.Option value="java">JAVA</Select.Option>
          </Select>
        </Form.Item>
        <Form.Item label="Upload" name="upload" rules={[{ required: true }]}>
          <Upload {...props}>
            <Button icon={<UploadOutlined />}>Select File</Button>
          </Upload>
        </Form.Item>
      </Form>
    </Modal>
  )

}


const Chaincode: React.FC = () => {
  // const [data, setData] = useState<DataType[]>(initialData);

  const [isInstallOpen, setIsInstallOpen] = useState(false)
  const handleInstall = () => {
    setIsInstallOpen(true);
  };
  // 处理模态框的取消
  const handleInstallCancel = () => {
    setIsInstallOpen(false);
  };


  const currentEnvId = useAppSelector((state) => state.env.currentEnvId);
  const [chainCodeList, setSync] = useChaincodeData(currentEnvId);
  const [activeChainCodeId, setActiveChainCodeId] = useState<string>("");

  const columns: TableProps<DataType>["columns"] = [
    {
      title: "Name",
      dataIndex: "name",
      key: "name",
      render: (text) => <a>{text}</a>,
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
      title: "Creator",
      dataIndex: "creator",
      key: "creator",
    },
    {
      title: "created_at",
      dataIndex: "create_time",
      key: "create_time",
    },
    {
      title: "Action",
      key: "action",
      render: (_, record) => (
        <Space size="middle">
          <a style={{ cursor: "pointer" }} onClick={() => { handleInstall(); setActiveChainCodeId(record.key) }}>
            Install
          </a>
        </Space>
      ),
    },
  ];
  const [isModalVisible, setIsModalVisible] = useState(false);


  // 显示模态框
  const handleAddChaincode = () => {
    setIsModalVisible(true);
  };



  return (
    <div>
      <Button
        type="primary"
        onClick={handleAddChaincode}
        style={{ marginBottom: 16 }}
      >
        Add Chaincode
      </Button>
      <Table columns={columns} dataSource={chainCodeList} />;
      <AddChaincodeModel isModalVisible={isModalVisible} setIsModalVisible={setIsModalVisible} setSync={setSync} />
      <Modal
        title="Details"
        open={isInstallOpen}
        onCancel={handleInstallCancel}
        style={{ width: '100%' }} // 设置宽度为100%
        width={' 85%'}
        footer={[
          <Button key="back" onClick={handleInstallCancel}>
            Return
          </Button>,
        ]}
      >
        <Detail chainCodeId={activeChainCodeId} />
      </Modal>
    </div>
  );
};

export default Chaincode;
