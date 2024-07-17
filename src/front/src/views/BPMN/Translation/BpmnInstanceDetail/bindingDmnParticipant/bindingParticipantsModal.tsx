import React, { useState } from 'react';
import { Card, Row, Col, Button, Typography, Steps, Modal, TableProps, Table, Select, Input, Tag, List } from "antd"
import { useLocation, useNavigate } from "react-router-dom";
import { useAppSelector } from "@/redux/hooks";
import { useParticipantsData, useAvailableMembers } from "../hooks"
import { title } from 'process';
import { v4 as uuidv4 } from 'uuid';
import { useFabricIdentities } from '@/views/Consortium/FabricUsers/hooks';

export const BindingParticipant = ({ bpmnId }) => {


  const [bindings, setBindings] = useState<{}>({})
  const [participants, syncParticipants] = useParticipantsData(bpmnId)

  const [modalActive, setModalActive] = useState(false);
  const [validationType, setValidationType] = useState('equal');
  const [showUserSection, setShowUserSection] = useState(true);
  const [showAttributeSection, setShowAttributeSection] = useState(false);
  const currentEnvId = useAppSelector((state) => state.env.currentEnvId);
  const [currentSelectedMembershipId, setCurrentSelectedMembershipId] = useState("");
  const [fabricIdentities, { isLoading, isError, isSuccess }, refetch] = useFabricIdentities(currentEnvId, currentSelectedMembershipId);

  const handleValidationTypeChange = (value, evt) => {
    setValidationType(value);
    if (evt.children == "一类") {
      setShowUserSection(false);
      setShowAttributeSection(true);
    } else {
      setShowUserSection(true);
      setShowAttributeSection(false);
    }
  };
  const [members, syncMembers] = useAvailableMembers(currentEnvId)


  const columns = [
    {
      title: "Participant",
      dataIndex: "participantName",
      key: "participant",
    },
    {
      title: "Action",
      dataIndex: "action",
      key: "action",
      render: (text, record) => {
        return (
          <Button
            onClick={() => {
              console.log(record.id)
              setModalActive(true)
            }}>
            绑定
          </Button>
        )
      }
    }
  ]
  const data = participants.map(participant => {
    return {
      participantName: participant.name,
      participantId: participant.id,
      dmn: bindings[participant.id] ? bindings[participant.id] : ""
    }
  })

  const DynamicTable = () => {
    const [dataSource, setDataSource] = useState([]);

    const handleAddRow = () => {
      const newData = {
        key: uuidv4(),
        attr: '',
        value: '',
      };
      setDataSource([...dataSource, newData]);
    };

    const handleDeleteRow = (key) => {
      const newData = dataSource.filter(item => item.key !== key);
      setDataSource(newData);
    };

    const handleInputChange = (key, field, value) => {
      const newData = dataSource.map(item => {
        if (item.key === key) {
          return { ...item, [field]: value };
        }
        return item;
      });
      setDataSource(newData);
    };

    const columns = [
      {
        title: 'Attr',
        dataIndex: 'attr',
        key: 'attr',
        render: (text, record) => (
          <Input
            value={text}
            onChange={(e) => handleInputChange(record.key, 'attr', e.target.value)}
          />
        )
      },
      {
        title: 'Equal Value',
        dataIndex: 'value',
        key: 'value',
        render: (text, record) => (
          <Input
            value={text}
            onChange={(e) => handleInputChange(record.key, 'value', e.target.value)}
          />
        )
      },
      {
        title: 'Operation',
        dataIndex: 'operation',
        key: 'operation',
        render: (_, record) =>
          dataSource.length >= 1 ? (
            <Button
              type="danger"
              onClick={() => handleDeleteRow(record.key)}
            >
              Delete
            </Button>
          ) : null,
      },
    ];

    return (
      <div
        style={{
          display: 'flex',        // 使用Flexbox布局
          flexDirection: 'column', // 子元素垂直排列
          width: '100%'
        }}>
        <Table
          columns={columns}
          dataSource={dataSource}
          scroll={{ y: 200 }} // 以像素为单位，设置合适的值以显示大约5行
        />
        <Button
          onClick={handleAddRow}
          type="primary"
          style={{
            width: "30%", marginBottom: 16, marginTop: '10px', alignSelf: 'flex-end' // 设置按钮靠右侧显示
            // 与上方组件（表格）间距10px
          }}
        >
          Add a row
        </Button>
      </div>
    );
  }

  const BindingParticipantComponent = () => {
    return (
      <div>{
        modalActive && (
          <Card>
            <div style={{
              display: 'flex',        // 使用Flexbox布局
              justifyContent: 'space-between', // 子元素间隔均匀分布
              alignItems: 'center',   // 垂直居中对齐子元素
              width: '100%',          // 容器宽度为100%
              marginBottom: '10px'    // 可选，为行添加底部间距
            }}>
              <label htmlFor="validationSelect">选择校验方式 :</label>
              <Select id="validationSelect" value={validationType} onChange={handleValidationTypeChange} style={{ width: 'auto', flexGrow: 1, paddingLeft: "10px" }}>
                <Select.Option value="equal">相等</Select.Option>
                <Select.Option value="type">一类</Select.Option>
              </Select>
            </div>
            <div style={{
              display: 'flex',        // 使用Flexbox布局
              justifyContent: 'space-between', // 子元素间隔均匀分布
              alignItems: 'center',   // 垂直居中对齐子元素
              width: '100%',          // 容器宽度为100%
              marginBottom: '10px'    // 可选，为行添加底部间距
            }}>
              <label htmlFor="mspSelect">选择MSP (可选):</label>
              <Select
                style={{ width: 'auto', flexGrow: 1, paddingLeft: "10px" }}
                defaultValue=""
                value={currentSelectedMembershipId}
                onChange={(value) => {
                  // 处理选择MSP的事件
                  setCurrentSelectedMembershipId(value);
                }}
              >
                <Select.Option value="" key="default">
                  请选择一个选项
                </Select.Option>
                {
                  members.map((member) => {
                    return (
                      <Select.Option value={member.membershipId} key={member.membershipId}>
                        {member.membershipName}
                      </Select.Option>
                    )
                  }) // 为Select添加一个空选项
                }
              </Select>
            </div>
            <div style={{
              display: 'flex',        // 使用Flexbox布局
              justifyContent: 'space-between', // 子元素间隔均匀分布
              alignItems: 'center',   // 垂直居中对齐子元素
              width: '100%',          // 容器宽度为100%
              marginBottom: '10px'    // 可选，为行添加底部间距
            }}>{
                showUserSection && (
                  <div style={{
                    display: 'flex',        // 使用Flexbox布局
                    justifyContent: 'space-between', // 子元素间隔均匀分布
                    alignItems: 'center',   // 垂直居中对齐子元素
                    width: '100%',          // 容器宽度为100%
                    marginBottom: '10px'    // 可选，为行添加底部间距
                  }}>
                    <label htmlFor="userSelect">选择用户:</label>
                    <Select id="userSelect" style={{ width: 'auto', flexGrow: 1, paddingLeft: "10px" }}>
                      {
                        fabricIdentities.map((user) => {
                          return (
                            <Select.Option value={user.id} key={user.id}>
                              {user.name}
                            </Select.Option>
                          )
                        })
                      }
                    </Select>
                  </div>
                )
              }
            </div>
            <div style={{
              display: 'flex',        // 使用Flexbox布局
              justifyContent: 'space-between', // 子元素间隔均匀分布
              alignItems: 'center',   // 垂直居中对齐子元素
              width: '100%',          // 容器宽度为100%
              marginBottom: '5px',    // 可选，为行添加底部间距
            }}>
              {
                showAttributeSection && (
                  <DynamicTable></DynamicTable>
                )
              }
            </div>
            {/* <div style={{
                display: 'flex',
                justifyContent: 'flex-end',
                width: '100%',
              }}>
                <Button onClick={handleModalClose}>关闭</Button>
              </div> */}
          </Card >
        )
      }
      </div >)
  };

  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'stretch' }}>
      <div style={{ flex: 1, marginRight: '20px' }}> {/* 为Table组件添加右边距 */}
        <Table
          columns={columns}
          dataSource={data}
          pagination={false}
        />
      </div>
      <div style={{ flex: 1 }}> {/* 让BindingParticipantComponent占用剩余空间 */}
        <BindingParticipantComponent />
      </div>
    </div>

  );
};

