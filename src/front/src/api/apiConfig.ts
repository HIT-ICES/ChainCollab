import axios from "axios";
import { localStorageGetItem } from "@/utils/localStorage";

const defaultBackendUrl =
  import.meta.env.MODE === "local_mode" ? "http://127.0.0.1:8000" : "http://192.168.1.177:8000";
const defaultTranslatorUrl =
  import.meta.env.MODE === "local_mode" ? "http://127.0.0.1:9999" : "http://192.168.1.177:9999";
const defaultHostBase =
  import.meta.env.MODE === "local_mode" ? "http://127.0.0.1" : "http://192.168.1.177";

const backendUrl = import.meta.env.VITE_BACKEND_URL || defaultBackendUrl;
const translatorUrl = import.meta.env.VITE_TRANSLATOR_URL || defaultTranslatorUrl;
export const current_ip = import.meta.env.VITE_HOST_BASE_URL || defaultHostBase;
export const backendBaseUrl = backendUrl;
export const translatorBaseUrl = translatorUrl;
export const translatorAPI = axios.create({
  baseURL: `${translatorUrl}/api/v1`,
  headers: {
    "Content-Type": "application/json",
  },
});
export const fireflyAPI = axios.create({
  baseURL: ``,
  headers: {
    "Content-Type": "application/json",
  },
});

const api = axios.create({
  // baseURL: "https://ae702a09-b9ea-40d0-858c-2f6bb82702d8.mock.pstmn.io/api/v1",
  baseURL: `${backendUrl}/api/v1`,
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use(
  (config) => {
    //pre request logic
    // exclude auth endpoints only (do not exclude arbitrary URLs containing "register")
    const rawUrl = String(config.url || "");
    const normalizedUrl = rawUrl.startsWith("http")
      ? new URL(rawUrl).pathname
      : rawUrl;
    const isAuthEndpoint =
      /^\/register(?:\/|$)/.test(normalizedUrl) ||
      /^\/login(?:\/|$)/.test(normalizedUrl) ||
      /^\/login\/refresh(?:\/|$)/.test(normalizedUrl) ||
      /^\/auth\/refresh(?:\/|$)/.test(normalizedUrl) ||
      /^\/token-verify(?:\/|$)/.test(normalizedUrl);

    if (isAuthEndpoint) {
      return config;
    }

    const token = localStorageGetItem("token");
    if (!token) {
      return Promise.reject(new axios.Cancel("Missing auth token"));
    }
    const cleanToken = String(token).trim();
    if (!cleanToken) {
      return Promise.reject(new axios.Cancel("Missing auth token"));
    }
    config.headers["Authorization"] = `JWT ${cleanToken}`;
    (config as any).__tokenSnapshot = cleanToken;
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

api.interceptors.response.use(
  (response) => {
    // pre response logic
    return response;
  },
  (error) => {
    if (error?.response?.status === 401) {
      const reqConfig: any = error?.config || {};
      const headerTokenRaw =
        reqConfig?.headers?.Authorization || reqConfig?.headers?.authorization || "";
      const headerToken = String(headerTokenRaw)
        .replace(/^JWT\s+/i, "")
        .replace(/^c\s+/i, "")
        .trim();
      const tokenSnapshot = String(reqConfig?.__tokenSnapshot || "").trim();

      const currentToken = String(localStorageGetItem("token") || "").trim();

      const usedToken = tokenSnapshot || headerToken;

      // Only clear token when this 401 comes from the same token currently in storage.
      // This prevents stale in-flight 401 responses from wiping a freshly logged-in token.
      if (usedToken && currentToken && usedToken === currentToken) {
        localStorage.removeItem("token");
      }
    }
    return Promise.reject(error);
  }
);

export default api;
