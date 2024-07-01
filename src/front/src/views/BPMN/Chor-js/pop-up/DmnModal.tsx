import React, { useEffect, useRef, useLayoutEffect } from 'react';
import DmnJS from 'dmn-js/lib/Modeler';
import { Modal } from 'antd'
import "dmn-js/dist/assets/diagram-js.css";
import "dmn-js/dist/assets/dmn-font/css/dmn-embedded.css";
import "dmn-js/dist/assets/dmn-js-decision-table-controls.css";
import "dmn-js/dist/assets/dmn-js-decision-table.css";
import "dmn-js/dist/assets/dmn-js-drd.css";
import "dmn-js/dist/assets/dmn-js-literal-expression.css";
import "dmn-js/dist/assets/dmn-js-shared.css";
import { migrateDiagram } from '@bpmn-io/dmn-migrate';

const DmnModal = ({ dataElementId, open: isModalOpen, onClose }) => {
    const blankXml = `<?xml version="1.0" encoding="UTF-8"?>
                <definitions xmlns="https://www.omg.org/spec/DMN/20191111/MODEL/" id="definitions_1olsuce" name="definitions" namespace="http://camunda.org/schema/1.0/dmn" exporter="dmn-js (https://demo.bpmn.io/dmn)" exporterVersion="16.4.0">
                <decision id="decision_0tybghz" name="">
                    <decisionTable id="decisionTable_1v3tii8">
                    <input id="input1" label="">
                        <inputExpression id="inputExpression1" typeRef="string">
                        <text></text>
                        </inputExpression>
                    </input>
                    <output id="output1" label="" name="" typeRef="string" />
                    </decisionTable>
                </decision>
                </definitions>`;

    const viewer = useRef(null);
    const containerRef = useRef(null);
    const isModelerHandling = useRef(false);

    const renderModel = async (xml) => {
        try {
            // (1.1) migrate to DMN 1.3 if necessary
            xml = await migrateDiagram(xml);
            await viewer.current.importXML(xml);
            console.log('rendered');
        } catch (err) {
            console.log('error rendering', err);
        }
    };

    useEffect(() => {

        const initViewer = async () => {
            while (isModelerHandling.current) {
                await new Promise(resolve => setTimeout(resolve, 10));
            }
            // console.log('container ref', containerRef.current)
            while (containerRef.current === null) {
                await new Promise(resolve => setTimeout(resolve, 10));
            }
            console.log('init viewer')
            isModelerHandling.current = true;
            viewer.current = new DmnJS({
                // container: '#container',
                decisionTable: {
                    keyboard: {
                        bindTo: document
                    }
                }

            });
            console.log("dmn created", viewer.current)

            // Function to attach viewer to container
            const attachViewer = () => {
                console.log("attach viewer")
                viewer.current.attachTo(containerRef.current);
            };


            // Import XML and render the DMN diagram
            await renderModel(blankXml);
            attachViewer();
            isModelerHandling.current = false;
        }

        // Attach viewer and render diagram on mount
        initViewer();

        // Clean up on unmount
        return () => {
            const detachViewer = async () => {
                while (isModelerHandling.current) {
                    await new Promise(resolve => setTimeout(resolve, 10));
                }
                isModelerHandling.current = true;
                // Function to detach viewer from container
                console.log("detach viewer")
                viewer.current.detach();
                isModelerHandling.current = false;
            };
            detachViewer();
        };
    }, []);

    let lastFile = null;
    let isDirty = false;

    // returns the file name of the diagram currently being displayed
    function diagramName() {
        if (lastFile) {
            return lastFile.name;
        }
        return 'diagram.dmn';
    }

    const js_download_listener = async (e: MouseEvent): Promise<void> => {
        console.log('downloadLink clicked');
        const downloadLink = document.getElementById('js-download-diagram-dmn');
        const result = await viewer.current.saveXML({ format: true });
        downloadLink['href'] = 'data:application/xml;charset=UTF-8,' + encodeURIComponent(result.xml);
        downloadLink['download'] = diagramName();
        isDirty = false;
    };

    const js_open_file_listener = (e: MouseEvent): void => {
        console.log('js-open-file clicked');
        document.getElementById('file-input-dmn').click();
    };

    const js_file_input_listener = (e: Event): void => {
        console.log('file-input changed');
        const loadDiagram = document.getElementById('file-input-dmn');
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
    };

    const js_create_new_diagram_listener = async (e: MouseEvent): Promise<void> => {
        console.log('newDiagram clicked');
        await renderModel(blankXml);
        lastFile = false;
    };

    const js_download_svg_listerner = async (e: MouseEvent): Promise<void> => {
        console.log('downloadSvgLink clicked');
        const downloadSvgLink = document.getElementById('js-download-svg-dmn');
        const result = await viewer.current.getActiveViewer().saveSVG();
        downloadSvgLink['href'] = 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(result.svg);
        downloadSvgLink['download'] = diagramName() + '.svg';
    };

    useEffect(() => {
        //download diagram as DMN XML
        const downloadLink = document.getElementById('js-download-diagram-dmn');
        console.log('dmn downloadLink listener added', downloadLink);
        downloadLink.addEventListener('click', js_download_listener);

        // open file dialog
        console.log('js_open_file add event listener');
        const js_open = document.getElementById('js-open-file-dmn');
        js_open.addEventListener('click', js_open_file_listener);


        // load diagram from disk
        console.log('js_file_input add event listener');
        const loadDiagram = document.getElementById('file-input-dmn');
        loadDiagram.addEventListener('change', js_file_input_listener);

        // create new diagram
        const newDiagram = document.getElementById('js-new-diagram');
        newDiagram.addEventListener('click', js_create_new_diagram_listener);

        // download diagram as SVG
        const downloadSvgLink = document.getElementById('js-download-svg-dmn');
        downloadSvgLink.addEventListener('click', js_download_svg_listerner);

        return () => {
            downloadLink.removeEventListener('click', js_download_listener);
            loadDiagram.removeEventListener('change', js_file_input_listener);
            newDiagram.removeEventListener('click', js_create_new_diagram_listener);
            js_open.removeEventListener('click', js_open_file_listener);
            console.log('downloadLink, loadDiagram, newDiagram, js_open listener removed');
        }
    }, []);

    const handleOk = async () => {
        const xml = await viewer.current.saveXML({ format: true });
        console.log('xml', xml);
        onClose && onClose(true);
    };

    const handleCancel = () => {
        onClose && onClose(false);
    };

    return (
        <div>
            <Modal
                className='content'
                open={isModalOpen}
                onOk={handleOk}
                onCancel={handleCancel}
                styles={
                    {
                        body: { width: 1700, height: 'calc(100vh - 160px)' }
                    }
                }
                style={{ top: 64 }}
                centered
                width={1800}
            >
                <div
                    id='container'
                    ref={containerRef}
                    style={{
                        width: "100%",
                        height: "100%",
                        background: "white",
                    }}>
                </div>
                <div className='button-group'
                    style={{
                        // position: "absolute",
                        bottom: 0,
                        width: "100%",
                        textAlign: "left",
                        paddingBottom: "10px", // Add padding if needed
                        backgroundColor: "white", // Ensure buttons are visible
                        display: "flex", // Use flexbox for layout
                        justifyContent: "flex-start", // Align items to the left
                        alignItems: "center", // Center items vertically
                        gap: "10px" // Add gap between elements
                    }}>
                    <div className="buttons djs-container">
                        <button id="js-open-file-dmn" className="icon-folder" title="Select DMN XML file" ></button>
                        <button id="js-new-diagram-dmn" className="icon-doc-new" title="Create new empty diagram" ></button>
                        <a id="js-download-diagram-dmn" className="icon-file-code" title="Download DMN XML file" ></a>
                        <a id="js-download-svg-dmn" className="icon-file-image" title="Download as SVG image" ></a>
                        <input id="file-input-dmn" name="name" type="file" accept=".dmn, .xml" style={{ display: "none" }} />
                    </div>
                </div>
            </Modal >
        </div >
    );
};

export default DmnModal;
