import React, { useEffect, useState, useRef } from 'react';
import ChoreoModeler from './chor-js/Modeler'; // Adjust the import based on your package structure
// import ChoreoModeler from 'chor-js/lib/Modeler'; // Adjust the import based on your package structure
import PropertiesPanelModule from 'bpmn-js-properties-panel';
import PropertiesProviderModule from './lib-provider/properties-provider'; // Adjust the import based on your package structure
import '../../../../src/assets/styles/app.less';  // 确保您已经配置了less-loader来处理less文件
import { set } from 'lodash';
let blankXml = `<?xml version="1.0" encoding="UTF-8"?>
<!-- origin at X=0.0 Y=0.0 -->
<bpmn2:definitions xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:bpmn2="http://www.omg.org/spec/BPMN/20100524/MODEL" xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" xmlns:di="http://www.omg.org/spec/DD/20100524/DI" xmlns:xs="http://www.w3.org/2001/XMLSchema" id="_tTv5YOycEeiHGOQ2NkJZNQ" targetNamespace="http://bpmn.io/schema/bpmn">
    <bpmn2:choreography id="Choreography">
    </bpmn2:choreography>
    <bpmndi:BPMNDiagram id="BPMNDiagram_1">
        <bpmndi:BPMNPlane id="BPMNPlane_Choreography_1" bpmnElement="Choreography">
        </bpmndi:BPMNPlane>
        <bpmndi:BPMNLabelStyle id="BPMNLabelStyle_1">
            <dc:Font name="arial" size="9.0"/>
        </bpmndi:BPMNLabelStyle>
    </bpmndi:BPMNDiagram>
</bpmn2:definitions>
`

const ChorJs = () => {

  const isModelerHandling = useRef(false);


  const generatePanelListener = (panel) => {
    const panels = Array.prototype.slice.call(
      document.getElementById('panel-toggle').children
    );
    const panelsToListener = {}
    panels.forEach(p => {
      panelsToListener[p] = () => {
        panels.forEach(otherPanel => {
          if (p === otherPanel && !p.classList.contains('active')) {
            p.classList.add('active');
            document.getElementById(p.dataset.togglePanel).classList.remove('hidden');
          } else {
            otherPanel.classList.remove('active');
            document.getElementById(otherPanel.dataset.togglePanel).classList.add('hidden');
          }
        });
      }
    });
    return [panels, panelsToListener]
  }

  useEffect(() => {

    let modeler = null;
    const [panels, panelListeners] = generatePanelListener('properties-panel');



    const InitModeler = async () => {
      while (isModelerHandling.current) {
        await new Promise(resolve => setTimeout(resolve, 10));
      }
      console.log("Start InitModeler");
      isModelerHandling.current = true;
      modeler = new ChoreoModeler({
        container: '#canvas',
        propertiesPanel: {
          parent: '#properties-panel'
        },
        additionalModules: [
          PropertiesPanelModule,
          PropertiesProviderModule
        ],
        keyboard: {
          bindTo: document
        }
      })
      let isDirty = false;


      console.log('modeler', modeler);
      // toggle side panels

      console.log('panels', panels)
      panels.forEach(
        panel => panel.addEventListener('click', panelListeners[panel])
      )

      async function renderModel(newXml) {
        await modeler.importXML(newXml);
        isDirty = false;
      }

      let lastFile;
      let isValidating = false;
      // returns the file name of the diagram currently being displayed
      function diagramName() {
        if (lastFile) {
          return lastFile.name;
        }
        return 'diagram.bpmn';
      }
      const initialRender = async () => {
        await renderModel(blankXml);
      }
      await initialRender();
      console.log("modeler initialized");
      isModelerHandling.current = false
    }
    InitModeler();


    // You can add additional setup or model loading here
    return () => {
      const removeModeler = async () => {
        while (isModelerHandling.current) {
          await new Promise(resolve => setTimeout(resolve, 10));
        }
        console.log("Start removeModeler");
        isModelerHandling.current = true;
        console.log(modeler)
        await modeler.destroy()
        console.log('modeler destroyed')
        panels.forEach(
          panel => panel.removeEventListener('click', panelListeners[panel])
        )
        isModelerHandling.current = (false);
      }
      removeModeler();
    };
  }, []);

  return (
    <div className="content">
      <div id="canvas" style={{ height: '80vh', width: '100%' }}></div>
      <div id="panel-toggle">
        <div data-toggle-panel="properties-panel" title="Toggle properties panel"><span>Properties</span></div>
      </div>
      <div id="properties-panel" className="side-panel hidden" ></div>
    </div>
  );
};
export default ChorJs;
