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


  // React.useEffect(() => {
  //   if (shape != null) {
  //     commandStack.execute('element.updateProperties', {
  //       element: shape,
  //       properties: {
  //         // 修改的内容是 shape.businessObject
  //         // 可以修改ID， 但感觉不必要
  //         // 'id': newId,
  //         // 也可以用这个修改title
  //         // 'name': newTitle, // 即element.updateLabel的功能
  //         // 修改 documentation, 数组，每行1个
  //         'documentation': [
  //           modeler._moddle.create("bpmn:Documentation", {
  //             text: JSON.stringify(paramListOptions)
  //           })
  //         ]
  //       }
  //     });
  //   }
  // }, [paramListOptions]);



  const [name, setName] = React.useState(shape !== null ? shape.businessObject.name : "");
  const [dataSource, setDataSource] = React.useState([]);

  const loadDataFromBPMN = () => {
    if (shape != null) {
      const data = shape.businessObject.documentation.length > 0 ? JSON.parse(shape.businessObject.documentation[0].text) : {
        properties: {},
        required: [],
        files: {},
        'file required': []
      }
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
    // 构造参数 from dataSource
    let properties = {};
    let files = {};
    let required = [];
    let fileRequired = [];

    dataSource.forEach((item) => {
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
    })

    const uploadData = {
      properties: properties,
      required: required,
      files: files,
      'file required': fileRequired
    }



    // update参数
    if (shape != null) {
      commandStack.execute('element.updateProperties', {
        element: shape,
        properties: {
          'documentation': [
            modeler._moddle.create("bpmn:Documentation", {
              text: JSON.stringify(uploadData)
            })
          ]
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
