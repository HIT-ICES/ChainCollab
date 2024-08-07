import * as React from 'react';
import $ from 'jquery';
import { Button } from 'antd';

import MessageModal from './MessageModal';
import DmnModal from './DmnModal'
import TaskModal from './TaskModal';
import ParticipantModal from './ParticipantModal';

export default function MainPage({ xmlDataMap, onSave }) {
  const [dataElementId, setDataElementId] = React.useState(null);
  const [dataElementType, setDataElementType] = React.useState(null);
  const [modalOpen, setModalOpen] = React.useState(false);

  React.useEffect(() => {
    const handleDoubleClick = (e) => {
      e.stopPropagation();
      const data_element_id = $(e.target).closest('.djs-element.djs-shape').attr('data-element-id');
      const ids = data_element_id.split('_');
      const type = ids[0];
      setDataElementId(data_element_id);
      setDataElementType(type);
      if (type === 'Activity' || type === 'Message') {
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
      {dataElementType === 'Message' && dataElementId ? (
        <MessageModal
          dataElementId={dataElementId}
          open={modalOpen && 'Message' === dataElementType}
          onClose={() => setModalOpen(false)}
        />
      ) : null}
      {dataElementType === 'Activity' && dataElementId ? (
        <DmnModal
          dataElementId={dataElementId}
          xmlData={xmlDataMap.get(dataElementId) ? xmlDataMap.get(dataElementId).dmnContent : null}
          open={modalOpen && 'Activity' === dataElementType}
          onClose={() => setModalOpen(false)}
          onSave={onSave}
        />) : null}
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
