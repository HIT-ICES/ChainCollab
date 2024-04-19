import axios from "axios";

const api = axios.create({
  // baseURL: "https://ae702a09-b9ea-40d0-858c-2f6bb82702d8.mock.pstmn.io/api/v1",
  baseURL: "http://192.168.1.177:8000/api/v1",
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.request.use(
  (config) => {
    //pre request logic
    // exclude register and login
    if (
      config.url.includes("/register") ||
      config.url.includes("login") ||
      config.url.includes("/auth/refresh")
    ) {
      return config;
    }

    const token = localStorage.getItem("token");
    if (token) {
      const cleanToken = token.replace(/^"(.*)"$/, '\$1');
      config.headers["Authorization"] = `JWT ${cleanToken}`;
    }
    return config;
  },
  (error) => {
    // if not authorized or token expired
    console.log("HANDLE")
    console.log(error.response)

    if (error.response.status === 401) {
      localStorage.removeItem("token");
      window.location.href = "/login";
    }
    //else
  }
);

api.interceptors.response.use((response) => {
  // pre response logic
  return response;
});

export default api;
