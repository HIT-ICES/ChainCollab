import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState
} from 'react';
import ChoreoModeler from './modeler/chor-js/Modeler.js';
import PropertiesPanelModule from 'bpmn-js-properties-panel';
import PropertiesProviderModule from './modeler/lib-provider/properties-provider';
import './assets/styles/app.less';
import blankXml from './assets/bpmns/newDiagram.bpmn?raw';
import Reporter from './modeler/lib-provider/validator/Validator.js';
import MainPage from './modeler/pop-up/MainPage';
import UploadDmnModal from './modeler/pop-up/UploadDmnModal';
import TestPaletteProvider from './modeler/lib-provider/external-elements';
import type { DmnDefinition, UploadableDmn } from './types/modeler';
import type { ChorApiClient } from './services/api';
import { createDefaultChorApiClient } from './services/api';

export interface ChorModelerProps {
  consortiumId: string;
  orgId: string;
  apiBaseUrl: string;
  translatorBaseUrl: string;
  authToken?: string;
  authScheme?: string;
  headers?: Record<string, string>;
  fetchImpl?: typeof fetch;
  defaultDiagramXml?: string;
  className?: string;
  style?: React.CSSProperties;
  serviceOverrides?: Partial<ChorApiClient>;
  onBpmnUpload?: (response: unknown) => void;
}

