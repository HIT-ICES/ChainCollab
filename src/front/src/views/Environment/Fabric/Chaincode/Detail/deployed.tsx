import React, { useState } from "react";
import { TableProps, Table, Tag, Button, Card } from "antd";
import { CheckCircleOutlined, CloseCircleOutlined } from "@ant-design/icons";

interface Props {
  chaincodeId: string;
}

interface elementOfApprovals {
  membershipName: string;
  isApproved: boolean;
}


interface DataType {
  key: string;
  name: string;
  membershipApprovals: elementOfApprovals[];
  chaincodeCommitted: boolean;
}

import { useChannelData } from './hooks.ts';
import { useAppSelector } from "@/redux/hooks.ts";

import { retriveChaincode, approveChaincode, commitChaincode } from '@/api/resourceAPI'



const DeployedChannels: React.FC<Props> = ({ chaincodeId }) => {

  const currentEnvId = useAppSelector((state) => state.env.currentEnvId);
  const currentOrgId = useAppSelector((state) => state.org.currentOrgId);
  const [channelList, syncChannelList] = useChannelData(currentEnvId, chaincodeId);

  const handleChangeApproval = async (channelName: string, resourceSetId: string) => {
    const chaincode = await retriveChaincode(currentEnvId, chaincodeId);
    await approveChaincode(
      chaincode.name, chaincode.version, channelName, currentEnvId, resourceSetId
    )
    syncChannelList();
  }

  const handleCommit = async (channelName: string, resourceSetId: string) => {
    const chaincode = await retriveChaincode(currentEnvId, chaincodeId);
    await commitChaincode(
      chaincode.name, chaincode.version, channelName, currentEnvId, resourceSetId
    )
    syncChannelList();
  };

  const columns: TableProps<DataType>["columns"] = [
    {
      title: "Name",
      dataIndex: "name",
      key: "name",
      align: "center",
    },
    {
      title: "Membership Approvals",
      dataIndex: "membershipApprovals",
      key: "membershipApprovals",
      align: "center",
      children: [
        {
          title: "Name",
          dataIndex: "membershipApprovals",
          key: "name",
          align: "center",
          render: (membershipApprovals) => (
            <>
              {membershipApprovals.map((approval) => (
                <div key={approval.membershipName + "_name"} style={{ marginBottom: 8 }}>
                  {approval.membershipName}
                </div>
              ))}
            </>
          ),
        },
        {
          title: "Status",
          dataIndex: "membershipApprovals",
          key: "status",
          align: "center",
          render: (membershipApprovals, record) => {
            return (
              <>
                {/* {membershipApprovals.filter((item) => item.orgId === currentOrgId).map((approval) => { */}
                {membershipApprovals.map((approval) => {
                  const is_matched = approval.orgId === currentOrgId
                  if (is_matched) {
                    return (
                      <div
                        key={approval.membershipName + "_status"}
                        style={{ marginBottom: 8, display: 'flex', alignItems: 'center', width: '100%', justifyContent: 'center' }}
                      >
                        <Tag color={approval.isApproved ? "darkgreen" : "red"}>
                          {approval.isApproved}
                        </Tag>
                        <Button
                          size="small"
                          style={{ marginLeft: 8 }}
                          onClick={() => handleChangeApproval(record.name, approval.resourceSetId)}
                        >
                          approve
                        </Button>
                        <Button
                          size="small"
                          style={{ marginLeft: 8 }}
                          onClick={() => handleCommit(record.name, approval.resourceSetId)}
                        >
                          commit
                        </Button>
                      </div>
                    );
                  } else {
                    return (
                      <div
                        key={approval.membershipName + "_status"}
                        style={{ marginBottom: 8, display: 'flex', alignItems: 'center', width: '100%', justifyContent: 'center' }}
                      >
                        <Tag color={approval.isApproved ? "darkgreen" : "red"}>
                          {approval.isApproved}
                        </Tag>
                        <Button
                          size="small"
                          style={{ marginLeft: 8 }}
                          disabled
                        >
                          approve
                        </Button>
                        <Button
                          size="small"
                          style={{ marginLeft: 8 }}
                          disabled
                        >
                          commit
                        </Button>
                      </div>
                    );
                  }
                })}
              </>
            )
          },
        },
      ],
    },
    {
      title: "Chaincode Committed",
      dataIndex: "chaincodeCommitted",
      key: "chaincodeCommitted",
      align: "center",
      render: (committed, record) => {
        const color = committed;
        const icon =
          committed ? (
            <CheckCircleOutlined
              // green
              style={{ color: 'green' }}
            />
          ) : (
            <CloseCircleOutlined
              style={{ color: 'red' }}
            />
          );
        return (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '100%',
            height: '100%'
          }} >
            <Tag color={color} icon={icon} key={committed}>
              {committed}
            </Tag>
            {/* button */}

          </div>

        );
      },
    },
  ];


  return (
    <Table
      columns={columns}
      dataSource={channelList}
      pagination={{ pageSize: 5 }}
      scroll={{ y: 270 }}
    />
    // <></>
  );
};

export default DeployedChannels;
