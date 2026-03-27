import { Avatar, Dropdown } from "antd";
import type { MenuProps } from "antd";
import React from "react";
import { removeAllCookies } from "@/utils/cookies.ts";
import { localStorageRemoveItemAll } from "@/utils/localStorage.ts";
import { useNavigate } from "react-router-dom";

import { useAppDispatch, useAppSelector } from '@/redux/hooks'
import {
  selectUser,
  logoutAction
} from '@/redux/slices/userSlice'

const UserInfo: React.FC = () => {

  const userInfo = useAppSelector(selectUser).userInfo;
  const navigateTo = useNavigate();
  const dispatch = useAppDispatch();
  const LogoutClick = () => {
    removeAllCookies();
    localStorageRemoveItemAll();
    dispatch(logoutAction());
    navigateTo("/login");
  };

  const items: MenuProps["items"] = [
    // {
    //   label: (
    //     <a
    //       className="text-3xl font-bold underline"
    //       href="https://www.antgroup.com"
    //     >
    //       1st menu item
    //     </a>
    //   ),
    //   key: "0",
    // },
    // {
    //   label: <a href="https://www.aliyun.com">2nd menu item</a>,
    //   key: "1",
    // },
    // {
    //   type: "divider",
    // },
    {
      label: (
        <a href="#" onClick={LogoutClick}>
          退出登录
        </a>
      ),
      key: "3",
    },
  ];

  return (
    <Dropdown menu={{ items }} trigger={["click"]} arrow={true}>
      <Avatar
        style={{ backgroundColor: "#00a2ae", cursor: "pointer", display: "flex", alignItems: "center"}}
        shape="square"
        size="large"
        gap={4}
        onClick={(e) => e?.preventDefault()}
      >
        {userInfo.username ? userInfo.username[0] : "链"}
      </Avatar>
    </Dropdown>
  );
};

export default UserInfo;
