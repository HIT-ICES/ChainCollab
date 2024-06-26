import React, { useEffect, useState ,useRef} from 'react';
import ChoreoModeler from 'chor-js/lib/Modeler'; // Adjust the import based on your package structure
import PropertiesPanelModule from 'bpmn-js-properties-panel';
// import PropertiesProviderModule from 'chor-js-properties-panel/lib/provider/chor';

const ChorJs = () => {
    const canvasRef = useRef(null);
  const propertiesPanelRef = useRef(null);

  useEffect(() => {
    const modeler = new ChoreoModeler({
      container: canvasRef.current,
      propertiesPanel: {
        parent: propertiesPanelRef.current
      },
      additionalModules: [
        PropertiesPanelModule,
        // PropertiesProviderModule
      ],
      keyboard: {
        bindTo: document
      }
    });

    // You can add additional setup or model loading here

    return () => {
      modeler.destroy();
    };
  }, []);

  return (
    <div className="content">
      <div id="canvas" ref={canvasRef} style={{ height: '80vh', width: '100%' }}></div>
      <div id="panel-toggle">
        <div data-toggle-panel="properties-panel" title="Toggle properties panel"><span>Properties</span></div>
      </div>
      <div id="properties-panel" className="side-panel hidden" ref={propertiesPanelRef}></div>
    </div>
  );
};
export default ChorJs;
