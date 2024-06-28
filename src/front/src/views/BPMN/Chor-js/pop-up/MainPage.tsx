import * as React from 'react';
import $ from 'jquery';
import { Button } from 'antd';

import MessageModal from './MessageModal';
import TaskModal from './TaskModal';
import ParticipantModal from './ParticipantModal';

export default function MainPage() {
  const [dataElementId, setDataElementId] = React.useState(null);
  const [dataElementType, setDataElementType] = React.useState(null);
  const [modalOpen, setModalOpen] = React.useState(false);

  React.useEffect(() => {
    $(document).on('dblclick', '.djs-element.djs-shape', function (e) {
      e.stopPropagation();
      const data_element_id = $(this).attr('data-element-id');
      // console.log('click task done', this, e, data_element_id)
      // debugger
      const ids = data_element_id.split('_');
      console.log(ids)
      const type = ids[0];
      setDataElementId(data_element_id);
      setDataElementType(type);
      setModalOpen(true);
    });
    return () => $(document).off('dblclick');
  }, []);

  return (
    <div>
      {dataElementId ? (
        <MessageModal
          dataElementId={dataElementId}
          open={modalOpen && 'Message' === dataElementType}
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
