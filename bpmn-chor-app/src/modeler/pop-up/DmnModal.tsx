// @ts-nocheck
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
import DmnDrawer from "./DmnDrawer"
import Draggable from 'react-draggable';
import type { DraggableEvent, DraggableData } from 'react-draggable';


const IOBlock = ({
    index, type, item, handleChange, handleRemove
}) => {

    return (
        <div key={index} style={{
            marginTop: 20, marginBottom: 10, gap: 10, display: "flex", flexDirection: "column", padding: "16px", width: "100%", borderRadius: "12px", background: "#fff", boxShadow: "0 8px 24px rgba(15,23,42,0.08)",
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
                    <Option value="string">String</Option>
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
                <Button danger type="text" style={{ width: 160 }} onClick={() => handleRemove(index, type)}>Remove</Button>
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
        <div style={{ display: "flex", justifyContent: "flex-end", width: "100%", flexDirection: "column", padding: "16px", gap: "12px", borderRadius: 12, background: "#fff", boxShadow: "0 8px 24px rgba(15,23,42,0.08)" }} >
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
                <Button type="primary" onClick={() => addItem('input',
                    name2fields[itemNameToAdd]
                )}>Add Input</Button>
            </div>
        </div>
    )

}


const DmnModal = ({ dataElementId, xmlData, open: isModalOpen, onClose, onSave }) => {

    useEffect(()=>{
        console.log("DmnModal")
        console.log(dataElementId)
        console.log(xmlData)
    },dataElementId)

    const clean = () => {
        setInputs([]);
        setOutputs([]);
    }

    const DmnDrawerRef = useRef(null)
    const [name, setName] = useState("")


    const [activeTabKey, setActiveTabKey] = useState('businessRuleTask');

    const handleOk = async () => {
        // depend on activeTabKey

        if (activeTabKey === 'businessRuleTask') {
            defineIOofActivity(shape);

            onClose && onClose(true);
            clean()
            // Clear the inputs and outputs

        } else {
            const { xml, svg } = await DmnDrawerRef.current?.getXmlAndSvg();
            onSave(dataElementId, { "dmnContent": xml, "name": name, "svgContent": svg });
            onClose && onClose(true);
        }
    };


    const handleCancel = () => {
        onClose && onClose(false);
        clean()
    };


    // Slot Definition
    const modeler = window.bpmnjs;
    const elementRegistry = modeler.get('elementRegistry');
    const commandStack = modeler.get('commandStack');
    const shape = elementRegistry.get(dataElementId);
    const eventBus = modeler.get('eventBus');

    const messageList = Object.keys(elementRegistry._elements).map(
        (key) => elementRegistry._elements[key]
    ).filter((element) => element.element.type === 'bpmn:Message').map((element) => {
        const documentation = element.element.businessObject.documentation;
        let fields = []
        if (documentation) {
            const doc = element.element.businessObject.documentation[0]
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

    // Read origin inputs and outputs

    const [inputs, setInputs] = useState([]);
    const [outputs, setOutputs] = useState([]);


    useEffect(() => {
        if (isModalOpen === false) return
        const doc = shape.businessObject.documentation[0];
        if (doc) {
            const content = JSON.parse(doc.text);
            if (content.inputs) {
                setInputs(content.inputs);
            }
            if (content.outputs) {
                setOutputs(content.outputs);
            }
        }
        const businessRuleTaskName = shape.businessObject.name;
        if (businessRuleTaskName) {
            setName(businessRuleTaskName);
        }
    }, [isModalOpen]);

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
        commandStack.execute('element.updateLabel', {
            element: shape,
            newLabel: name,
        });
        eventBus.fire('element.changed', { element: shape });
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


    const draggleRef = useRef<HTMLDivElement | null>(null)
    const [dragDisabled, setDragDisabled] = useState(true);
    const [bounds, setBounds] = useState({ left: 0, top: 0, bottom: 0, right: 0 });

    const onStart = (_event: DraggableEvent, uiData: DraggableData) => {
        const { clientWidth, clientHeight } = window.document.documentElement;
        const targetRect = draggleRef.current?.getBoundingClientRect();
        if (!targetRect) {
            return;
        }
        setBounds({
            left: -targetRect.left + uiData.x,
            right: clientWidth - (targetRect.right - uiData.x),
            top: -targetRect.top + uiData.y,
            bottom: clientHeight - (targetRect.bottom - uiData.y),
        });
    };

    return (
        <div>
            <Modal
                title={
                    <div
                        style={{ cursor: 'move', display: 'flex', flexDirection: 'column', gap: 4 }}
                        onMouseOver={() => dragDisabled && setDragDisabled(false)}
                        onMouseOut={() => setDragDisabled(true)}
                    >
                        <span style={{ fontWeight: 600, fontSize: 18 }}>DMN 与业务规则配置</span>
                        <span style={{ fontSize: 12, color: '#64748b' }}>配置业务规则与 DMN 决策逻辑</span>
                    </div>
                }
                open={isModalOpen}
                onOk={handleOk}
                onCancel={handleCancel}
                width={1200}
                styles={{
                    header: {
                        borderBottom: '1px solid #e2e8f0',
                        padding: '16px 24px'
                    },
                    body: {
                        width: 1140,
                        maxHeight: 'calc(100vh - 220px)',
                        overflow: 'auto',
                        padding: '0 24px 24px',
                        background: '#f8fafc'
                    },
                    footer: {
                        borderTop: 'none',
                        padding: '16px 24px 24px'
                    }
                }}
                centered
                maskStyle={{ backdropFilter: 'blur(1px)' }}
                modalRender={(modal) => (
                    <Draggable
                        nodeRef={draggleRef}
                        disabled={dragDisabled}
                        bounds={bounds}
                        onStart={onStart}
                    >
                        <div ref={draggleRef}>{modal}</div>
                    </Draggable>
                )}
            >
                <Tabs
                    defaultActiveKey="1"
                    onChange={(key) => setActiveTabKey(key)}
                    tabBarGutter={32}
                    tabBarStyle={{ marginBottom: 24 }}
                >
                    <Tabs.TabPane tab="Business Rule Task" key="businessRuleTask" style={{ paddingTop: 12 }}>
                        <div style={{ marginBottom: 24, display: 'flex', flexDirection: 'column', gap: 8 }}>
                            <Text type="secondary" strong>Business Rule Task Name</Text>
                            <Input
                                placeholder="Change Business Rule Task Name"
                                style={{ width: 320 }}
                                value={name}
                                onChange={(e) => {
                                    setName(e.target.value);
                                }}
                            />
                        </div>
                        <div>
                            <Row gutter={24} justify="space-between">
                                <Col span={12} style={{ overflowY: "auto", maxHeight: "calc(100vh - 360px)", paddingRight: 8 }} >
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
                                <Col span={12} style={{ overflowY: "auto", maxHeight: "calc(100vh - 360px)", paddingLeft: 8 }}>
                                    {outputs.map((output, index) => (
                                        <IOBlock key={index} index={index} type="output" item={output} handleChange={handleInputChange} handleRemove={removeItem} />
                                    ))}
                                    <div style={{ display: "flex", justifyContent: "flex-end", width: "100%" }} >
                                        <Button type="primary" ghost onClick={() => addItem('output')}>Add Output</Button>
                                    </div>
                                </Col>
                            </Row>

                        </div>
                    </Tabs.TabPane >
                    <Tabs.TabPane tab="DMN Drawer" key="dmnDrawer">
                        <div style={{ height: '65vh', background: '#fff', borderRadius: 12, boxShadow: '0 8px 24px rgba(15,23,42,0.08)', overflow: 'hidden', padding: 12 }}>
                            <DmnDrawer
                                ref={DmnDrawerRef}
                                dataElementId={dataElementId}
                                xmlData={xmlData}
                            />
                        </div>
                    </Tabs.TabPane>
                </Tabs >

            </Modal >
        </div >
    );
};

export default DmnModal;
