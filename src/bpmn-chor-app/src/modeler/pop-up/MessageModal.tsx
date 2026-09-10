// @ts-nocheck
import * as React from 'react';
import { Modal, Button, Input, Select, List, Typography, Table } from 'antd';

const paramTypes = [
  {
    value: 'boolean',
    label: 'boolean',
  },
  {
    value: 'json',
    label: 'json',
  },
  {
    value: 'string',
    label: 'string',
  },
  {
    value: 'number',
    label: 'number',
  },
  {
    value: 'file',
    label: 'file',
  },

];

const defaultMessageSchema = {
  properties: {},
  required: [],
  files: {},
  'file required': []
};

const localName = (item) => {
  return item?.$type?.split(':').pop() || item?.localName || item?.tagName?.split(':').pop();
};

const requiredValue = (value) => {
  return value === true || value === 'true' || value === '1';
};

const parseDefinition = (item) => {
  if (!item?.definition) {
    return {};
  }
  try {
    return JSON.parse(item.definition);
  } catch (error) {
    return {};
  }
};

const readMessageSchemaFromExtension = (businessObject) => {
  const values = businessObject?.extensionElements?.values || [];
  const schema = values.find((value) => localName(value) === 'MessageSchema');
  if (!schema) {
    return null;
  }

  const data = {
    properties: {},
    required: [],
    files: {},
    'file required': []
  };

  (schema.properties || []).forEach((property) => {
    const definition = parseDefinition(property);
    const name = property.name || definition.name;
    if (!name) {
      return;
    }
    data.properties[name] = {
      type: definition.type || property.type || 'string',
      description: definition.description || property.description || ''
    };
    if (requiredValue(definition.required ?? property.required)) {
      data.required.push(name);
    }
  });

  (schema.files || []).forEach((file) => {
    const definition = parseDefinition(file);
    const name = file.name || definition.name;
    if (!name) {
      return;
    }
    data.files[name] = {
      type: definition.type || file.type || 'file',
      description: definition.description || file.description || ''
    };
    if (requiredValue(definition.required ?? file.required)) {
      data['file required'].push(name);
    }
  });

  return data;
};

const readMessageSchemaFromDocumentation = (businessObject) => {
  const documentation = businessObject?.documentation;
  if (!documentation?.length || !documentation[0]?.text) {
    return null;
  }
  try {
    return JSON.parse(documentation[0].text);
  } catch (error) {
    return null;
  }
};

const buildMessageSchemaPayload = (dataSource) => {
  const properties = {};
  const files = {};
  const required = [];
  const fileRequired = [];

  dataSource.forEach((item) => {
    if (!item.name) {
      return;
    }
    if (item.type != 'file') {
      properties[item.name] = {
        type: item.type,
        description: item.description
      };
      if (item.required) {
        required.push(item.name);
      }
    } else {
      files[item.name] = {
        type: item.type,
        description: item.description
      };
      if (item.required) {
        fileRequired.push(item.name);
      }
    }
  });

  return {
    properties,
    required,
    files,
    'file required': fileRequired
  };
};

const buildMessageSchemaExtension = (modeler, shape, payload) => {
  const extensionElements = shape.businessObject.extensionElements
    || modeler._moddle.create('bpmn:ExtensionElements', { values: [] });

  const messageSchema = modeler._moddle.create('abc:MessageSchema', {
    properties: [],
    files: []
  });

  Object.keys(payload.properties).forEach((name) => {
    const definition = payload.properties[name];
    const required = payload.required.includes(name);
    const property = modeler._moddle.create('abc:Property', {
      name,
      type: definition.type,
      description: definition.description,
      required,
      definition: JSON.stringify(definition)
    });
    property.$parent = messageSchema;
    messageSchema.properties.push(property);
  });

  Object.keys(payload.files).forEach((name) => {
    const definition = payload.files[name];
    const required = payload['file required'].includes(name);
    const file = modeler._moddle.create('abc:File', {
      name,
      type: definition.type,
      description: definition.description,
      required,
      definition: JSON.stringify(definition)
    });
    file.$parent = messageSchema;
    messageSchema.files.push(file);
  });

  messageSchema.$parent = extensionElements;
  extensionElements.values = (extensionElements.values || [])
    .filter((value) => localName(value) !== 'MessageSchema')
    .concat(messageSchema);
  extensionElements.$parent = shape.businessObject;

  return extensionElements;
};

