import React, { useState } from 'react';
import { Modal, Button } from 'antd';

const ParticipantDmnBindingModal = ({ open, setOpen }) => {

  const handleOk = () => {
    setOpen(false);
  };

  const handleCancel = () => {
    setOpen(false);
  };

  return (
    <div>
      <Modal title="Custom Modal" open={open} onOk={handleOk} onCancel={handleCancel}>
        <div style={{ display: 'flex', marginBottom: '20px' }}>
          <div style={{ flex: 1, borderRight: '1px solid #ccc', paddingRight: '10px' }}>
            <MyLeftComponent />
          </div>
          <div style={{ flex: 1, paddingLeft: '10px' }}>
            <MyRightComponent />
          </div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <MySVGComponent />
        </div>
      </Modal>
    </div>
  );
};

const MyLeftComponent = () => (
  <div>
    <h3>Left Component</h3>
    {/* 这里放置左边组件的内容 */}
  </div>
);

const MyRightComponent = () => (
  <div>
    <h3>Right Component</h3>
    {/* 这里放置右边组件的内容 */}
  </div>
);

const MySVGComponent = () => (
  <div>
    <h3>SVG Component</h3>
    {/* 这里放置SVG内容 */}
    <svg width="100" height="100">
      <circle cx="50" cy="50" r="40" stroke="black" strokeWidth="3" fill="red" />
    </svg>
  </div>
);

export default ParticipantDmnBindingModal;