const ChorModelerApp: React.FC<ChorModelerProps> = ({
  consortiumId,
  orgId,
  apiBaseUrl,
  translatorBaseUrl,
  authToken,
  authScheme = 'JWT',
  headers,
  fetchImpl,
  defaultDiagramXml,
  className,
  style,
  serviceOverrides,
  onBpmnUpload
}) => {
  const modeler = useRef<any>(null);
  const reporter = useRef<any>(null);
  const isModelerHandling = useRef(false);
  const isDirtyRef = useRef(false);
  const lastFileRef = useRef<File | null>(null);
  const isValidatingRef = useRef(false);

  const [dmnUploadModalOpen, setDmnUploadModalOpen] = useState(false);
  const [dmnIdXmlMap, setDmnIdXmlMap] = useState<Map<string, DmnDefinition>>(new Map());

  const apiClient = useMemo<ChorApiClient>(() => {
    const baseClient = createDefaultChorApiClient({
      apiBaseUrl,
      translatorBaseUrl,
      authToken,
      authScheme,
      headers,
      fetchImpl
    });

    return {
      ...baseClient,
      ...(serviceOverrides ?? {})
    };
  }, [apiBaseUrl, translatorBaseUrl, authToken, authScheme, headers, fetchImpl, serviceOverrides]);

  const addToDmnMap = useCallback((key: string, value: DmnDefinition) => {
    setDmnIdXmlMap((prev) => {
      const updated = new Map(prev);
      updated.set(key, value);
      return updated;
    });
  }, []);

  const renderModel = useCallback(async (newXml: string) => {
    if (!modeler.current) {
      return;
    }
    await modeler.current.importXML(newXml);
    isDirtyRef.current = false;
  }, []);

  const diagramName = useCallback(() => {
    return lastFileRef.current?.name ?? 'diagram.bpmn';
  }, []);

  const handleBulkDmnUpload = useCallback(async (items: UploadableDmn[]) => {
    await Promise.all(items.map((item) =>
      apiClient.addDmn({
        consortiumId,
        orgId,
        name: item.uploadName,
        dmnContent: item.dmnContent,
        svgContent: item.svgContent
      })
    ));
  }, [apiClient, consortiumId, orgId]);

  useEffect(() => {
    const beforeUnload = (e: BeforeUnloadEvent) => {
      if (isDirtyRef.current) {
        e.preventDefault();
        e.returnValue = '';
      }
    };
    window.addEventListener('beforeunload', beforeUnload);
    return () => window.removeEventListener('beforeunload', beforeUnload);
  }, []);

  useEffect(() => {
    let panelListeners: Array<{ panel: Element; handler: () => void }> = [];

    const setupPanelListeners = () => {
      const toggleContainer = document.getElementById('panel-toggle');
      if (!toggleContainer) {
        return;
      }
      const panels = Array.from(toggleContainer.children);
      panelListeners = panels.map((panel) => {
        const listener = () => {
          panels.forEach((otherPanel) => {
            const togglePanel = otherPanel.getAttribute('data-toggle-panel');
            const target = togglePanel ? document.getElementById(togglePanel) : null;
            if (panel === otherPanel && !otherPanel.classList.contains('active')) {
              otherPanel.classList.add('active');
              target?.classList.remove('hidden');
            } else {
              otherPanel.classList.remove('active');
              target?.classList.add('hidden');
            }
          });
        };
        panel.addEventListener('click', listener);
        return { panel, handler: listener };
      });
    };

    setupPanelListeners();

    let cancelled = false;

    const initModeler = async () => {
      while (isModelerHandling.current) {
        await new Promise((resolve) => setTimeout(resolve, 10));
      }
      if (cancelled) {
        return;
      }
      isModelerHandling.current = true;
      const ModelerCtor = ChoreoModeler as any;
      modeler.current = new ModelerCtor({
        container: '#canvas',
        propertiesPanel: {
          parent: '#properties-panel'
        },
        additionalModules: [
          PropertiesPanelModule,
          PropertiesProviderModule,
          TestPaletteProvider
        ],
        keyboard: {
          bindTo: document
        }
      });
      reporter.current = new Reporter(modeler.current);
      await renderModel(defaultDiagramXml ?? blankXml);
      window.bpmnjs = modeler.current;
      isModelerHandling.current = false;
    };

    initModeler();

    return () => {
      cancelled = true;
      panelListeners.forEach(({ panel, handler }) => panel.removeEventListener('click', handler));
      const destroyModeler = async () => {
        while (isModelerHandling.current) {
          await new Promise((resolve) => setTimeout(resolve, 10));
        }
        isModelerHandling.current = true;
        if (modeler.current) {
          await modeler.current.destroy();
          modeler.current = null;
          window.bpmnjs = undefined;
        }
        reporter.current = null;
        isModelerHandling.current = false;
      };
      destroyModeler();
    };
  }, [defaultDiagramXml, renderModel]);

  useEffect(() => {
    if (!modeler.current) {
      return;
    }

    const downloadLink = document.getElementById('js-download-diagram');
    const downloadSvgLink = document.getElementById('js-download-svg');
    const openFileElement = document.getElementById('js-open-file');
    const loadDiagram = document.getElementById('file-input') as HTMLInputElement | null;
    const newDiagram = document.getElementById('js-new-diagram');
    const validateButton = document.getElementById('js-validate');
    const uploadButton = document.getElementById('js-upload');
    const uploadDmnButton = document.getElementById('js-upload-dmn');
    const dropZone = document.body;

    if (!downloadLink || !downloadSvgLink || !openFileElement || !loadDiagram || !newDiagram || !validateButton || !uploadButton || !uploadDmnButton) {
      return;
    }

    const downloadHandler = async () => {
      const result = await modeler.current.saveXML({ format: true });
      downloadLink.setAttribute('href', 'data:application/bpmn20-xml;charset=UTF-8,' + encodeURIComponent(result.xml));
      downloadLink.setAttribute('download', diagramName());
      isDirtyRef.current = false;
    };

    const downloadSvgHandler = async () => {
      const result = await modeler.current.saveSVG();
      downloadSvgLink.setAttribute('href', 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(result.svg));
      downloadSvgLink.setAttribute('download', diagramName() + '.svg');
    };

    const openFileHandler = () => {
      loadDiagram.click();
    };

    const fileInputHandler = (e: Event) => {
      const target = e.target as HTMLInputElement;
      const file = target.files?.[0];
      if (file) {
        const reader = new FileReader();
        lastFileRef.current = file;
        reader.addEventListener('load', async () => {
          if (typeof reader.result === 'string') {
            await renderModel(reader.result);
            target.value = '';
          }
        });
        reader.readAsText(file);
      }
    };

    const newDiagramHandler = async () => {
      await renderModel(defaultDiagramXml ?? blankXml);
      lastFileRef.current = null;
    };

    const dragOverHandler = (event: DragEvent) => {
      event.preventDefault();
      dropZone.classList.add('is-dragover');
    };

    const dragLeaveHandler = (event: DragEvent) => {
      event.preventDefault();
      dropZone.classList.remove('is-dragover');
    };

    const dropHandler = (event: DragEvent) => {
      event.preventDefault();
      dropZone.classList.remove('is-dragover');
      const file = event.dataTransfer?.files?.[0];
      if (file) {
        const reader = new FileReader();
        lastFileRef.current = file;
        reader.addEventListener('load', async () => {
          if (typeof reader.result === 'string') {
            await renderModel(reader.result);
          }
        });
        reader.readAsText(file);
      }
    };

    const validateHandler = () => {
      isValidatingRef.current = !isValidatingRef.current;
      if (isValidatingRef.current) {
        reporter.current?.validateDiagram();
        validateButton.classList.add('selected');
        validateButton.setAttribute('title', 'Disable checking');
      } else {
        reporter.current?.clearAll();
        validateButton.classList.remove('selected');
        validateButton.setAttribute('title', 'Check diagram for problems');
      }
    };

    const uploadHandler = async () => {
      const bpmnName = window.prompt('请输入BPMN文件的名字：');
      if (!bpmnName) {
        return;
      }
      const confirmUpload = window.confirm('是否上传该bpmn文件？');
      if (!confirmUpload) {
        return;
      }
      const result = await modeler.current.saveXML({ format: true });
      const svgResult = await modeler.current.saveSVG();
      const participants = await apiClient.getParticipantsByContent(result.xml);
      const response = await apiClient.addBpmn({
        consortiumId,
        orgId,
        name: `${bpmnName}.bpmn`,
        bpmnContent: result.xml,
        svgContent: svgResult.svg,
        participants
      });
      onBpmnUpload?.(response);
    };

    const uploadDmnHandler = () => {
      setDmnUploadModalOpen(true);
    };

    const commandStackChange = () => {
      if (isValidatingRef.current) {
        reporter.current?.validateDiagram();
      }
      isDirtyRef.current = true;
    };

    const importRenderHandler = () => {
      if (isValidatingRef.current) {
        reporter.current?.validateDiagram();
      }
    };

    downloadLink.addEventListener('click', downloadHandler);
    downloadSvgLink.addEventListener('click', downloadSvgHandler);
    openFileElement.addEventListener('click', openFileHandler);
    loadDiagram.addEventListener('change', fileInputHandler);
    newDiagram.addEventListener('click', newDiagramHandler);
    dropZone.addEventListener('dragover', dragOverHandler);
    dropZone.addEventListener('dragleave', dragLeaveHandler);
    dropZone.addEventListener('drop', dropHandler);
    validateButton.addEventListener('click', validateHandler);
    uploadButton.addEventListener('click', uploadHandler);
    uploadDmnButton.addEventListener('click', uploadDmnHandler);
    modeler.current.on('commandStack.changed', commandStackChange);
    modeler.current.on('import.render.complete', importRenderHandler);

    return () => {
      downloadLink.removeEventListener('click', downloadHandler);
      downloadSvgLink.removeEventListener('click', downloadSvgHandler);
      openFileElement.removeEventListener('click', openFileHandler);
      loadDiagram.removeEventListener('change', fileInputHandler);
      newDiagram.removeEventListener('click', newDiagramHandler);
      dropZone.removeEventListener('dragover', dragOverHandler);
      dropZone.removeEventListener('dragleave', dragLeaveHandler);
      dropZone.removeEventListener('drop', dropHandler);
      validateButton.removeEventListener('click', validateHandler);
      uploadButton.removeEventListener('click', uploadHandler);
      uploadDmnButton.removeEventListener('click', uploadDmnHandler);
      modeler.current?.off?.('commandStack.changed', commandStackChange);
      modeler.current?.off?.('import.render.complete', importRenderHandler);
    };
  }, [apiClient, consortiumId, orgId, diagramName, defaultDiagramXml, onBpmnUpload, renderModel]);

  return (
    <div
      className={className}
      style={{
        width: '100%',
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        background: '#eef2ff',
        ...(style ?? {})
      }}
    >
      <div className="modeler-shell">
        <div className="modeler-header">
          <div className="modeler-header__info">
            <p className="eyebrow">CHOREOGRAPHY STUDIO</p>
            <h2>Cross-Org Process Designer</h2>
            <span>Design, validate and orchestrate choreography models across organizations.</span>
          </div>
          <div className="modeler-actions djs-container">
            <button id="js-new-diagram" className="icon-doc-new" title="Create new empty diagram" />
            <button id="js-open-file" className="icon-folder" title="Select BPMN XML file" />
            <a id="js-download-diagram" className="icon-file-code" title="Download BPMN XML file" />
            <a id="js-download-svg" className="icon-file-image" title="Download as SVG image" />
            <button id="js-validate" className="icon-bug" title="Check diagram for problems" />
            <button id="js-upload" className="icon-file-upload" title="Upload BPMN file" />
            <button id="js-upload-dmn" className="icon-file-upload" title="Upload Dmn file" />
            <input id="file-input" name="name" type="file" accept=".bpmn, .xml" style={{ display: 'none' }} />
          </div>
        </div>
        <div className="content">
        <div id="canvas" style={{ height: '100%', width: '100%' }} />
        <div id="panel-toggle">
          <div data-toggle-panel="properties-panel" title="Toggle properties panel"><span>Properties</span></div>
        </div>
        <div id="properties-panel" className="side-panel hidden" />
        </div>
      </div>
      <MainPage
        xmlDataMap={dmnIdXmlMap}
        onSave={addToDmnMap}
      />
      <UploadDmnModal
        dmnData={dmnIdXmlMap}
        open={dmnUploadModalOpen}
        setOpen={setDmnUploadModalOpen}
        onUpload={handleBulkDmnUpload}
      />
    </div>
  );
};

export default ChorModelerApp;
