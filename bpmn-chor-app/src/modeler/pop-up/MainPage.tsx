import React from 'react';
import $ from 'jquery';
import MessageModal from './MessageModal';
import DmnModal from './DmnModal';
import OracleTaskModal from './OracleTaskModal';
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
      const modeler = window.bpmnjs;
      const elementRegistry = modeler?.get?.('elementRegistry');
      const element = elementRegistry?.get?.(elementId);
      const elementType = element?.type || element?.businessObject?.$type || '';
      const isMessage = elementType === 'bpmn:Message';
      const isActivity = elementType === 'bpmn:ChoreographyTask' ||
        elementType === 'oracle:DataTask' ||
        elementType === 'bpmn:BusinessRuleTask';
      const isOracleTask = elementType === 'bpmn:ReceiveTask' || elementType === 'bpmn:ScriptTask';
      if (!isMessage && !isActivity && !isOracleTask) {
        return;
      }
      setDataElementId(elementId);
      setDataElementType(isMessage ? 'Message' : (isOracleTask ? 'OracleTask' : 'Activity'));
      setModalOpen(true);
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
      {dataElementType === 'OracleTask' && dataElementId ? (
        <OracleTaskModal
          dataElementId={dataElementId}
          open={modalOpen && dataElementType === 'OracleTask'}
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
