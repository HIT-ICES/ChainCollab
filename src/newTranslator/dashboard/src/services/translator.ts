import axios from 'axios';
import { API_BASE, ROUTES } from '../config';

export interface ChaincodeOutput {
  bpmnContent: string;
  ffiContent: string;
  timecost?: string;
}

export interface ParticipantsResponse {
  [id: string]: string;
}

export interface MessageResponseItem {
  name?: string;
  documentation?: string;
}

export interface MessagesResponse {
  [id: string]: MessageResponseItem;
}

export interface BusinessRuleResponseItem {
  name?: string;
  documentation?: string;
}

export interface BusinessRuleResponse {
  [id: string]: BusinessRuleResponseItem;
}

export interface DecisionDetail {
  id: string;
  name?: string;
  is_main?: boolean;
  inputs: {
    id: string;
    label?: string;
    expression_id?: string;
    typeRef?: string;
    text?: string;
  }[];
  outputs: {
    id: string;
    name?: string;
    label?: string;
    type?: string;
  }[];
}

const client = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const translatorService = {
  async generateChaincode(bpmnContent: string): Promise<ChaincodeOutput> {
    const { data } = await client.post<ChaincodeOutput>(ROUTES.generate, { bpmnContent });
    return data;
  },

  async getParticipants(bpmnContent: string): Promise<ParticipantsResponse> {
    const { data } = await client.post<ParticipantsResponse>(ROUTES.participants, { bpmnContent });
    return data;
  },

  async getMessages(bpmnContent: string): Promise<MessagesResponse> {
    const { data } = await client.post<MessagesResponse>(ROUTES.messages, { bpmnContent });
    return data;
  },

  async getBusinessRules(bpmnContent: string): Promise<BusinessRuleResponse> {
    const { data } = await client.post<BusinessRuleResponse>(ROUTES.businessRules, { bpmnContent });
    return data;
  },

  async getDecisions(dmnContent: string): Promise<DecisionDetail[]> {
    const { data } = await client.post<DecisionDetail[]>(ROUTES.decisions, { dmnContent });
    return data;
  },
};
