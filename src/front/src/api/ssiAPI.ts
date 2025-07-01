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
