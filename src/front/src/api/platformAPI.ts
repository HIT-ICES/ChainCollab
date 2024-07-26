import { result } from "lodash";
import api from "./apiConfig";
import { env } from "process";

export const createOrg = async (orgName: string) => {
  const response = await api.post("/organizations", {
    name: orgName,
  });
  return response.data;
};

export const getOrgs = async () => {
  try {
    const response = await api.get("/organizations");
    return {
      orgs: response.data.map((org: any) => ({
        id: org.id,
        name: org.name,
      })),
    };
  } catch (err) {
    console.log(err);
  }
};

export const getOrg = async (orgId: string) => {
  const response = await api.get(`/organizations/${orgId}`);
  return response.data;
};

export const getOrgList = async () => {
  try {
    const res = await api.get("/organizations");
    return res.data.map((org: any) => ({
      id: org.id,
      name: org.name,
    }));
  } catch (err) {
    console.error("获取orgList失败", err);
    return []
  }
};

export const updateOrg = async (orgId: string, org: any) => {
  const response = {};
  return response;
};

export const deleteOrg = async (orgId: string) => {
  const response = {};
  return response;
};

// User

export const getUserList = async (orgId: string) => {
  const res = await api.get("users", {
    params: {
      org_id: orgId,
    },
  });
  return res.data.data.map((user: any) => ({
    id: user.id,
    name: user.username,
    email: user.email,
  }));
}

// Invition

export const inviteUserJoinOrg = async (orgId: string, email: string) => {
  const res = await api.post("/organization-invites", {
    org_uuid: orgId,
    user_email: email,
  });
  return res.data;
}

export const getUserInvitationList = async () => {
  const res = await api.get("/organization-invites");
  return res.data;
};

export const getUserInvitation = async (invitationId: string) => { };

export const acceptUserInvitation = async (invitationId: string) => {
  const res = await api.put(`/organization-invites/${invitationId}`, {
    status: "accept",
  });
  return res.data;
};

export const declineUserInvitation = async (invitationId: string) => {
  const res = await api.put(`/organization-invites/${invitationId}`, {
    status: "reject",
  });
  return res.data;
};

// Consortium

export const createConsortium = async (
  orgId: string,
  consortiumName: string
) => {
  const response = await api.post(`/consortiums`, {
    name: consortiumName,
    baseOrgId: orgId,
  });
  return response.data;
};

export const getConsortiumList = async (orgId: string) => {
  if (orgId === '') {
    return [];
  }
  try {
    const res = await api.get("consortiums", {
      params: {
        org_uuid: orgId,
      },
    });
    return res.data.map(({ id, name, ...rest }) => ({
      id,
      name,
    }));
  } catch (err) {
    console.error("获取consortiumList失败", err);
    return [];
  }
};

export const getConsortium = async (consortiumId: string) => {
  const response = {};
  return response;
};

// export const updateConsortium = async (consortiumId: string, consortium: any) => {

//     const response = {}
//     return response;

// };

// Consortium Invitation
export const inviteOrgJoinConsortium = async (
  orgId: string,
  consortiumId: string,
  invitorId: string
) => {
  try {
    await api.post("/consortium-invites", {
      org_uuid: orgId,
      consortium_uuid: consortiumId,
      invitor_uuid: invitorId,
    });
    return true;
  } catch (err) {
    console.error("邀请组织时，上传邀请失败", err);
    return false;
  }
};

export const getOrgInvitationList = async (orgId: string) => {
  if (orgId === '') {
    return [];
  }
  try {
    const res = await api.get("/consortium-invites", {
      params: {
        org_uuid: orgId,
      },
    });

    return res.data.map((invitation: any) => ({
      id: invitation.id,
      date: invitation.date,
      orgID: invitation.loleido_organization.id,
      orgName: invitation.loleido_organization.name,
      consortiumID: invitation.consortium.id,
      consortiumName: invitation.consortium.name,
      invitorID: invitation.invitor.id,
      invitorName: invitation.invitor.name,
      status: invitation.status,
    }));
  } catch (err) {
    console.error("拉取邀请消息失败", err);
    return [];
  }
};

export const getOrgInvitation = async (invitationId: string) => { };

export const acceptOrgInvitation = async (invitationId: string) => {
  try {
    await api.put(`/consortium-invites/${invitationId}`, {
      status: "accept",
    });
  } catch (err) {
    console.error("上传接受邀请消息失败", err);
  }
};

export const rejectOrgInvitation = async (invitationId: string) => {
  try {
    await api.put(`/consortium-invites/${invitationId}`, {
      status: "reject",
    });
  } catch (err) {
    console.error("上传拒绝邀请消息失败", err);
  }
};

