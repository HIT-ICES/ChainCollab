const BASE_URL = import.meta.env.VITE_AGENT_BASE_URL || "http://127.0.0.1:5001";

async function handleResponse(res) {
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || res.statusText);
  }
  return res.json();
}

export function fetchNetworks() {
  return handleResponse(fetch(`${BASE_URL}/api/v1/networks`));
}

export function createFabricNode(payload) {
  const form = new FormData();
  Object.entries(payload).forEach(([key, value]) => value !== undefined && form.append(key, value));
  return handleResponse(
    fetch(`${BASE_URL}/api/v1/nodes`, {
      method: "POST",
      body: form,
    })
  );
}

export function createCa(payload) {
  const form = new FormData();
  Object.entries(payload).forEach(([key, value]) => value !== undefined && form.append(key, value));
  return handleResponse(
    fetch(`${BASE_URL}/api/v1/ca`, {
      method: "POST",
      body: form,
    })
  );
}

export function createEthNode(payload) {
  const form = new FormData();
  Object.entries(payload).forEach(([key, value]) => value !== undefined && form.append(key, value));
  return handleResponse(
    fetch(`${BASE_URL}/api/v1/ethnode`, {
      method: "POST",
      body: form,
    })
  );
}
