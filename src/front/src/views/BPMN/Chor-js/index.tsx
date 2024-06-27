import React, { useEffect, useState, useRef } from 'react';
import ChoreoModeler from './chor-js/Modeler'; // Adjust the import based on your package structure
// import ChoreoModeler from 'chor-js/lib/Modeler'; // Adjust the import based on your package structure
import PropertiesPanelModule from 'bpmn-js-properties-panel';
import PropertiesProviderModule from './lib-provider/properties-provider'; // Adjust the import based on your package structure
import '../../../../src/assets/styles/app.less';  // 确保您已经配置了less-loader来处理less文件
import blankXml from '../../../../src/assets/bpmns/newDiagram.bpmn'; // Adjust the import based on your package structure
import Reporter from './lib-provider/validator/Validator.js';
import axios from 'axios';
import { c } from 'node_modules/vite/dist/node/types.d-aGj9QkWt';
import { report } from 'process';

const ChorJs = () => {

  const isModelerHandling = useRef(false);
  // const [modeler, setModeler] = useState(null);
  const modeler = useRef(null);
  const reporter = useRef(null);
  let isDirty = false;
  let lastFile = null;
  let isValidating = false;

  async function renderModel(newXml) {
    await modeler.current.importXML(newXml);
    isDirty = false;
  }

  const generatePanelListener = () => {
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

  // returns the file name of the diagram currently being displayed
  function diagramName() {
    if (lastFile) {
      return lastFile.name;
    }
    return 'diagram.bpmn';
  }

  const js_download_diagram = () => {
    const downloadLink = document.getElementById('js-download-diagram');
    console.log('downloadLink listener added');
    downloadLink.addEventListener('click', async e => {
      console.log('downloadLink clicked');
      const result = await modeler.current.saveXML({ format: true });
      downloadLink['href'] = 'data:application/bpmn20-xml;charset=UTF-8,' + encodeURIComponent(result.xml);
      downloadLink['download'] = diagramName();
      isDirty = false;
    });
  }

  const js_download_svg = () => {
    // download diagram as SVG
    const downloadSvgLink = document.getElementById('js-download-svg');
    downloadSvgLink.addEventListener('click', async e => {
      console.log('downloadSvgLink clicked');
      const result = await modeler.current.saveSVG();
      downloadSvgLink['href'] = 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(result.svg);
      downloadSvgLink['download'] = diagramName() + '.svg';
    });
  }

  const js_open_file = () => {
    console.log('js_open_file add event listener');
    // open file dialog
    document.getElementById('js-open-file').addEventListener('click', e => {
      console.log('js-open-file clicked');
      document.getElementById('file-input').click();
    });
  }

  const js_file_input = () => {
    console.log('js_file_input add event listener');
    // load diagram from disk
    const loadDiagram = document.getElementById('file-input');
    loadDiagram.addEventListener('change', e => {
      console.log('file-input changed');
      const file = loadDiagram.files[0];
      if (file) {
        const reader = new FileReader();
        lastFile = file;
        reader.addEventListener('load', async () => {
          await renderModel(reader.result);
          loadDiagram.value = null; // allows reloading the same file
        }, false);
        reader.readAsText(file);
      }
    });
  }

  const js_create_new_diagram = () => {
    // create new diagram
    const newDiagram = document.getElementById('js-new-diagram');
    newDiagram.addEventListener('click', async e => {
      console.log('newDiagram clicked');
      await renderModel(blankXml);
      lastFile = false;
    });
  }

  const js_drag_n_drop = () => {
    // drag & drop file
    const dropZone = document.body;
    dropZone.addEventListener('dragover', e => {
      e.preventDefault();
      dropZone.classList.add('is-dragover');
    });
    dropZone.addEventListener('dragleave', e => {
      e.preventDefault();
      dropZone.classList.remove('is-dragover');
    });
    dropZone.addEventListener('drop', e => {
      e.preventDefault();
      dropZone.classList.remove('is-dragover');
      const file = e.dataTransfer.files[0];
      if (file) {
        const reader = new FileReader();
        lastFile = file;
        reader.addEventListener('load', () => {
          renderModel(reader.result);
        }, false);
        reader.readAsText(file);
      }
    });
  }

  const js_validate = () => {

    // validation logic and toggle
    const validateButton = document.getElementById('js-validate');
    validateButton.addEventListener('click', e => {
      console.log('validateButton clicked');
      isValidating = !isValidating;
      if (isValidating) {
        reporter.current.validateDiagram();
        validateButton.classList.add('selected');
        validateButton['title'] = 'Disable checking';
      } else {
        reporter.current.clearAll();
        validateButton.classList.remove('selected');
        validateButton['title'] = 'Check diagram for problems';
      }
    });
  }

  const js_upload = () => {
    //upload bpmn file
    document.getElementById('js-upload').addEventListener('click', async e => {
      const bpmnName = prompt("请输入BPMN文件的名字：");
      if (bpmnName) {
        const confirmUpload = confirm("是否上传该bpmn文件？");
        if (confirmUpload) {
          const result = await modeler.current.saveXML({ format: true });
          console.log(result)

          const resultOfSvg = await modeler.current.saveSVG();
          console.log(resultOfSvg)

          var params = {};
          var queryString = window.location.search.substring(1);
          var pairs = queryString.split("&");
          for (var i = 0; i < pairs.length; i++) {
            var pair = pairs[i].split("=");
            params[pair[0]] = decodeURIComponent(pair[1]);
          }

          console.log("consortiumid = " + params["consortiumid"])
          // console.log("userid = " + params["userid"])
          upload_bpmn_post(result, params, bpmnName, resultOfSvg);
        } else {
        }
      }
    });
  }
  function upload_bpmn_post(result, params, bpmnName, resultOfSvg) {
    return axios.post('http://192.168.1.177:9999/chaincode/getPartByBpmnC', {
      bpmnContent: result.xml
    })
      .then((response) => {
        console.log('Post getParticipant request success:', response.data);
        axios.post(`http://192.168.1.177:8000/api/v1/consortiums/${params["consortiumid"]}/bpmns/_upload`, {
          bpmnContent: result.xml,
          consortiumid: params["consortiumid"],
          orgid: params["orgid"],
          name: bpmnName + '.bpmn', //之后加一个输入名字？
          svgContent: resultOfSvg.svg,
          participants: response.data
        })
          .then(function (response) {
            console.log(response);
          })
          .catch(function (error) {
            console.error(error);
          });
      })
      .catch((error) => {
        console.error('Post request error:', error);
      });
  }

  useEffect(() => {
    js_download_diagram();
    js_download_svg();
    js_open_file();
    js_file_input();
    js_create_new_diagram();
    js_drag_n_drop();
    js_validate();
    js_upload();
    if (modeler.current === null || modeler.current === undefined) {
      return;
    }
    modeler.current.on('commandStack.changed', () => {
      if (isValidating) {
        reporter.current.validateDiagram();
      }
      isDirty = true;
    });
    modeler.current.on('import.render.complete', () => {
      if (isValidating) {
        reporter.current.validateDiagram();
      }
    });
  }, []);

  useEffect(() => {

    // let modeler = null;
    const [panels, panelListeners] = generatePanelListener();

    const InitModeler = async () => {
      while (isModelerHandling.current) {
        await new Promise(resolve => setTimeout(resolve, 10));
      }
      console.log("Start InitModeler");
      isModelerHandling.current = true;
      modeler.current = new ChoreoModeler({
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

      console.log('Init modeler', modeler.current);
      reporter.current = new Reporter(modeler.current);

      // toggle side panels

      console.log('panels', panels)
      panels.forEach(
        panel => panel.addEventListener('click', panelListeners[panel])
      )

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
        console.log('Remove modeler', modeler.current)
        if (modeler.current !== null && modeler.current !== undefined) {
          await modeler.current.destroy()
          console.log('modeler destroyed')
        }
        // remove event listeners
        panels.forEach(
          panel => panel.removeEventListener('click', panelListeners[panel])
        )
        document.getElementById('js-download-diagram').removeEventListener('click', js_download_diagram);
        document.getElementById('js-download-svg').removeEventListener('click', js_download_svg);
        document.getElementById('js-open-file').removeEventListener('click', js_open_file);
        document.getElementById('file-input').removeEventListener('change', js_file_input);
        document.getElementById('js-new-diagram').removeEventListener('click', js_create_new_diagram);
        document.getElementById('js-validate').removeEventListener('click', js_validate);
        document.getElementById('js-upload').removeEventListener('click', js_upload);
        console.log('event listeners[js-download-diagram, js-download-svg, js-open-file, file-input, js-new-diagram, js-validate, js-upload] removed');
        isModelerHandling.current = false;
      }
      removeModeler();
    };
  }, []);

  return (
    <div
      style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        height: "calc(100vh - 160px)",
        background: "white",
      }}
    >
      <div className="content">
        <div id="canvas" style={{ height: '100%', width: '100%' }}></div>
        <div id="panel-toggle">
          <div data-toggle-panel="properties-panel" title="Toggle properties panel"><span>Properties</span></div>
        </div>
        <div id="properties-panel" className="side-panel hidden" ></div>
        <div className="buttons djs-container">
          <button id="js-new-diagram" className="icon-doc-new" title="Create new empty diagram"></button>
          <button id="js-open-file" className="icon-folder" title="Select BPMN XML file"></button>
          <div className="divider"></div>
          <a id="js-download-diagram" className="icon-file-code" title="Download BPMN XML file"></a>
          <a id="js-download-svg" className="icon-file-image" title="Download as SVG image"></a>
          <div className="divider"></div>
          <button id="js-validate" className="icon-bug" title="Check diagram for problems"></button>
          <div className="divider"></div>
          <button id="js-upload" className="icon-file-upload" title="Upload BPMN file"></button>
          <button id="js-test" className="icon-file-test" title="Create A Test BPMN file"></button>
          <input id="file-input" name="name" type="file" accept=".bpmn, .xml" style={{ display: "none" }} />
        </div>
      </div>
    </div >
  );
};
export default ChorJs;