// Memebership
export const createMembership = async (
  orgId: string,
  consortiumId: string,
  consortiumName: string
) => {
  try {
    await api.post(`/consortium/${consortiumId}/memberships`, {
      org_uuid: orgId,
      name: consortiumName,
    });
  } catch (err) {
    console.error("创建Membership时，上传失败", err);
  }
};

export const getMembershipList = async (consortiumId: string) => {
  try {
    const res = await api.get(`/consortium/${consortiumId}/memberships`);
    return res.data;
  } catch (err) {
    console.error("获取membershipList失败", err);
  }
};

export const getMembership = async (
  membershipId: string,
  consortiumId: string = '1',
) => {
  const res = await api.get(
    `/consortium/${consortiumId}/memberships/${membershipId}`
  );
  return res.data;
};

export const updateMembership = async (
  membershipId: string,
  membership: any
) => { };

export const deleteMembership = async (
  consortiumId: string,
  membershipId: string
) => {
  try {
    await api.delete(`/consortium/${consortiumId}/memberships/${membershipId}`);
  } catch (err) {
    console.error("删除Membership时，上传失败", err);
  }
};

// Environment

export const createEnvironment = async (consortiumId: string, name: string) => {
  try {
    const res = await api.post(`/consortium/${consortiumId}/environments`, {
      name: name,
    });
    return res.data;
  } catch (err) {
    console.error("创建env失败", err);
  }
};

export const getEnvironmentList = async (consortiumId: string) => {
  if (consortiumId === '') {
    return [];
  }

  try {
    const res = await api.get(`/consortium/${consortiumId}/environments`);
    return res.data.map((env: any) => ({
      id: env.id,
      name: env.name,
    }));
  } catch (err) {
    console.error("获取envList失败", err);
  }
};

export const getEnvironment = async (environmentId: string, consortiumId: string) => {
  if (environmentId === '') {
    return {};
  }
  try {
    const res = await api.get(`/consortium/${consortiumId}/environments/${environmentId}`);
    return {
      name: res.data.name,
      id: res.data.id,
      status: res.data.status,
      createdAt: res.data.created_at,
    }
  } catch (err) {
    console.error("获取env失败", err);
  }
};

export const updateEnvironment = async (
  environmentId: string,
  name: string
) => { };

export const deleteEnvironment = async (environmentId: string) => { };


export const getFabricIdentityList = async (resourceSetId) => {
  try {
    const res = await api.get(`/fabric_identities?resource_set_id=${resourceSetId}`);
    return res.data;
  } catch (err) {
    console.error("获取fabricIdentityList失败", err);
  }
}

export const retrieveFabricIdentity = async (fabricIdentityId) => {
  try {
    const res = await api.get(`/fabric_identities/${fabricIdentityId}`);
    return res.data;
  } catch (err) {
    console.error("获取fabricIdentity失败", err);
  }
}

export const createFabricIdentity = async (resourceSetId, info = {
  nameOfFabricIdentity: "",
  nameOfIdentity: "",
  secretOfIdentity: "",
  attributes: {
  }
}) => {
  try {
    const res = await api.post(`/fabric_identities`, {
      resource_set_id: resourceSetId,
      name_of_fabric_identity: info.nameOfFabricIdentity,
      name_of_identity: info.nameOfIdentity,
      secret_of_identity: info.secretOfIdentity,
      attributes: info.attributes
    });
    return res.data;
  } catch (err) {
    console.error("创建fabricIdentity失败", err);
  }
}

export const registerAPIKey = async (membershipId, envId) => {
  try {
    const res = await api.post(`/api_secret_keys`, {
      membership_id: membershipId
    });
    return res.data;
  } catch (err) {
    console.error("注册API Key失败", err);
  }
}

export const getAPIKeyList = async (membershipId, envId) => {
  if (envId === '') {
    return [];
  }
  try {
    const res = await api.get(`/api_secret_keys`, {
      params: {
        membership_id: membershipId
      }
    });
    return res.data;
  } catch (err) {
    console.error("获取API Key失败", err);
  }
}

export const getFireflyIdentity = async (envId, orgId) => {
  if (envId === '' || orgId === '') {
    return {};
  }
  try {
    const res = await api.get(`/search/search-identity-by-org-and-env`, {
      params: {
        env_id: envId,
        org_id: orgId
      }
    });
    return res.data;
  } catch (err) {
    console.error("获取fireflyIdentity失败", err);
  }
}