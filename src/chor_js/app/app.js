import React, { useState } from 'react';
import ReactDOM from 'react-dom';
import axios from "axios";

import { Button } from 'antd';

import 'antd/dist/antd.compact.min.css';
import 'sweetalert2/dist/sweetalert2.css';

import MainPage from './MainPage';

// ---- begin of bpmn import ------

import ChoreoModeler from 'chor-js/lib/Modeler';
import PropertiesPanelModule from 'bpmn-js-properties-panel';

import Reporter from './lib/validator/Validator.js';
import PropertiesProviderModule from './lib/properties-provider';

import xml from './diagrams/pizzaDelivery.bpmn';
import blankXml from './diagrams/newDiagram.bpmn';
import testXml from './diagrams/test.bpmn';

// ---- end of bpmn import ------

// ---- begin of bpmn panel ------

let lastFile;
let isValidating = false;
let isDirty = false;

// create and configure a chor-js instance
const modeler = new ChoreoModeler({
  container: '#canvas',
  propertiesPanel: {
    parent: '#properties-panel'
  },
  // remove the properties' panel if you use the Viewer
  // or NavigatedViewer modules of chor-js
  additionalModules: [
    PropertiesPanelModule,
    PropertiesProviderModule
  ],
  keyboard: {
    bindTo: document
  }
});
console.log(modeler);
// display the given model (XML representation)
async function renderModel(newXml) {
  await modeler.importXML(newXml);
  isDirty = false;
}

// returns the file name of the diagram currently being displayed
function diagramName() {
  if (lastFile) {
    return lastFile.name;
  }
  return 'diagram.bpmn';
}

document.addEventListener('DOMContentLoaded', () => {
  // download diagram as XML
  const downloadLink = document.getElementById('js-download-diagram');
  downloadLink.addEventListener('click', async e => {
    const result = await modeler.saveXML({ format: true });
    downloadLink['href'] = 'data:application/bpmn20-xml;charset=UTF-8,' + encodeURIComponent(result.xml);
    downloadLink['download'] = diagramName();
    isDirty = false;
  });

  // download diagram as SVG
  const downloadSvgLink = document.getElementById('js-download-svg');
  downloadSvgLink.addEventListener('click', async e => {
    const result = await modeler.saveSVG();
    downloadSvgLink['href'] = 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(result.svg);
    downloadSvgLink['download'] = diagramName() + '.svg';
  });

  // open file dialog
  document.getElementById('js-open-file').addEventListener('click', e => {
    document.getElementById('file-input').click();
  });

  //upload bpmn file
  document.getElementById('js-upload').addEventListener('click', async e => {
    const bpmnName = prompt("请输入BPMN文件的名字：");
    if (bpmnName) {
      const confirmUpload = confirm("是否上传该bpmn文件？");
      if (confirmUpload) {
        const result = await modeler.saveXML({ format: true });
        console.log(result)

        const resultOfSvg = await modeler.saveSVG();
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

  // create a test Bpmn
  document.getElementById('js-test').addEventListener('click', async e => {
    const formattedDateString = createCurrentTime();
    const bpmnName = "test-" + formattedDateString;
    await renderModel(testXml)
    const result = await modeler.saveXML({ format: true });
    const resultOfSvg = await modeler.saveSVG();
    var params = {};
    var queryString = window.location.search.substring(1);
    var pairs = queryString.split("&");
    for (var i = 0; i < pairs.length; i++) {
      var pair = pairs[i].split("=");
      params[pair[0]] = decodeURIComponent(pair[1]);
    }

    console.log("consortiumid = " + params["consortiumid"])
    upload_bpmn_post(result, params, bpmnName, resultOfSvg);
  });

  // toggle side panels
  const panels = Array.prototype.slice.call(
    document.getElementById('panel-toggle').children
  );
  panels.forEach(panel => {
    panel.addEventListener('click', () => {
      panels.forEach(otherPanel => {
        if (panel === otherPanel && !panel.classList.contains('active')) {
          // show clicked panel if it is not already active, otherwise hide it as well
          panel.classList.add('active');
          document.getElementById(panel.dataset.togglePanel).classList.remove('hidden');
        } else {
          // hide all other panels
          otherPanel.classList.remove('active');
          document.getElementById(otherPanel.dataset.togglePanel).classList.add('hidden');
        }
      });
    });
  });

  // create new diagram
  const newDiagram = document.getElementById('js-new-diagram');
  newDiagram.addEventListener('click', async e => {
    await renderModel(blankXml);
    lastFile = false;
  });

  // load diagram from disk
  const loadDiagram = document.getElementById('file-input');
  loadDiagram.addEventListener('change', e => {
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

  // validation logic and toggle
  const reporter = new Reporter(modeler);
  const validateButton = document.getElementById('js-validate');
  validateButton.addEventListener('click', e => {
    isValidating = !isValidating;
    if (isValidating) {
      reporter.validateDiagram();
      validateButton.classList.add('selected');
      validateButton['title'] = 'Disable checking';
    } else {
      reporter.clearAll();
      validateButton.classList.remove('selected');
      validateButton['title'] = 'Check diagram for problems';
    }
  });
  modeler.on('commandStack.changed', () => {
    if (isValidating) {
      reporter.validateDiagram();
    }
    isDirty = true;
  });
  modeler.on('import.render.complete', () => {
    if (isValidating) {
      reporter.validateDiagram();
    }
  });
});

// expose bpmnjs to window for debugging purposes
window.bpmnjs = modeler;

window.addEventListener('beforeunload', function (e) {
  if (isDirty) {
    // see https://developer.mozilla.org/en-US/docs/Web/API/WindowEventHandlers/onbeforeunload
    e.preventDefault();
    e.returnValue = '';
  }
});

renderModel(blankXml);

// ---- end of bpmn panel ------

ReactDOM.render(<MainPage />, document.getElementById('app'),);

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

function createCurrentTime() {
  const currentDate = new Date();
  const year = currentDate.getFullYear();
  const month = (currentDate.getMonth() + 1).toString().padStart(2, '0'); // 加 1 是因为 getMonth 返回的是从 0 开始计数的月份
  const day = currentDate.getDate().toString().padStart(2, '0');
  const hours = currentDate.getHours().toString().padStart(2, '0');
  const minutes = currentDate.getMinutes().toString().padStart(2, '0');
  const seconds = currentDate.getSeconds().toString().padStart(2, '0');
  const formattedDateString = `${year}-${month}-${day}-${hours}.${minutes}.${seconds}`;
  return formattedDateString;
}

