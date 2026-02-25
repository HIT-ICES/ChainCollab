import { useEffect, useState } from 'react';
import { getConsortiumList, getOrgList, getEnvironmentList } from '@/api/platformAPI';
import { ConsortiumItemType, OrgItemType, EnvItemType } from './types';


export const useOrgData = (): [OrgItemType[], () => void] => {
  // Example: 获取当前用户的org列表
  const [orgList, setOrgList] = useState<OrgItemType[]>([]);
  const [syncFlag, setSyncFlag] = useState<boolean>(false);
  useEffect(() => {
    let ignore = false;
    const fetchData = async () => {
      if (!localStorage.getItem("token")) {
        if (!ignore) setOrgList([]);
        return;
      }
      try {
        const res = await getOrgList();
        if (ignore) return
        setOrgList(res);
      } catch (err) {
        console.error("导航栏获取OrgList报错", err);
      }
    };
    fetchData();
    return () => { ignore = true; };
  }, [syncFlag]);
  const setSync = () => setSyncFlag(!syncFlag);
  return [orgList, setSync];
}

export const useConsortiaData = (orgId: string): [ConsortiumItemType[], () => void] => {
  // Example: 获取当前orgID对应的可用consortia列表，当currentOrgId切换就会发生变化
  const [consortiaList, setConsortiaList] = useState<ConsortiumItemType[]>([]);
  const [syncFlag, setSyncFlag] = useState<boolean>(false);
  useEffect(() => {
    let ignore = false;
    const fetchData = async (orgId: string) => {
      if (!localStorage.getItem("token")) {
        if (!ignore) setConsortiaList([]);
        return;
      }
      try {
        const res = await getConsortiumList(orgId);
        if (ignore) return [[], () => { }];
        setConsortiaList(res);
      } catch (err) {
        console.error("导航栏获取ConsortiaList报错", err);
      }
    };

    fetchData(orgId);
    return () => {
      ignore = true;
    };
  }, [orgId, syncFlag]);
  const setSync = () => setSyncFlag(!syncFlag);
  return [consortiaList, setSync];
}

export const useEnvData = (consortiumId: string): [EnvItemType[], boolean, () => void] => {
  // Example: 获取当前consortiumID对应的可用env列表，当currentConsortiumId切换就会发生变化
  const [envList, setEnvList] = useState<EnvItemType[]>([]);
  const [syncFlag, setSyncFlag] = useState<boolean>(false);
  const [ready, setReady] = useState<boolean>(false);
  useEffect(() => {
    let ignore = false;
    const fetchData = async (consortiumId: string) => {
      if (!localStorage.getItem("token")) {
        if (!ignore) {
          setEnvList([]);
          setReady(true);
        }
        return;
      }
      setReady(false);
      try {
        const res = await getEnvironmentList(consortiumId);
        if (ignore) return [[], () => { }];
        setEnvList(res);
      } catch (err) {
        console.error("导航栏获取EnvList报错", err);
      }
      setReady(true);
    };
    fetchData(consortiumId);
    return () => {
      ignore = true;
    };
  }, [consortiumId, syncFlag]);
  const setSync = () => setSyncFlag(!syncFlag);
  return [envList, ready, setSync];
}
