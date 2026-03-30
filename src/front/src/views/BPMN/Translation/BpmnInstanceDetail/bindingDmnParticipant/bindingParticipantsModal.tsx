import React, { useEffect, useMemo, useState } from 'react';
import { Card, Row, Col, Button, Typography, Steps, Modal, TableProps, Table, Select, Input, Tag, List, Switch, message } from "antd"
import { useLocation, useNavigate } from "react-router-dom";
import { useAppSelector } from "@/redux/hooks";
import { useParticipantsData, useAvailableMembers } from "../hooks"
import { v4 as uuidv4 } from 'uuid';
import { useFabricIdentities } from '@/views/Consortium/FabricUsers/hooks';
import { useEthereumIdentities } from '@/views/Consortium/EthereumUsers/hooks';

import {getFabricIdentityList, getEthereumIdentityList, getMembershipList} from "@/api/platformAPI";
import { getResourceSets } from "@/api/resourceAPI";

const AttrTable = ({ dataSource, _setShowBingParticipantValue, clickedActionIndex }) => {

  // const [dataSource, setDataSource] = useState([]);
  const handleAddRow = () => {
    const newData = {
      key: uuidv4(),
      attr: '',
      value: '',
    };
    _setShowBingParticipantValue(clickedActionIndex, { "Attr": [...dataSource, newData] })
  };

  const handleDeleteRow = (key) => {
    const newData = dataSource.filter(item => item.key !== key);
    _setShowBingParticipantValue(clickedActionIndex, { "Attr": newData })
  };

  const handleInputChange = (key, field, value) => {
    const newData = dataSource.map(item => {
      if (item.key === key) {
        return { ...item, [field]: value };
      }
      return item;
    });
    _setShowBingParticipantValue(clickedActionIndex, { "Attr": newData })
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
            danger
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

interface membershipItemType {
  id: string;
  name: string;
  orgId: string;
  consortiumId: string;
}

interface bindingValueType {
  selectedValidationType?: string;
  selectedMembershipId?: string;
  selectedUser?: string;
  Attr?: Array<{ key: string; attr: string; value: string }>;
}

const normalizeBindingText = (value: string) =>
  String(value || "")
    .toLowerCase()
    .replace(/[^a-z0-9\u4e00-\u9fa5]+/g, " ")
    .trim();

const splitBindingTokens = (value: string) =>
  normalizeBindingText(value)
    .split(/\s+/)
    .filter(Boolean);

const scoreMembershipForParticipant = (participantName: string, membershipName: string) => {
  const participantNorm = normalizeBindingText(participantName);
  const membershipNorm = normalizeBindingText(membershipName);
  if (!participantNorm || !membershipNorm) return 0;
  if (participantNorm === membershipNorm) return 100;
  let score = 0;
  if (participantNorm.includes(membershipNorm) || membershipNorm.includes(participantNorm)) {
    score += 40;
  }
  const participantTokens = splitBindingTokens(participantName);
  const membershipTokens = splitBindingTokens(membershipName);
  const commonCount = membershipTokens.filter((token) => participantTokens.includes(token)).length;
  score += commonCount * 15;
  return score;
};

const BindingParticipantComponent = ({ clickedActionIndex, showBindingParticipantMap, setShowBindingParticipantMap, showBindingParticipantValueMap, setShowBindingParticipantValueMap, envId, envType }) => {

  const currentEnvId = useAppSelector((state) => state.env.currentEnvId);
  const currentEnvType = useAppSelector((state) => state.env.currentEnvType);
  const effectiveEnvId = envId || currentEnvId;
  const effectiveEnvType = envType || currentEnvType;

  // fetch datas
  const [identities, { isLoading, isError, isSuccess }, refetch] = effectiveEnvType === "Ethereum"
    ? useEthereumIdentities(effectiveEnvId, showBindingParticipantValueMap.get(clickedActionIndex)?.selectedMembershipId)
    : useFabricIdentities(effectiveEnvId, showBindingParticipantValueMap.get(clickedActionIndex)?.selectedMembershipId);
  const [members, syncMembers] = useAvailableMembers(effectiveEnvId)

  const [membershipList, setMembershipList] = useState<membershipItemType[]>([]);

  const renameMembership = (item: any): membershipItemType => ({
    id: item.id,
    name: item.name,
    orgId: item.loleido_organization,
    consortiumId: item.consortium,
  });

  const consortiumId = useAppSelector(
    (state) => state.consortium
  ).currentConsortiumId;

  useEffect(() => {
    const fetchAndSetData = async (consortiumId: string) => {
      const data = await getMembershipList(consortiumId);
      const newMembershipList = Array.isArray(data) ? data.map(renameMembership) : [];
      setMembershipList(newMembershipList);
    };

    if (consortiumId) {
      fetchAndSetData(consortiumId);
    }
  }, [consortiumId]);

  const _setShowBingParticipant = (id, updates) => {
    setShowBindingParticipantMap(prev => {
      const currentObj = prev.get(id) || {};
      const updatedObj = { ...currentObj, ...updates };
      return new Map(prev).set(id, updatedObj);
    });
  }

  const _setShowBingParticipantValue = (id, updates) => {
    setShowBindingParticipantValueMap(prev => {
      const currentObj = prev.get(id) || {};
      const updatedObj = { ...currentObj, ...updates };
      return new Map(prev).set(id, updatedObj);
    });
  }

  const handleValidationTypeChange = (value) => {
    _setShowBingParticipantValue(clickedActionIndex, { 'selectedValidationType': value })
    if (value === "group") {
      _setShowBingParticipant(clickedActionIndex, { "showUserSection": false, "showAttributeSection": true, 'showMspSection': true })
    } else if (value === 'equal') {
      _setShowBingParticipant(clickedActionIndex, { "showUserSection": true, "showAttributeSection": false, 'showMspSection': true })
    } else {
      _setShowBingParticipant(clickedActionIndex, { "showUserSection": true, "showAttributeSection": false, 'showMspSection': true })
    }
  };

  return (
    <div>{
      clickedActionIndex && (
        <Card>
          <div style={{
            display: 'flex',        // 使用Flexbox布局
            justifyContent: 'space-between', // 子元素间隔均匀分布
            alignItems: 'center',   // 垂直居中对齐子元素
            width: '100%',          // 容器宽度为100%
            marginBottom: '10px'    // 可选，为行添加底部间距
          }}>
            <label htmlFor="validationSelect">选择校验方式 :</label>
            <Select id="validationSelect" value={showBindingParticipantValueMap.get(clickedActionIndex)?.selectedValidationType} onChange={handleValidationTypeChange} style={{ width: 'auto', flexGrow: 1, paddingLeft: "10px" }}>
              <Select.Option value="equal">相等</Select.Option>
              <Select.Option value="group">一类</Select.Option>
            </Select>
          </div>
          <div style={{
            display: 'flex',        // 使用Flexbox布局
            justifyContent: 'space-between', // 子元素间隔均匀分布
            alignItems: 'center',   // 垂直居中对齐子元素
            width: '100%',          // 容器宽度为100%
            marginBottom: '10px'    // 可选，为行添加底部间距
          }}>
            {showBindingParticipantMap.get(clickedActionIndex)?.showMspSection && (
              <div>
                <label htmlFor="mspSelect">
                  {showBindingParticipantValueMap.get(clickedActionIndex)?.selectedValidationType === 'equal' ? '选择Membership :' : '选择Membership(可选) :'}
                </label>
                <Select
                  style={{ width: 'auto', flexGrow: 1, paddingLeft: "10px" }}
                  defaultValue=""
                  value={showBindingParticipantValueMap.get(clickedActionIndex)?.selectedMembershipId}
                  onChange={(value) => {
                    // 处理选择MSP的事件
                    _setShowBingParticipantValue(clickedActionIndex, { 'selectedMembershipId': value })
                  }}
                >
                  <Select.Option value="" key="default">
                    请选择一个选项
                  </Select.Option>
                  {
                    membershipList.map((member) => {
                      return (
                        <Select.Option value={member.id} key={member.id}>
                          {member.name}
                        </Select.Option>
                      )
                    }) // 为Select添加一个空选项
                  }
                </Select>
              </div>
            )}
          </div>
          <div style={{
            display: 'flex',        // 使用Flexbox布局
            justifyContent: 'space-between', // 子元素间隔均匀分布
            alignItems: 'center',   // 垂直居中对齐子元素
            width: '100%',          // 容器宽度为100%
            marginBottom: '10px'    // 可选，为行添加底部间距
          }}>{
              showBindingParticipantMap.get(clickedActionIndex)?.showUserSection && showBindingParticipantValueMap.get(clickedActionIndex)?.selectedMembershipId && (
                <div style={{
                  display: 'flex',        // 使用Flexbox布局
                  justifyContent: 'space-between', // 子元素间隔均匀分布
                  alignItems: 'center',   // 垂直居中对齐子元素
                  width: '100%',          // 容器宽度为100%
                  marginBottom: '10px'    // 可选，为行添加底部间距
                }}>
                  <label htmlFor="userSelect">选择用户:</label>
                  <Select
                    id="userSelect"
                    value={showBindingParticipantValueMap.get(clickedActionIndex)?.selectedUser}
                    onChange={(value) => {
                      // 处理选择MSP的事件
                      _setShowBingParticipantValue(clickedActionIndex, { 'selectedUser': value })
                    }}
                    style={{ width: 'auto', flexGrow: 1, paddingLeft: "10px" }}>
                    {
                      identities.map((user) => {
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
              showBindingParticipantMap.get(clickedActionIndex)?.showAttributeSection && (
                <AttrTable
                  dataSource={showBindingParticipantValueMap.get(clickedActionIndex)?.Attr || []}
                  _setShowBingParticipantValue={_setShowBingParticipantValue}
                  clickedActionIndex={clickedActionIndex}>
                </AttrTable>
              )
            }
          </div>
        </Card >
      )
    }
    </div >)
};


export const BindingParticipant = ({ participants, showBindingParticipantMap, setShowBindingParticipantMap, showBindingParticipantValueMap, setShowBindingParticipantValueMap, envId, envType
}) => {

  const [clickedActionIndex, setClickedActionIndex] = useState("");
  const [autoBinding, setAutoBinding] = useState(false);
  const [useFirstMembershipForAll, setUseFirstMembershipForAll] = useState(false);
  const currentEnvId = useAppSelector((state) => state.env.currentEnvId);
  const currentEnvType = useAppSelector((state) => state.env.currentEnvType);
  const effectiveEnvId = envId || currentEnvId;
  const effectiveEnvType = envType || currentEnvType;
  const consortiumId = useAppSelector(
    (state) => state.consortium
  ).currentConsortiumId;
  const [membershipList, setMembershipList] = useState<membershipItemType[]>([]);

  const renameMembership = (item: any): membershipItemType => ({
    id: item.id,
    name: item.name,
    orgId: item.loleido_organization,
    consortiumId: item.consortium,
  });

  useEffect(() => {
    const fetchAndSetData = async (targetConsortiumId: string) => {
      const data = await getMembershipList(targetConsortiumId);
      const newMembershipList = Array.isArray(data) ? data.map(renameMembership) : [];
      setMembershipList(newMembershipList);
    };

    if (consortiumId) {
      fetchAndSetData(consortiumId);
    }
  }, [consortiumId]);

  const currentBindings = useMemo(() => {
    return participants.map((participant) => {
      const binding = (showBindingParticipantValueMap.get(participant.id) || {}) as bindingValueType;
      const membershipName = membershipList.find((item) => item.id === binding.selectedMembershipId)?.name || "";
      return {
        participantId: participant.id,
        selectedValidationType: binding.selectedValidationType || "",
        selectedMembershipId: binding.selectedMembershipId || "",
        selectedUser: binding.selectedUser || "",
        membershipName,
      };
    });
  }, [participants, showBindingParticipantValueMap, membershipList]);

  const setParticipantBindingState = (participantId: string, updates: Record<string, any>) => {
    setShowBindingParticipantMap(prev => {
      const currentObj = prev.get(participantId) || {};
      const updatedObj = { ...currentObj, ...updates };
      return new Map(prev).set(participantId, updatedObj);
    });
  };

  const setParticipantBindingValue = (participantId: string, updates: Record<string, any>) => {
    setShowBindingParticipantValueMap(prev => {
      const currentObj = prev.get(participantId) || {};
      const updatedObj = { ...currentObj, ...updates };
      return new Map(prev).set(participantId, updatedObj);
    });
  };

  const handleAutoBind = async () => {
    if (!effectiveEnvId) {
      message.error("Environment is not selected");
      return;
    }
    if (useFirstMembershipForAll && membershipList.length === 0) {
      message.error("No memberships available for auto binding");
      return;
    }
    setAutoBinding(true);
    try {
      const nextMap = new Map(showBindingParticipantMap);
      const nextValueMap = new Map(showBindingParticipantValueMap);
      let autoBoundCount = 0;
      const firstMembershipId = membershipList[0]?.id || "";

      for (const participant of participants) {
        const bestMembership = membershipList
          .map((membership) => ({
            membership,
            score: scoreMembershipForParticipant(participant.name, membership.name),
          }))
          .sort((a, b) => b.score - a.score)[0];

        const selectedMembershipId = useFirstMembershipForAll
          ? firstMembershipId
          : bestMembership && bestMembership.score > 0
            ? bestMembership.membership.id
            : membershipList.length === 1
              ? membershipList[0].id
              : "";

        const currentValue = (nextValueMap.get(participant.id) || {}) as bindingValueType;
        const selectedUser = useFirstMembershipForAll
          ? ""
          : currentValue.selectedUser || "";
        const mergedValue: Record<string, any> = {
          selectedValidationType: currentValue.selectedValidationType || "equal",
          selectedMembershipId: useFirstMembershipForAll
            ? selectedMembershipId
            : currentValue.selectedMembershipId || selectedMembershipId,
          selectedUser,
          Attr: currentValue.Attr || [],
        };

        if (mergedValue.selectedValidationType === "equal" && mergedValue.selectedMembershipId && !mergedValue.selectedUser) {
          if (effectiveEnvType === "Ethereum") {
            const identities = await getEthereumIdentityList(effectiveEnvId, mergedValue.selectedMembershipId);
            if (Array.isArray(identities) && identities.length === 1) {
              mergedValue.selectedUser = identities[0].id;
            }
          } else {
            const resourceSets = await getResourceSets(effectiveEnvId, null, mergedValue.selectedMembershipId);
            const resourceSet = Array.isArray(resourceSets) && resourceSets.length > 0 ? resourceSets[0] : null;
            if (resourceSet?.id) {
              const identities = await getFabricIdentityList(resourceSet.id);
              if (Array.isArray(identities) && identities.length === 1) {
                mergedValue.selectedUser = identities[0].id;
              }
            }
          }
        }

        nextValueMap.set(participant.id, mergedValue);
        nextMap.set(participant.id, {
          ...((nextMap.get(participant.id) || {}) as Record<string, any>),
          showUserSection: mergedValue.selectedValidationType === "equal",
          showAttributeSection: mergedValue.selectedValidationType === "group",
          showMspSection: true,
        });

        if (mergedValue.selectedMembershipId) {
          autoBoundCount += 1;
        }
      }

      setShowBindingParticipantMap(nextMap);
      setShowBindingParticipantValueMap(nextValueMap);
      message.success(
        useFirstMembershipForAll
          ? `已按第一个 membership 自动填充 ${autoBoundCount}/${participants.length} 个 participant 绑定`
          : `已自动填充 ${autoBoundCount}/${participants.length} 个 participant 绑定`,
      );
    } catch (error: any) {
      message.error(error?.message || "自动绑定失败");
    } finally {
      setAutoBinding(false);
    }
  };

  const columns = [
    {
      title: "Participant",
      dataIndex: "participantName",
      key: "participant",
    },
    {
      title: "Binding",
      dataIndex: "binding",
      key: "binding",
      render: (_text, record) => {
        const binding = currentBindings.find((item) => item.participantId === record.participantId);
        if (!binding?.selectedMembershipId) {
          return <Tag>未绑定</Tag>;
        }
        return (
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
            <Tag color="blue">{binding.membershipName || binding.selectedMembershipId}</Tag>
            {binding.selectedUser ? <Tag color="green">{binding.selectedUser.slice(0, 8)}</Tag> : null}
          </div>
        );
      }
    },
    {
      title: "Action",
      dataIndex: "action",
      key: "action",
      render: (text, record) => {
        return (
          <Button
            onClick={() => {
              setClickedActionIndex(record.participantId)
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
    }
  })

  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'stretch' }}>
      <div style={{ flex: 1, marginRight: '20px' }}> {/* 为Table组件添加右边距 */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12, gap: 12 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <Switch
              checked={useFirstMembershipForAll}
              onChange={setUseFirstMembershipForAll}
            />
            <span>全部使用第一个 membership</span>
          </div>
          <Button type="primary" ghost loading={autoBinding} onClick={handleAutoBind}>
            一键自动绑定
          </Button>
        </div>
        <Table
          columns={columns}
          dataSource={data}
          pagination={false}
        />
      </div>
      <div style={{ flex: 1 }}> {/* 让BindingParticipantComponent占用剩余空间 */}
        <BindingParticipantComponent
          clickedActionIndex={clickedActionIndex}
          showBindingParticipantMap={showBindingParticipantMap}
          setShowBindingParticipantMap={setShowBindingParticipantMap}
          showBindingParticipantValueMap={showBindingParticipantValueMap}
          setShowBindingParticipantValueMap={setShowBindingParticipantValueMap}
          envId={envId}
          envType={envType}
        />
      </div>
    </div>

  );
};
