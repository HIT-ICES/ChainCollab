import React from 'react';
import { Modal, Typography } from 'antd';
import { ExclamationCircleFilled } from '@ant-design/icons';

const { Link } = Typography

interface Props {
  onDelete: () => void;
}

const DelMembership: React.FC<Props> = ({ onDelete }) => {
  const handleOk = () => {
    onDelete();
  };

  const showDeleteConfirm = () => {
    Modal.confirm({
      title: 'Delete Membership',
      icon: <ExclamationCircleFilled />,
      content: 'Are you sure you want to delete the Membership?',
      okText: 'Yes',
      okType: 'danger',
      cancelText: 'Cancel',
      onOk: handleOk,
    });
  };

  return (
    <Link type="danger" onClick={showDeleteConfirm} strong>
      DELETE MEMBERSHIP
    </Link>
  );
};

export default DelMembership;
