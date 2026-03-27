import React, { useState, useEffect } from 'react';
import { Button, Modal, Form, Input, message } from 'antd';
import { useInviteUser } from './hooks'
import { useAppSelector } from '@/redux/hooks';


const InviteModal: React.FC = () => {
    const [visible, setVisible] = useState(false);
    const [inviteForm] = Form.useForm();
    const [isValidInput, setIsValidInput] = useState(true);


    const currentOrgId = useAppSelector((state) => state.org.currentOrgId)
    const [inviteUser, inviteResult] = useInviteUser()

    const onFinish = (values: any) => {
        inviteUser({
            orgId: currentOrgId,
            email: values.email
        })
    }

    useEffect(() => {
        if (inviteResult.isSuccess) {
            message.success('Invite Success!')
            setVisible(false)
            inviteForm.resetFields()
        }
        if (inviteResult.isError) {
            message.error('Invite Failed!')
        }
    }, [inviteResult.isSuccess, inviteResult.isError])

    return (
        <>
            <Button type="primary" onClick={() => setVisible(true)}>INVITE NEW MEMBERS</Button>
            <Modal
                title="Invite User"
                open={visible}
                // onOk={() => setVisible(false)}
                onCancel={() => setVisible(false)}
                confirmLoading={inviteResult.isLoading}
                okButtonProps={{
                    htmlType: "submit",
                    form: "basic",
                }}
            >
                <Form
                    name="basic"
                    labelCol={{ span: 8 }}
                    wrapperCol={{ span: 16 }}
                    style={{ maxWidth: 600 }}
                    form={inviteForm}
                    onFinish={onFinish}
                    autoComplete="off"
                    preserve={false} // 在Modal关闭后，销毁Field
                >
                    <Form.Item
                        label="User's Email"
                        name="email"
                        rules={[
                            { required: true, message: "Please input User's Email!" },
                        ]}
                        validateStatus={!isValidInput ? "error" : undefined}
                        help={
                            !isValidInput
                                ? "This ID is invalid! Please input again."
                                : undefined
                        }
                    >
                        <Input allowClear />
                    </Form.Item>
                </Form>
            </Modal>
        </>
    )
}

export default InviteModal;