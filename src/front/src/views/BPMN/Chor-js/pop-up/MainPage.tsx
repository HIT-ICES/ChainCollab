import * as React from 'react';
import $ from 'jquery';
import { Button } from 'antd';
import AssetTaskModal from './AssetTaskModal'
import AssetModal from './AssetModal'
import MessageModal from './MessageModal';
import DmnModal from './DmnModal'
import TaskModal from './TaskModal';
import ParticipantModal from './ParticipantModal';
import { getAssetOperation } from '../utils/assetExtension';

export default function MainPage({ xmlDataMap, onSave }) {
  const [dataElementId, setDataElementId] = React.useState(null);
  const [dataElementType, setDataElementType] = React.useState(null);
  const [modalOpen, setModalOpen] = React.useState(false);

  React.useEffect(() => {
    const handleDoubleClick = (e) => {
      e.stopPropagation();
      const data_element_id = $(e.target).closest('.djs-element.djs-shape').attr('data-element-id');

      const modeler = window.bpmnjs;
      const elementRegistry = modeler.get('elementRegistry');
      const shape = elementRegistry.get(data_element_id);
      if (!shape) return;
      // console.log('data_element_id-shape', data_element_id, shape);
      const type = shape.type;
      const popupType = type === 'bpmn:ChoreographyTask' && getAssetOperation(shape)
        ? 'abc:AssetTask'
        : type;
      console.log('data_element_id-type', data_element_id, type);
      // const ids = data_element_id.split('_');
      // const type = ids[0];
      setDataElementId(data_element_id);
      setDataElementType(popupType);
      if (popupType === 'bpmn:BusinessRuleTask' || popupType === 'bpmn:Message' || popupType === 'abc:AssetTask' || popupType === 'abc:Asset') {
        setModalOpen(true);
      }
    }
    if (!modalOpen) {
      $(document).on('dblclick', '.djs-element.djs-shape', handleDoubleClick);
    } else {
      $(document).off('dblclick', '.djs-element.djs-shape', handleDoubleClick);
    }
    return () => $(document).off('dblclick', '.djs-element.djs-shape', handleDoubleClick);
  }, [modalOpen]);

  return (
    <div>
      {dataElementType === 'bpmn:Message' && dataElementId ? (
        <MessageModal
          dataElementId={dataElementId}
          open={modalOpen && 'bpmn:Message' === dataElementType}
          onClose={() => setModalOpen(false)}
        />
      ) : null}
      {dataElementType === 'bpmn:BusinessRuleTask' && dataElementId ? (
        <DmnModal
          dataElementId={dataElementId}
          xmlData={xmlDataMap.get(dataElementId) ? xmlDataMap.get(dataElementId).dmnContent : null}
          open={modalOpen && 'bpmn:BusinessRuleTask' === dataElementType}
          onClose={() => setModalOpen(false)}
          onSave={onSave}
        />) : null}
      {dataElementType === 'abc:AssetTask' && dataElementId ? (
        <AssetTaskModal
          dataElementId={dataElementId}
          open={modalOpen && 'abc:AssetTask' === dataElementType}
          onClose={() => setModalOpen(false)}
        />
      ) : null}
      {dataElementType === 'abc:Asset' && dataElementId ? (
        <AssetModal
          dataElementId={dataElementId}
          open={modalOpen && 'abc:Asset' === dataElementType}
          onClose={() => setModalOpen(false)}
        />
      ) : null}
      {/* <ParticipantModal
        dataElementId={dataElementId}
        open={modalOpen && 'Participant' === dataElementType}
        onClose={() => setModalOpen(false)}
      />
      <TaskModal
        dataElementId={dataElementId}
        open={modalOpen && 'ChoreographyTask' === dataElementType}
        onClose={() => setModalOpen(false)}
      /> */}
    </div>
  );
}
