import React from 'react';
import $ from 'jquery';
import MessageModal from './MessageModal';
import DmnModal from './DmnModal';
import type { DmnDefinition } from '@/types/modeler';

interface MainPageProps {
  xmlDataMap: Map<string, DmnDefinition>;
  onSave: (key: string, value: DmnDefinition) => void;
}

const MainPage: React.FC<MainPageProps> = ({ xmlDataMap, onSave }) => {
  const [dataElementId, setDataElementId] = React.useState<string | null>(null);
  const [dataElementType, setDataElementType] = React.useState<string | null>(null);
  const [modalOpen, setModalOpen] = React.useState(false);

  React.useEffect(() => {
    const handleDoubleClick = (e: JQuery.DoubleClickEvent) => {
      e.stopPropagation();
      const elementId = $(e.target).closest('.djs-element.djs-shape').attr('data-element-id');
      if (!elementId) {
        return;
      }
      const ids = elementId.split('_');
      const type = ids[0];
      setDataElementId(elementId);
      setDataElementType(type);
      if (type === 'Activity' || type === 'Message') {
        setModalOpen(true);
      }
    };

    if (!modalOpen) {
      $(document).on('dblclick', '.djs-element.djs-shape', handleDoubleClick);
    } else {
      $(document).off('dblclick', '.djs-element.djs-shape', handleDoubleClick);
    }

    return () => {
      $(document).off('dblclick', '.djs-element.djs-shape', handleDoubleClick);
    };
  }, [modalOpen]);

  return (
    <div>
      {dataElementType === 'Message' && dataElementId ? (
        <MessageModal
          dataElementId={dataElementId}
          open={modalOpen && dataElementType === 'Message'}
          onClose={() => setModalOpen(false)}
        />
      ) : null}
      {dataElementType === 'Activity' && dataElementId ? (
        <DmnModal
          dataElementId={dataElementId}
          xmlData={xmlDataMap.get(dataElementId)?.dmnContent ?? null}
          open={modalOpen && dataElementType === 'Activity'}
          onClose={() => setModalOpen(false)}
          onSave={onSave}
        />
      ) : null}
    </div>
  );
};

export default MainPage;
