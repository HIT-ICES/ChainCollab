import React, { useEffect, useRef, useLayoutEffect, useState } from 'react';
import DmnJS from 'dmn-js/lib/Modeler';
import { Modal, Input } from 'antd'
import "dmn-js/dist/assets/diagram-js.css";
import "dmn-js/dist/assets/dmn-font/css/dmn-embedded.css";
import "dmn-js/dist/assets/dmn-js-decision-table-controls.css";
import "dmn-js/dist/assets/dmn-js-decision-table.css";
import "dmn-js/dist/assets/dmn-js-drd.css";
import "dmn-js/dist/assets/dmn-js-literal-expression.css";
import "dmn-js/dist/assets/dmn-js-shared.css";
import { migrateDiagram } from '@bpmn-io/dmn-migrate';
import DmnDrawer from "./DmnDrawer"

const DmnModal = ({ dataElementId, xmlData, open: isModalOpen, onClose, onSave }) => {


    const DmnDrawerRef = useRef()
    const [name, setName] = useState("")

    const handleOk = async () => {
        if (DmnDrawerRef.current === undefined) {
            return;
        }
        const {xml,svg} = await DmnDrawerRef.current.getXmlAndSvg()
        // console.log('xml', xml);
        onSave(dataElementId, { "dmnContent": xml_result.xml, "name": name, "svgContent": svg_result.svg });
        // updateBpmnName();
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
                Business Rule Task Name<br />
                <Input
                    placeholder="Change Business Rule Task Name"
                    style={{ width: '50%', }}
                    value={name}
                    onChange={
                        (e) => {
                            setName(e.target.value);
                        }
                    }
                />
                <br />
                <DmnDrawer
                    ref = {DmnDrawerRef}
                    dataElementId={dataElementId}
                    xmlData={xmlData}
                />
            </Modal >
        </div >
    );
};

export default DmnModal;
