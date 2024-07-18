import React, { useEffect, useState } from 'react';
import { Modal, Button } from 'antd';
import { BindingDmnModal } from './bindingDmnModal';
import { BindingParticipant } from './bindingParticipantsModal';
import { useBpmnSvg } from './hooks';

const ParticipantDmnBindingModal = ({ open, setOpen, bpmnId }) => {

  const [showBindingParticipantMap, setShowBindingParticipantMap] = useState(new Map());
  const [showBindingParticipantValueMap, setShowBindingParticipantValueMap] = useState(new Map());

  const handleOk = () => {
    setOpen(false);
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
              bpmnId={bpmnId}
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
