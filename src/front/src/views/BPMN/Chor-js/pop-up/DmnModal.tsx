import React, { useEffect, useRef, useLayoutEffect, useState } from 'react';
import DmnJS from 'dmn-js/lib/Modeler';
import { Modal, Input, Tabs, Row, Col, Select, Button, Typography } from 'antd'
const { Option } = Select;
const { Text } = Typography;
import "dmn-js/dist/assets/diagram-js.css";
import "dmn-js/dist/assets/dmn-font/css/dmn-embedded.css";
import "dmn-js/dist/assets/dmn-js-decision-table-controls.css";
import "dmn-js/dist/assets/dmn-js-decision-table.css";
import "dmn-js/dist/assets/dmn-js-drd.css";
import "dmn-js/dist/assets/dmn-js-literal-expression.css";
import "dmn-js/dist/assets/dmn-js-shared.css";
import { migrateDiagram } from '@bpmn-io/dmn-migrate';
import DmnDrawer from "./DmnDrawer"


const IOBlock = ({
    index, type, item, handleChange, handleRemove
}) => {

    return (
        <div key={index} style={{
            marginTop: 20, marginBottom: 10, gap: 10, display: "flex", flexDirection: "column", border: "1px solid #d9d9d9", padding: "10px", width: "500px", borderRadius: "5px",
        }} >
            <div style={{ display: 'flex', gap: '20px', alignContent: "center", justifyContent: "flex-start" }}>
                <Text style={{ width: '200px', display: 'inline-block' }} type="secondary" strong>Field Name</Text>
                <Input
                    placeholder="Name"
                    value={item.name}
                    style={{ width: 250 }}
                    onChange={(e) => handleChange(index, 'name', e.target.value, type)}
                    readOnly={type === 'input'}
                />
            </div>
            <div style={{ display: 'flex', gap: '20px', alignContent: "center", justifyContent: "flex-start" }}>
                <Text style={{ width: '200px', display: 'inline-block' }} type="secondary" strong>Field Type</Text>
                <Select
                    placeholder="Type"
                    style={{ width: 250 }}
                    value={item.type}
                    onChange={(value) => handleChange(index, 'type', value, type)}
                    disabled={type === 'input'}
                >
                    <Option value="text">Text</Option>
                    <Option value="number">Number</Option>
                    <Option value="boolean">Boolean</Option>
                </Select>
            </div>
            <div style={{ display: 'flex', gap: '20px', alignContent: "center", justifyContent: "flex-start" }}>
                <Text style={{ width: '200px', display: 'inline-block' }} type="secondary" strong>Field Description</Text>
                <Input
                    placeholder="Description"
                    style={{ width: 250 }}
                    value={item.description}
                    onChange={(e) => handleChange(index, 'description', e.target.value, type)}
                />
            </div>
            {/* Remove Button */}
            <div style={{ display: "flex", justifyContent: "flex-end" }}>
                <Button style={{ color: "white", background: "red", width: "200px" }} onClick={() => handleRemove(index, type)}>Remove</Button>
            </div>
        </div>
    )
}

const AddInputBlock = ({ messageList, addItem }) => {

    const [itemNameToAdd, setItemNameToAdd] = useState("");


    const [currentMessageName, setCurrentMessageName] = useState("");
    const fileds = messageList.filter((message) => message.name === currentMessageName)[0]?.fields
    const name2fields = {}
    if (fileds) {
        fileds.map((field) => {
            name2fields[field.name] = field
        })
    }


    return (
        <div style={{ display: "flex", justifyContent: "flex-end", width: "500px", flexDirection: "column", border: "1px solid #d9d9d9", padding: "10px", gap: "10px" }} >
            < div style={{ display: 'flex', gap: '20px', alignContent: "center", justifyContent: "flex-start" }}>
                <Text style={{ width: '200px', display: 'inline-block' }} type="secondary" strong>Source Message of Input Data</Text>
                <Select
                    placeholder="Type"
                    style={{ width: 250 }}
                    value={currentMessageName}
                    onChange={(value) => setCurrentMessageName(value)}
                >
                    {messageList.map((message) => {
                        return <Option value={message.name}>{message.name}</Option>
                    })}
                </Select>
            </div>
            <div style={{ display: 'flex', gap: '20px', alignContent: "center", justifyContent: "flex-start" }}>
                <Text style={{ width: '200px', display: 'inline-block' }} type="secondary" strong>Specific Field</Text>
                <Select
                    placeholder="Type"
                    style={{ width: 250 }}
                    value={itemNameToAdd}
                    onChange={(value) => setItemNameToAdd(value)}
                >
                    {
                        currentMessageName && messageList.filter((message) => message.name === currentMessageName)[0].fields.map((field) => {
                            return <Option value={
                                field.name
                            }>{"name: " + field.name + " " + "type: " + field.type}</Option>
                        })
                    }
                </Select>
            </div>
            <div style={{ display: 'flex', gap: '20px', alignContent: "center", justifyContent: "flex-end" }}>
                <Button onClick={() => addItem('input',
                    name2fields[itemNameToAdd]
                )}>Add Input</Button>
            </div>
        </div>
    )

}


