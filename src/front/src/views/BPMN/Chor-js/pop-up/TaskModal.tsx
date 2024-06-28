import * as React from 'react';
import {Modal, Button, Input, Select, List, Typography, Form} from 'antd';

export default function TaskModal({dataElementId, open: isModalOpen, onClose}) {
  const title = `chor-task ID: ${dataElementId}`;

  const [taskName, setTaskName] = React.useState('');
  const [taskDescription, setTaskDescription] = React.useState("你好你好你好你好");

  const taskNameInputRef = React.useRef(null);
  const taskDescriptionInputRef = React.useRef(null);

  const handleOk = () => {
    onClose && onClose(true);
  };

  const handleCancel = () => {
    onClose && onClose(false);
  };

  const handleTaskNameInputOk = () => {
    setTaskName(taskNameInputRef.current.input.value);
    // TODO 1.即时同步 + Cancel时回滚?
    // TODO 2.延迟同步（点击Ok时同步）?
    testingfunction("ChoreographyTask_175oxwe", "msgTop", "$scope.task.parttop", "$scope.task.tname", "$scope.task.partbot", "msgbottom");
  };

  const handleTaskDescriptionInputOk = () => {
    setTaskDescription(taskDescriptionInputRef.current.input.value)
  };

  return (<Modal title={title} visible={isModalOpen} onOk={handleOk} onCancel={handleCancel}>

    Task Name<br />
    <Input ref={taskNameInputRef} placeholder="ChangetaskName" style={{ width: '50%', }} onPressEnter={handleTaskNameInputOk}></Input>
    <br />

    Task Description
    <Input ref={taskDescriptionInputRef} rows={4} value={taskDescription} placeholder="maxLength is 100" maxLength={100} onChange={handleTaskDescriptionInputOk} />
  </Modal>);
}
