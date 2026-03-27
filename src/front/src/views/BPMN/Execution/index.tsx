import React, { useEffect, useState } from "react";
import { TableProps, Table, Tag, Button, Modal } from "antd";
import { CheckCircleOutlined, CloseCircleOutlined } from "@ant-design/icons";
import { useNavigate, useSearchParams } from "react-router-dom";
import {useAppSelector} from "@/redux/hooks.ts";
import { getBPMNInstanceList, getBPMNList } from "@/api/externalResource";
import { getFireflyList } from "@/api/resourceAPI";

interface DataType {
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
      const [searchParams] = useSearchParams();
      const isMockMode = searchParams.get("mode") === "mock";
      const [bpmnData, setBpmnData] = useState<DataType[]>([]);
      const currentConsortiumId = useAppSelector((state) => state.consortium).currentConsortiumId;
      const currentEnvId = useAppSelector((state) => state.env.currentEnvId);
      const currentOrgId = useAppSelector((state) => state.org.currentOrgId);
    const [selectedDataTypeId, setSelectedDataTypeId] = useState<string | null>(null);      //改为instanceid
    const [visible, setVisible] = useState(false);
    const [instanceDataList, setInstanceDataList] = useState<BpmnInstanceDataType[]>([]);
    const [fireflyData, setFireflyData] = useState<FireflyDataType[]>([]);
        // 获取bpmnData和participantsData
    useEffect(() => {
        const fetchData = async () => {
      // 获取bpmnData
    //   const res = await fetch("http://localhost:8000/api/v1/bpmns/1/_list");
    const data = await getBPMNList(currentConsortiumId);

      // 使用 filter 只保存 status 为 Deployed 的数据
    //   data = data.filter((item: DataType) => item.status === "executing");
      setBpmnData(data);
    };
    if (currentConsortiumId) {
      fetchData();
    } else {
      setBpmnData([]);
    }
  }, [currentConsortiumId]);

  useEffect(() => {
    if (!bpmnData.length) {
        setInstanceDataList([]);
        return;
    }
        const ids = bpmnData.map(item => item.id);

        const fetchInstanceData = async () => {
            const instanceDataPromises = ids.map(id => getBPMNInstanceList(id));
            const instanceDataArray = await Promise.all(instanceDataPromises);

            const instanceDataList = instanceDataArray.flat();

            setInstanceDataList(instanceDataList);
        };

        fetchInstanceData();

}, [bpmnData]);


    const handleClickDeploy = (id: string) => {
        if (isMockMode) {
            navigate(`./${id}?mode=mock`, { state: { id } });
            return;
        }
        setSelectedDataTypeId(id);
        setVisible(true);
        fetchFireflyData();
    };

    const handleSelectFirefly = (coreUrl: string, membershipId: string) => {
        // navigate(`./${selectedDataTypeId}/${id}`);
        navigate(`./${selectedDataTypeId}?coreUrl=${coreUrl}&membershipId=${membershipId}`);
        setVisible(false);
    };

    const fetchFireflyData = async () => {
        try {
            if (!currentEnvId) {
                setFireflyData([]);
                return;
            }
            const data = await getFireflyList(currentEnvId, currentOrgId || null);
            setFireflyData(data); // 保存从API返回的数据到状态中
        } catch (error) {
            console.error("Error fetching firefly data:", error);
            setFireflyData([]);
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
              {isMockMode ? "Mock Execute" : "Deploy"}
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
          {isMockMode ? null : (
            <Modal
                title="Select Firefly"
                open={visible}
                onCancel={() => setVisible(false)}
                footer={null}
            >
                <FireflyTable data={fireflyData} onSelect={handleSelectFirefly} />
            </Modal>
          )}
      </div>
  );
};

interface FireflyTableProps {
    onSelect: (coreUrl: string, membershipId: string) => void;
    data: FireflyDataType[];
}

const FireflyTable: React.FC<FireflyTableProps> = ({ onSelect, data }) => {
    const fireflyData: FireflyDataType[] = data;

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
