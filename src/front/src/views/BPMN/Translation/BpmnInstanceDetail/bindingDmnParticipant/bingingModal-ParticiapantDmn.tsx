import React, { useEffect, useState } from 'react';
import { Modal, Button, Alert } from 'antd';
import { BindingDmnModal } from './bindingDmnModal';
import { BindingParticipant } from './bindingParticipantsModal';
import { useBpmnSvg } from './hooks';
import { getMembership, retrieveFabricIdentity } from '@/api/platformAPI';
import { getFireflyList, getResourceSets } from '@/api/resourceAPI';
import { useAppSelector } from '@/redux/hooks';
import { useFireflyData, useParticipantsData } from '../hooks';
import { getFireflyVerify } from '@/api/executionAPI';

const ParticipantDmnBindingModal = ({ open, setOpen, bpmnId }) => {

  const [showBindingParticipantMap, setShowBindingParticipantMap] = useState(new Map());
  const [showBindingParticipantValueMap, setShowBindingParticipantValueMap] = useState(new Map());
  const currentEnvId = useAppSelector((state) => state.env.currentEnvId);
  const [errorMessage, setErrorMessage] = useState('');
  const [participants, syncParticipants] = useParticipantsData(bpmnId);

  const handleOk = async () => {
    const createInstanceParam = await constructParam();
    // 创建一个空对象
    let singleObject = {};

    // 遍历数组中的每个元素，并将其合并到singleObject中
    createInstanceParam.forEach((item) => {
      Object.assign(singleObject, item);
    });
    console.log('createInstanceParam', createInstanceParam);
    console.log('result', singleObject);

    async function constructParam() {
      const createInstanceParam = []
      showBindingParticipantValueMap.forEach(async (value, key) => {
        const selectedValidationType = value.selectedValidationType;
        if (selectedValidationType === 'group') {
          let msp = '';
          if (value.selectedMembershipId) {
            let memberships = await getResourceSets(currentEnvId, null, value.selectedMembershipId);
            msp = memberships[0].msp;
          }
          let attr = value.Attr;
          if (attr) {
            attr = attr.map(({ attr, value }) => ({ [attr]: value })).reduce((acc, obj) => {
              return { ...acc, ...obj };
            }, {});
          }
          createInstanceParam.push({
            [key]: {
              "msp": msp,
              "attributes": attr,
              "isMulti": true,
              "multiMaximum": 0,
              "multiMinimum": 0,
              "x509": "",
            }
          }
          );
        } else if (selectedValidationType === 'equal') {
          let msp = '';
          if (!value.selectedMembershipId) {
            setErrorMessage(`Participant ${participants.find(key)} membership is null`);
          }
          let memberships = await getResourceSets(currentEnvId, null, value.selectedMembershipId);
          msp = memberships[0].msp;
          if (!value.selectedUser) {
            setErrorMessage(`Participant ${participants.find(key)} user is null`);
          }
          const fabricIdentity = await retrieveFabricIdentity(value.selectedUser);
          const fireflyData = await getFireflyList(currentEnvId, null, fabricIdentity.membership);
          const fireflyCoreUrl = fireflyData[0].coreURL;
          const verify = await getFireflyVerify(fireflyCoreUrl, fabricIdentity.firefly_identity_id);
          const x509 = verify[0].value.split('::').slice(1).join('::');
          createInstanceParam.push({
            [key]: {
              "msp": msp,
              "attributes": '',
              "isMulti": false,
              "multiMaximum": 0,
              "multiMinimum": 0,
              "x509": x509,
            }
          }
          );
        }
      });
      return createInstanceParam
    }
    // setOpen(false);
  };

  const handleCancel = () => {
    setOpen(false);
  };

  return (
    <Modal title="Binding Dmns and Participants" open={open} onOk={handleOk} onCancel={handleCancel}
      style={{ minWidth: "1600px", textAlign: 'center' }}>
      <div>
        <div style={{ display: 'flex', marginBottom: '20px', height: '600px' }}>
          <div style={{ flex: '0 1 35%', paddingRight: '10px' }}>
            <h2>Binding BPMN businessRuleTasks and DMN</h2>
            <BindingDmnModal
              bpmnId={bpmnId}
            ></BindingDmnModal>
          </div>
          <div style={{ flex: '0 1 65%', paddingLeft: '10px', height: '600px' }}>
            <h2>Binding Participants</h2>
            <BindingParticipant
              participants={participants}
              showBindingParticipantMap={showBindingParticipantMap}
              setShowBindingParticipantMap={setShowBindingParticipantMap}
              showBindingParticipantValueMap={showBindingParticipantValueMap}
              setShowBindingParticipantValueMap={setShowBindingParticipantValueMap}
            ></BindingParticipant>
          </div>
        </div>
        <div style={{ textAlign: 'center', height: '400px' }}>
          <SVGDisplayComponent bpmnId={bpmnId} />
        </div>
        {errorMessage && (
          <Alert
            message={errorMessage}
            description="Error Description Error Description Error Description Error Description Error Description Error Description"
            type="error"
            closable
            onClose={() => setErrorMessage('')}
          />)}
      </div>
    </Modal>
  );
};

// TODO 调整SVG大小到固定尺寸
const SVGDisplayComponent = ({ bpmnId }) => {
  const [svgContent, { }, refreshSvg] = useBpmnSvg(bpmnId);

  return (
    <div
      style={{
        width: '100 %',/* 或者具体的px值 */
        height: 'auto' /* 保持SVG的宽高比 */
      }}
      dangerouslySetInnerHTML={{ __html: svgContent }}
    />
  );
}

export default ParticipantDmnBindingModal;