const DmnModal = ({ dataElementId, xmlData, open: isModalOpen, onClose, onSave }) => {


    const DmnDrawerRef = useRef()
    const [name, setName] = useState("")


    const [activeTabKey, setActiveTabKey] = useState('businessRuleTask');

    const handleOk = async () => {
        if (DmnDrawerRef.current === undefined) {
            return;
        }
        const { xml, svg } = DmnDrawerRef.current?.getXmlAndSvg() || {};
        // console.log('xml', xml);
        onSave(dataElementId, { "dmnContent": xml, "name": name, "svgContent": svg });
        // updateBpmnName();
        onClose && onClose(true);
    };


    const handleCancel = () => {
        onClose && onClose(false);
    };


    // Slot Definition
    const modeler = window.bpmnjs;
    const elementRegistry = modeler.get('elementRegistry');
    const commandStack = modeler.get('commandStack');
    const shape = elementRegistry.get(dataElementId);

    const messageList = Object.keys(elementRegistry._elements).map(
        (key) => elementRegistry._elements[key]
    ).filter((element) => element.element.type === 'bpmn:Message').map((element) => {
        const doc = element.element.businessObject.documentation[0]
        let fields = []
        if (doc) {
            const content = JSON.parse(doc.text).properties
            // {\"input1\":{\"type\":\"string\",\"description\":\"123\"}
            fields = Object.keys(content).map((key) => {
                return {
                    name: key,
                    type: content[key].type,
                    description: content[key].description
                }
            })
        }
        return {
            name: element.element.businessObject.id,
            fields: fields
        }
    })


    const [inputs, setInputs] = useState([]);
    const [outputs, setOutputs] = useState([]);

    const defineIOofActivity = (shape) => {
        commandStack.execute('element.updateProperties', {
            element: shape,
            properties: {
                'documentation': [
                    modeler._moddle.create("bpmn:Documentation", {
                        text: JSON.stringify({
                            "inputs": inputs,
                            "outputs": outputs
                        })
                    })
                ]
            }
        });
    }

    const handleInputChange = (index, key, value, type) => {
        if (type === 'input') {
            const newInputs = [...inputs];
            newInputs[index][key] = value;
            setInputs(newInputs);
        } else {
            const newOutputs = [...outputs];
            newOutputs[index][key] = value;
            setOutputs(newOutputs);
        }
    };

    const addItem = (type, item = {
        name: "",
        type: "",
        description: ""
    }) => {
        if (type === 'input') {
            setInputs([...inputs, { name: item.name, type: item.type, description: item.description }]);
        } else {
            setOutputs([...outputs, { name: item.name, type: item.type, description: item.description }]);
        }
    };

    const removeItem = (index, type) => {
        if (type === 'input') {
            const newInputs = [...inputs];
            newInputs.splice(index, 1);
            setInputs(newInputs);
        } else {
            const newOutputs = [...outputs];
            newOutputs.splice(index, 1);
            setOutputs(newOutputs);
        }
    }


    return (
        <div>
            <Modal
                className='content'
                open={isModalOpen}
                onOk={handleOk}
                onCancel={handleCancel}
                styles={
                    {
                        body: { width: 1700, height: 'calc(100vh - 300px)' }
                    }
                }
                style={{ top: 64 }}
                centered
                width={1800}
            >
                <Tabs defaultActiveKey="1" onChange={(key) => setActiveTabKey(key)}>
                    <Tabs.TabPane tab="Business Rule Task" key="businessRuleTask">
                        <div>
                            Business Rule Task Name<br />
                            <Input
                                placeholder="Change Business Rule Task Name"
                                style={{ width: '30%' }}
                                value={name}
                                onChange={(e) => {
                                    setName(e.target.value);
                                }}
                            />
                        </div>
                        <div >
                            <Row>
                                <Col span={8} style={{ overflow: "auto", maxHeight: "70vh" }} >
                                    {inputs.map((input, index) => (
                                        <IOBlock
                                            key={index}
                                            index={index}
                                            type="input"
                                            item={input}
                                            handleChange={handleInputChange}
                                            handleRemove={removeItem}
                                        />
                                    ))}
                                    <AddInputBlock messageList={messageList} addItem={addItem} />

                                </Col>
                                <Col span={8} style={{ overflow: "auto", maxHeight: "70vh" }}>
                                    {outputs.map((output, index) => (
                                        <IOBlock key={index} index={index} type="output" item={output} handleChange={handleInputChange} handleRemove={removeItem} />
                                    ))}
                                    <div style={{ display: "flex", justifyContent: "flex-end", width: "500px" }} >
                                        <Button onClick={() => addItem('output')}>Add Output</Button>
                                    </div>
                                </Col>
                            </Row>

                        </div>
                    </Tabs.TabPane >
                    <Tabs.TabPane tab="DMN Drawer" key="dmnDrawer">
                        <DmnDrawer
                            ref={DmnDrawerRef}
                            dataElementId={dataElementId}
                            xmlData={xmlData}
                        />
                    </Tabs.TabPane>
                </Tabs >

            </Modal >
        </div >
    );
};

export default DmnModal;
