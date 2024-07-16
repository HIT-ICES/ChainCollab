import React, { useEffect, useState } from "react";
import { TableProps, Table, Tag, Button, Form, Select, Modal, Typography } from "antd";
import { CheckCircleOutlined, CloseCircleOutlined } from "@ant-design/icons";
import { useNavigate } from "react-router-dom";
import {useAppSelector} from "@/redux/hooks.ts";
import { getBPMNInstanceList, getBPMNList } from "@/api/externalResource";
import { current_ip } from "@/api/apiConfig";
const { Link } = Typography;

// interface DataType {
//   id: string;
//   BPMN: string;
//   Uploader: string;
//   status: string;
// }

interface DataType {
    // id: string;
    // consortium_id: string;
    // organization_id: string;
    // status: string;
    // name: string;
    // bpmnContent: string;
    // svgContent: string;
    // chaincodeContent: string;
    // ffiContent: string
    id: string;
    consortium: string;
    organization: string;
    name: string;
    participants: string;
    bpmnContent: string;
    svgContent: string;
}

interface FireflyDataType {
    id: string,
    orgName: string,
    coreUrl: string,
    sandboxUrl: string,
    membershipId: string,
    membershipName: string,
}

interface BpmnInstanceDataType {
    id: string;
    bpmn_id: string;
    status: string;
    name: string;
    environment_id: string;
    environment_name: string;
    chaincode_id: string;
    chaincode_content: string | null;
    firefly_url: string | null;
    ffiContent: string | null;
    create_at: string;
    update_at: string;
}

// redux获取当前org
// const org = useSelector((state: RootState) => state.org);、


const Execution: React.FC = () => {
      const navigate = useNavigate();
      const [bpmnData, setBpmnData] = useState<DataType[]>([]);
        const currentOrgId = useAppSelector((state) => state.org).currentOrgId;
    const [selectedDataTypeId, setSelectedDataTypeId] = useState<string | null>(null);      //改为instanceid
    const [visible, setVisible] = useState(false);
    const [instanceDataList, setInstanceDataList] = useState<BpmnInstanceDataType[]>([]);
    const [fireflyData, setFireflyData] = useState<FireflyDataType[]>([]);
        // 获取bpmnData和participantsData
    useEffect(() => {
        const fetchData = async () => {
      // 获取bpmnData
    //   const res = await fetch("http://localhost:8000/api/v1/bpmns/1/_list");
    const res = await getBPMNList(currentOrgId);        //先不写
    console.log(res);
    // const res = await getBPMNInstanceList(bpmnData.id)
      let data = res.data;

      // 使用 filter 只保存 status 为 Deployed 的数据
    //   data = data.filter((item: DataType) => item.status === "executing");
      setBpmnData(data);
    };
    fetchData();
  }, [currentOrgId]);

  useEffect(() => {
    if (bpmnData) {
        const ids = bpmnData.map(item => item.id);
        console.log(ids); 

        const fetchInstanceData = async () => {
            const instanceDataPromises = ids.map(id => getBPMNInstanceList(id));
            const instanceDataArray = await Promise.all(instanceDataPromises);
            console.log(instanceDataArray); 

            const instanceDataResult = instanceDataArray.map(item => item.data);
            console.log(instanceDataResult);

            const instanceDataList = [];
            instanceDataArray.forEach(item => {
                instanceDataList.push(...item.data);
            });
            console.log(instanceDataList);

            console.log("---------------------")
            console.log(bpmnData)

            setInstanceDataList(instanceDataList);
        };

        fetchInstanceData();

    }
}, [bpmnData]);


    const handleClickDeploy = (id: string) => {
        setSelectedDataTypeId(id);
        setVisible(true);
        fetchFireflyData();
    };

    const handleSelectFirefly = (coreUrl: string, membershipId: string) => {
        // navigate(`./${selectedDataTypeId}/${id}`);
        navigate(`./${selectedDataTypeId}?coreUrl=${coreUrl}&membershipId=${membershipId}`);
        setVisible(false);
    };

  const handleClick = (id: string) => {
    // const id = new Date().getTime(); // 使用当前时间作为id
    navigate(`./${id}`, {state :{id : id }}); // 导航到对应的页面
  };



    const fetchFireflyData = async () => {
        try {
            const res = await fetch(`${current_ip}:8000/api/v1/fireflys/1/start`);
            const data = await res.json();
            setFireflyData(data); // 保存从API返回的数据到状态中
        } catch (error) {
            console.error("Error fetching firefly data:", error);
        }
    };

  const columns: TableProps<BpmnInstanceDataType>["columns"] = [
      {
          title: "BPMNINSTANCE",
          dataIndex: "name",
          key: "BPMNINSTANCE",
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
          title: "update_at",  //Uploader改为了org
          dataIndex: "update_at",
          key: "update_at",
          align: "center",
      },
    {
      title: "Deployed Status",
      dataIndex: "status",
      key: "status",
      align: "center",
      render: (status) => {
        const color = status === "Registered" ? "success" : "error";
        const icon =
            status === "Registered" ? (
                <CheckCircleOutlined />
            ) : (
                <CloseCircleOutlined />
            );
        return (
            <Tag color={color} icon={icon} key={status}>
              {status}
            </Tag>
        );
      },
    },
    {
      title: "Action",
      key: "action",
      align: "center",
      render: (_, record: BpmnInstanceDataType) => {
        // if (record.Uploader === currOrg) {
        return (
            // <Button
            //     type="primary"
            //     onClick={() => handleClick(record.id)}
            // >
            <Button type="primary" onClick={() => handleClickDeploy(record.id)}>
              Deploy
            </Button>
        );
        // }
        // return null;
      },
    },
  ];

  return (
      <div>
        <Table
            columns={columns}
            dataSource={instanceDataList}
            pagination={{ pageSize: 50 }}
            scroll={{ y: 640 }}
        />
          <Modal
              title="Select Firefly"
              visible={visible}
              onCancel={() => setVisible(false)}
              footer={null}
          >
              <FireflyTable onSelect={handleSelectFirefly} />
          </Modal>
      </div>
  );
};

interface FireflyTableProps {
    onSelect: (coreUrl: string, membershipId: string) => void;
}

const FireflyTable: React.FC<FireflyTableProps> = ({ onSelect }) => {
    const fireflyData: FireflyDataType[] = []; // Assuming you have FireflyDataType data

    const columns: TableProps<FireflyDataType>["columns"] = [
        {
            title: "MembershipId",
            dataIndex: "membershipId",
            key: "MembershipId",
            align: "center",
        },
        {
                title: "MembershipName",
                dataIndex: "membershipName",
                key: "MembershipName",
                align: "center",
                // hidden: true
            },
        {
            title: "Select",
            key: "select",
            align: "center",
            render: (_, record: FireflyDataType) => (
                <Button type="primary" onClick={() => {
                    return onSelect(record.coreUrl, record.membershipId);
                }}>
                    Select
                </Button>
            ),
        },
    ];

    return (
        <Table
            columns={columns}
            dataSource={fireflyData}
            pagination={{ pageSize: 50 }}
            scroll={{ y: 400 }}
        />
    );
};



export default Execution;
