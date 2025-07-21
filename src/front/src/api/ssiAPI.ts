import { result } from "lodash";
import api from "./apiConfig";
import { env } from "process";

export const getConnections = async (membershipId: string) => {
  const res = await api.get(`/memberships/${membershipId}/connections`);
  return res.data;
};

export const getPendingInvitations = async (membershipId: string) => {
  const res = await api.get(`/memberships/${membershipId}/connection_requests`);
  return res.data;
};

export const sendConnectionRequest = async (payload: {
  sender_id: string;
  sender_label: string;
  receiver_id: string;
  receiver_label: string;
}) => {
  const res = await api.post(`/connection_requests/`, payload);
  return res.data;
};

export const acceptConnectionRequest = async (
  invitationId: string,
  receiverId: string
) => {
  const res = await api.post(`/connection_requests/${invitationId}/accept`, {
    receiver_id: receiverId,
  });
  return res.data;
};


export const createAndStartSSIAgent = async (
  envId: string,
) => {
  try {
    const response = await api.post(
      `/environments/${envId}/create_start_ssi_agent`
    );
    return response.data;
  } catch (error) {
    throw error;
  }
};

export const ssiExpansion = async (
  envId: string,
  bindings: Array<{
    membership_id: string;
    url: string;
    public_did: string;
  }>
) => {
  const res = await api.post(`/environments/${envId}/ssi_expansion/`, {
    ssi_bindings: bindings,
  });
  return res.data;
};