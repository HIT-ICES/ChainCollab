import React, { useState, useEffect } from 'react';
import UserInfoCard from './UserInfoCard';
import InviteModal from './InviteModal.tsx';
import { useUserListData } from './hooks.ts';
import { useAppSelector } from '@/redux/hooks.ts';

const UsersManage: React.FC = () => {

  const currentOrgId = useAppSelector(state => state.org.currentOrgId);
  const [userList, { isLoading, isError, isSuccess }, refetch] = useUserListData(currentOrgId);

  return (
    <>
      {/* Button to Invite a user to join Organization */}
      <div style={{ paddingBottom: '10px', paddingTop:'10px' }}>
        <InviteModal />
      </div>

      {/* User List */}

      {isLoading && <div>loading...</div>}
      {isError && <div>error...</div>}
      {isSuccess && userList.map((user, index) => {
        return <UserInfoCard key={index} name={
          user.name} email={user.email}
          onDelete={() => { console.log('delete') }}
        />
      })}
    </>)
}

export default UsersManage;