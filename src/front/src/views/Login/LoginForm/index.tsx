import React, { useEffect, useState } from "react";
import {
  LockOutlined,
  UserOutlined,
  MailOutlined,
  HomeOutlined,
} from "@ant-design/icons";
import { Button, Checkbox, Form, Input, Tabs, message } from "antd";
import styles from "./index.module.scss";
import { useNavigate } from "react-router-dom";
import LoginTitle from "./LoginLogo";
const { TabPane } = Tabs;


//Action Dispatch and Selector
import { useAppDispatch, useAppSelector } from '@/redux/hooks'
import { selectUser, loginAction, registerUserAction, registerReset } from '@/redux/slices/userSlice'

import { loginStart, loginSuccess, loginFailed, logout } from '@/redux/slices/userSlice'

const App: React.FC = () => {
  const navigateTo = useNavigate();
  const { loginFormBox, loginFormButton } = styles;
  const [registerForm] = Form.useForm();
  const [loginForm] = Form.useForm();

  const loginStatus = useAppSelector(selectUser).loginStatus === 'login';
  const registerStatus = useAppSelector(selectUser).registerStatus;
  const dispatch = useAppDispatch();
  const [activeKey, setActiveKey] = useState("1");
  const onKeyChange = (key: string) => {
    setActiveKey(key);
  }

  const isSuccess = useAppSelector(
    (state) => state.user
  ).loginStatus === 'success';

  useEffect(() => {
    if (registerStatus !== 'idle') {
      if (registerStatus === 'failed') {
        message.error('Register Failed');
      } else if (registerStatus === 'success') {
        message.success('Register Succeeded');
        loginForm.setFieldsValue({
          email: registerForm.getFieldValue('email'),
          password: registerForm.getFieldValue('password')
        });
        registerForm.resetFields();
        setActiveKey('1');
      }
      dispatch(registerReset());
    }
  }
    , [registerStatus]);

  useEffect(() => {
    if (isSuccess) {
      navigateTo('/home');
    }
  }, [isSuccess]);


  const onFinishLogin = async (values: any) => {
    dispatch(loginAction(values.email, values.password))
  };

  const onFinishRegister = (values: any) => {
    // 注册处理逻辑
    dispatch(registerUserAction(values.username, values.email, values.password))
  };

  const validateMessages = {
    required: "${label} is required!",
    types: {
      email: "${label} is not valid email!",
      pattern: {
        mismatch: "${label} format not correct!",
      },
    },
  };

  const passwordValidator = (form) => ({
    validator(_, value) {
      if (!value || form.getFieldValue("password") === value) {
        return Promise.resolve();
      }
      return Promise.reject(new Error("The two passwords do not match.!"));
    },
  });

  return (
    <div className={`${loginFormBox} global-center`}>
      <LoginTitle />
      <Tabs defaultActiveKey="1" centered activeKey={activeKey} onChange={onKeyChange} >
        <TabPane tab="Login" key="1">
          {/* 登录表单 */}
          <Form
            form={loginForm}
            name="normal_login"
            className="login-form"
            initialValues={{ remember: true }}
            onFinish={onFinishLogin}
          >
            <Form.Item
              name="email"
              rules={[{ required: true, message: "Please Input Email" }]}
            >
              <Input
                prefix={<UserOutlined className="site-form-item-icon" />}
                placeholder="Email"
              />
            </Form.Item>
            <Form.Item
              name="password"
              rules={[{ required: true, message: "Please Input Password" }]}
            >
              <Input
                prefix={<LockOutlined className="site-form-item-icon" />}
                type="password"
                placeholder="Password"
              />
            </Form.Item>
            <Form.Item>
              <div
                className="global-center"
                style={{ justifyContent: "space-between" }}
              >
                <Form.Item name="remember" valuePropName="checked" noStyle>
                  <Checkbox>Remember the password</Checkbox>
                </Form.Item>

                <a className="login-form-forgot" href="">
                  Forgot Password?
                </a>
              </div>
            </Form.Item>

            <Form.Item>
              <Button
                type="primary"
                htmlType="submit"
                className={loginFormButton}
                loading={loginStatus}
              >
                Login
              </Button>
            </Form.Item>
          </Form>
        </TabPane>

        <TabPane tab="Register" key="2">
          {/* 注册表单 */}
          <Form
            name="register"
            onFinish={onFinishRegister}
            validateMessages={validateMessages}
            form={registerForm}
          >
            <Form.Item
              name="username"
              label="Username"
              rules={[
                { required: true },
                {
                  pattern: /^[a-zA-Z0-9]{3,}$/,
                  message: "username format worng!",
                },
              ]}
            >
              <Input prefix={<HomeOutlined />} placeholder="Username" />
            </Form.Item>
            <Form.Item
              name="email"
              label="Email"
              rules={[{ required: true }, { type: "email" }]}
            >
              <Input prefix={<MailOutlined />} placeholder="Email" />
            </Form.Item>
            <Form.Item
              name="password"
              label="Password"
              rules={[{ required: true }]}
              hasFeedback
            >
              <Input.Password prefix={<LockOutlined />} placeholder="Password" />
            </Form.Item>
            <Form.Item
              name="confirmPassword"
              label="Confirm Password"
              dependencies={["password"]}
              hasFeedback
              rules={[
                { required: true, message: "Please re-enter the password!" },
                passwordValidator(registerForm),
              ]}
            >
              <Input.Password
                prefix={<LockOutlined />}
                placeholder="Confirm Password"
              />
            </Form.Item>
            <Form.Item>
              <Button
                type="primary"
                htmlType="submit"
                className={loginFormButton}
                loading={registerStatus === 'register'}
              >
                Register
              </Button>
            </Form.Item>
          </Form>
        </TabPane>
      </Tabs>
    </div>
  );
};

export default App;