export default function MessageModal({ dataElementId, open: isModalOpen, onClose }) {
  const [title, setTitle] = React.useState(`message id: ${dataElementId}`);

  // //用于选择要添加元素的type
  // const [paramType, setParamType] = React.useState("");
  // const [paramListOptions, setParamListOptions] = React.useState(
  //   [
  //     { label: 'Vue', value: 'Vue', type: 'boolean' },
  //     { label: 'React', value: 'React', type: 'number' },
  //     { label: 'Angular', value: 'Angular', type: 'string' },
  //   ]
  // );

  const modeler = window.bpmnjs;
  const elementRegistry = modeler.get('elementRegistry');
  const commandStack = modeler.get('commandStack');
  const shape = elementRegistry.get(dataElementId);
  console.log(dataElementId, shape)


  const [name, setName] = React.useState(shape !== null ? shape.businessObject.name : "");
  const [dataSource, setDataSource] = React.useState([]);

  const loadDataFromBPMN = () => {
    if (shape != null) {
      const data = readMessageSchemaFromExtension(shape.businessObject)
        || readMessageSchemaFromDocumentation(shape.businessObject)
        || defaultMessageSchema;
      const propertiesData = Object.keys(data.properties).map((key, index) => {
        return {
          key: index,
          name: key,
          type: data.properties[key].type,
          description: data.properties[key].description,
          required: data.required.includes(key)
        };
      });

      const filesData = Object.keys(data.files).map((key, index) => {
        return {
          key: index + Object.keys(data.properties).length,
          name: key,
          type: data.files[key].type,
          description: data.files[key].description,
          required: data['file required'].includes(key)
        };
      });

      setDataSource([...propertiesData, ...filesData]);
    }
  }

  React.useEffect(() => {
    if (shape !=null){
      setName(shape.businessObject.name)
    }
  }, [shape]);

  React.useEffect(() => {
    loadDataFromBPMN();
  }, [shape]);

  const updateDataToBPMN = () => {
    // update标题
    if (shape != null) {
      commandStack.execute('element.updateLabel', {
        element: shape,
        newLabel: name,
      });
    }
    // update参数
    if (shape != null) {
      const uploadData = buildMessageSchemaPayload(dataSource);
      commandStack.execute('element.updateProperties', {
        element: shape,
        properties: {
          'extensionElements': buildMessageSchemaExtension(modeler, shape, uploadData),
          'documentation': []
        }
      });
    }
  }



  const columns = [

    {
      title: 'Type',
      dataIndex: 'type',
      key: 'type',
      render: (text, record) => (
        <Select defaultValue={record.type} style={{ width: 120 }} onChange={(value) => {
          const copy = [...dataSource];
          copy[record.key].type = value;
          setDataSource(copy);
        }
        }>
          {paramTypes.map((item) => {
            return <Select.Option value={item.value}>{item.label}</Select.Option>
          })}
        </Select>
      )
    },
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      render: (text, record) => (
        <Input value={record.name} onChange={(e) => {
          const copy = [...dataSource];
          copy[record.key].name = e.target.value;
          setDataSource(copy);
        }
        } />
      )
    },
    {
      title: 'Discription',
      dataIndex: 'discription',
      key: 'discription',
      render: (text, record) => (
        <Input value={record.description} onChange={(e) => {
          const copy = [...dataSource];
          copy[record.key].description = e.target.value;
          setDataSource(copy);
        }
        } />
      )
    },
    {
      title: 'Required',
      dataIndex: 'required',
      key: 'required',
      render: (text, record) => (
        <input
          type="checkbox"
          checked={record.required}
          onChange={(e) => {
            const copy = [...dataSource];
            copy[record.key].required = e.target.checked;
            setDataSource(copy);
          }}
        />
      )
    },
    {
      title: 'Action',
      dataIndex: '',
      key: 'x',
      render: (text, record) => (
        <a
          href="#"
          onClick={() => {
            const copy = [...dataSource];
            copy.splice(record.key, 1);
            setDataSource(copy);
          }}
        >
          Delete
        </a>
      )
    }
  ];


  const handleOk = () => {
    onClose && onClose(true);
    updateDataToBPMN()
  };

  const handleCancel = () => {
    onClose && onClose(false);
  };




  return (<Modal title={`message id: ${dataElementId}`} open={isModalOpen} onOk={handleOk} onCancel={handleCancel}
    rootClassName="chor-modal"
    width={800}
  >
    Message Name<br />
    <Input
      placeholder="ChangeMessageName"
      style={{ width: '50%', }}
      value={name}
      onChange={
        (e) => {
          setName(e.target.value);
        }
      }
    />
    <br />

    Parameter List
    {/* <List
      bordered
      dataSource={paramListOptions}
      renderItem={(item) => (
        <List.Item>
          <Typography.Text mark>{item.type}</Typography.Text> {item.value}
        </List.Item>
      )}
    /> */}
    <Table
      dataSource={dataSource}
      columns={columns}
      pagination={false}
    />
    <div style={{ display: 'flex', justifyContent: "flex-end", marginTop: "10px" }} >
      <Button type="primary" onClick={() => {
        // ADD New ITEM INTO dataSource
        const copy = [...dataSource];
        copy.push({ key: copy.length, name: '', type: 'string', description: '', required: false });
        setDataSource(copy);
      }}>Add New Field</Button>
      {/* delete Last Line */}
    </div>
  </Modal>);
}
