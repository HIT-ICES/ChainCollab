
import React, { useState } from 'react';
import { Card, Row, Col, Button, Typography, Steps, Modal, TableProps, Table, Select, Input, Tag } from "antd"
import { useLocation, useNavigate } from "react-router-dom";
import { useAppSelector } from "@/redux/hooks";
import { useParticipantsData, useAvailableMembers, useBPMNBindingData } from "./hooks"

const ParticipantList = () => {
 
  const location = useLocation();
  const bpmnInstanceId = location.pathname.split("/").pop();

  const [modalActive, setModalActive] = useState(false);
  const [validationType, setValidationType] = useState('equal');
  const [showUserSection, setShowUserSection] = useState(true);
  const [showMspSection, setShowMspSection] = useState(false);
  const [showAttributeSection, setShowAttributeSection] = useState(false);
  const currentEnvId = useAppSelector((state) => state.env.currentEnvId);
  const [attrRows, setAttrRows] = useState([{ attrName: '', equalValue: '' }]);
  const handleParticipantClick = () => {setModalActive(true);};
  const handleModalClose = () => {setModalActive(false);};
  const handleValidationTypeChange = (e) => {
    setValidationType(e.target.value);
    if (e.target.value === 'type') {
      setShowUserSection(false);
      setShowMspSection(true);
      setShowAttributeSection(true);
    } else {
      setShowUserSection(true);
      setShowMspSection(false);
      setShowAttributeSection(false);
    }
  };
  const handleAddRow = () => {const newRows = [...attrRows, { attrName: '', equalValue: '' }];setAttrRows(newRows);};

  const [alreadyBindings, syncAlreadyBindings] = useBPMNBindingData(bpmnInstanceId)
  const [bindings, setBindings] = useState<{}>({})
  const [usedMember, setUsedMember] = useState<string[]>([])
  const [participants, syncParticipants] = useParticipantsData(bpmnInstanceId)
  const [members, syncMembers] = useAvailableMembers(currentEnvId)
  

  let beforedUsedMember = []
      for (let key in alreadyBindings) {
          beforedUsedMember.push(alreadyBindings[key])
      }

  const participants1 = participants.map ( (a)  => {return <li onClick={handleParticipantClick}>{a.name}</li>})
  
  return (
  <div>
  <h1>参与方列表</h1>
  <ul className="participant-list">{participants1}</ul>
    {modalActive && (
      <div className="modal">
        <div className="modal-header">绑定参与方</div>
        <div className="modal-body">
          <label htmlFor="validationSelect">选择校验方式:</label>
          <select id="validationSelect" value={validationType} onChange={handleValidationTypeChange}>
            <option value="equal">相等</option>
            <option value="type">一类</option>
          </select>
          <br /><br />
          {showUserSection && (
            <div>
              <label htmlFor="userSelect">选择用户:</label>
              <select id="userSelect">
                <option value="user1">用户 1</option>
                <option value="user2">用户 2</option>
                <option value="user3">用户 3</option>
              </select>
              <br /><br />
            </div>
          )}
          {showMspSection && (
            <div>
              <label htmlFor="mspSelect">选择MSP (可选):</label>

              //这里可能不太对。。
              <Select
                style={{ width: "100%" }}
                defaultValue=""
                >
                          {
                              members.filter((item) => {
                                  return !beforedUsedMember.includes(item.membershipId) && !usedMember.includes(item.membershipId)
                              }).map((member) => {
                                  return (
                                      <Select.Option value={member.membershipId} key={member.membershipId}>
                                          {member.membershipName}
                                      </Select.Option>
                                  )
                              })
                          }
              </Select>
            </div>
          )}
          {showAttributeSection && (
            <div>
              <table className="attr-table">
                <thead>
                  <tr>
                    <th>Attr name</th>
                    <th>Equal value</th>
                  </tr>
                </thead>
                <tbody>
                  {attrRows.map((row, index) => (
                    <tr key={index}>
                      <td><input type="text" name="attrName[]" /></td>
                      <td><input type="text" name="equalValue[]" /></td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <button className="add-row-btn" onClick={handleAddRow}>添加一行</button>
            </div>
          )}
        </div>
        <div className="modal-footer">
          <button onClick={handleModalClose}>关闭</button>
        </div>
      </div>
    )}
  </div>
  );
};

export default ParticipantList;

//TODO:是不是应该加个"确定"按钮,以及处理逻辑？