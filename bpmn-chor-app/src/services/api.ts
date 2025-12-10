type FetchLike = typeof fetch;

export interface ChorApiConfig {
  apiBaseUrl: string;
  translatorBaseUrl: string;
  authToken?: string;
  authScheme?: string;
  headers?: Record<string, string>;
  fetchImpl?: FetchLike;
}

export interface AddBpmnPayload {
  consortiumId: string;
  orgId: string;
  name: string;
  bpmnContent: string;
  svgContent: string;
  participants: unknown;
}

export interface AddDmnPayload {
  consortiumId: string;
  orgId: string;
  name: string;
  dmnContent: string;
  svgContent: string;
}

export interface ChorApiClient {
  addBpmn: (payload: AddBpmnPayload) => Promise<unknown>;
  addDmn: (payload: AddDmnPayload) => Promise<unknown>;
  getParticipantsByContent: (bpmnContent: string) => Promise<unknown>;
}

const normalizeBaseUrl = (url: string) => url.replace(/\/+$/, '');

const parseJsonResponse = async (response: Response) => {
  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    return response.json();
  }
  return response.text();
};

export const createDefaultChorApiClient = (config: ChorApiConfig): ChorApiClient => {
  const fetcher: FetchLike | undefined = config.fetchImpl ?? (typeof fetch !== 'undefined' ? fetch : undefined);
  if (!fetcher) {
    throw new Error('No fetch implementation available. Provide fetchImpl in ChorModeler props.');
  }

  const apiBase = normalizeBaseUrl(config.apiBaseUrl);
  const translatorBase = normalizeBaseUrl(config.translatorBaseUrl);
  const baseHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(config.headers ?? {})
  };

  const authHeader = (): Record<string, string> => {
    if (!config.authToken) {
      return {};
    }
    return {
      Authorization: `${config.authScheme ?? 'JWT'} ${config.authToken}`
    };
  };

  const request = async <T>(url: string, init: RequestInit): Promise<T> => {
    const response = await fetcher(url, init);
    if (!response.ok) {
      const message = await response.text();
      throw new Error(`Request failed (${response.status}): ${message}`);
    }
    return parseJsonResponse(response) as Promise<T>;
  };

  const addBpmn = async (payload: AddBpmnPayload) => {
    return request(`${apiBase}/consortiums/${payload.consortiumId}/bpmns/_upload`, {
      method: 'POST',
      headers: {
        ...baseHeaders,
        ...authHeader()
      },
      body: JSON.stringify({
        consortiumid: payload.consortiumId,
        orgid: payload.orgId,
        name: payload.name,
        bpmnContent: payload.bpmnContent,
        svgContent: payload.svgContent,
        participants: payload.participants
      })
    });
  };

  const addDmn = async (payload: AddDmnPayload) => {
    return request(`${apiBase}/consortiums/${payload.consortiumId}/dmns`, {
      method: 'POST',
      headers: {
        ...baseHeaders,
        ...authHeader()
      },
      body: JSON.stringify({
        consortiumid: payload.consortiumId,
        orgid: payload.orgId,
        name: payload.name,
        dmnContent: payload.dmnContent,
        svgContent: payload.svgContent
      })
    });
  };

  const getParticipantsByContent = async (bpmnContent: string) => {
    return request(`${translatorBase}/chaincode/getPartByBpmnC`, {
      method: 'POST',
      headers: {
        ...baseHeaders,
        ...authHeader()
      },
      body: JSON.stringify({
        bpmnContent
      })
    });
  };

  return {
    addBpmn,
    addDmn,
    getParticipantsByContent
  };
};
