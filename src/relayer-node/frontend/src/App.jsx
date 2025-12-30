import React, { useEffect, useMemo, useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE || "";

const sections = [
  { id: "overview", label: "Overview" },
  { id: "identities", label: "Identities" },
  { id: "routes", label: "Relay Routes" },
  { id: "logs", label: "Logs" }
];

const initialIdentity = {
  name: "",
  chain_type: "evm",
  rpc_url: "",
  private_key: "",
  address: "",
  notes: "",
  metadata: {
    gateway_url: "",
    channel_name: "",
    chaincode_name: "",
    msp_id: "",
    cert_path: "",
    key_path: ""
  }
};

const initialRoute = {
  name: "",
  enabled: true,
  source_chain_type: "evm",
  source_identity_id: "",
  source_adapter: "",
  source_chain_id: "",
  source_start_block: "",
  poll_interval: 5,
  dest_chain_type: "evm",
  dest_identity_id: "",
  dest_adapter: "",
  dest_chain_id: "",
  metadata: {
    source_event_name: "XCallRequested",
    relay_signers: [],
    result_callback: {
      target: "",
      method: "onXCallResult(bytes32,bool,bytes)"
    }
  }
};

export default function App() {
  const [active, setActive] = useState("overview");
  const [notice, setNotice] = useState(null);
  const [identities, setIdentities] = useState([]);
  const [routes, setRoutes] = useState([]);
  const [logs, setLogs] = useState([]);
  const [identityForm, setIdentityForm] = useState(initialIdentity);
  const [routeForm, setRouteForm] = useState(initialRoute);
  const [selectedRoute, setSelectedRoute] = useState("");
  const [logFilter, setLogFilter] = useState("");

  useEffect(() => {
    refreshAll();
  }, []);

  async function refreshAll() {
    await Promise.all([loadIdentities(), loadRoutes()]);
    await loadLogs("");
  }

  async function loadIdentities() {
    const res = await fetch(`${API_BASE}/identities`);
    const data = await res.json();
    setIdentities(data);
    if (!identityForm.address && data.length > 0) {
      setIdentityForm((prev) => ({ ...prev, address: data[0].address || "" }));
    }
    if (!routeForm.source_identity_id && data.length > 0) {
      setRouteForm((prev) => ({
        ...prev,
        source_identity_id: data[0].id,
        dest_identity_id: data[0].id
      }));
    }
  }

  async function loadRoutes() {
    const res = await fetch(`${API_BASE}/routes`);
    const data = await res.json();
    setRoutes(data);
  }

  async function loadLogs(routeId) {
    const query = routeId ? `?route_id=${routeId}` : "";
    const res = await fetch(`${API_BASE}/logs${query}`);
    const data = await res.json();
    setLogs(data);
  }

  function showNotice(text, type = "success") {
    setNotice({ text, type });
    window.clearTimeout(showNotice._t);
    showNotice._t = window.setTimeout(() => setNotice(null), 2600);
  }

  async function submitIdentity(e) {
    e.preventDefault();
    const payload = {
      name: identityForm.name,
      chain_type: identityForm.chain_type,
      rpc_url: identityForm.chain_type === "evm" ? identityForm.rpc_url : null,
      private_key: identityForm.chain_type === "evm" ? identityForm.private_key : null,
      address: identityForm.address,
      notes: identityForm.notes,
      metadata: identityForm.chain_type === "fabric" ? identityForm.metadata : {}
    };
    const res = await fetch(`${API_BASE}/identities`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      showNotice("Failed to save identity.", "error");
      return;
    }
    setIdentityForm(initialIdentity);
    await loadIdentities();
    showNotice("Identity saved.");
  }

  async function deleteIdentity(id) {
    if (!window.confirm("Delete identity?")) {
      return;
    }
    const res = await fetch(`${API_BASE}/identities/${id}`, { method: "DELETE" });
    if (!res.ok) {
      showNotice("Delete failed.", "error");
      return;
    }
    await loadIdentities();
    showNotice("Identity deleted.");
  }

  async function submitRoute(e) {
    e.preventDefault();
    const payload = {
      name: routeForm.name,
      enabled: routeForm.enabled,
      source_chain_type: routeForm.source_chain_type,
      source_identity_id: routeForm.source_identity_id,
      source_adapter: routeForm.source_adapter,
      source_chain_id: routeForm.source_chain_id ? Number(routeForm.source_chain_id) : null,
      source_start_block: routeForm.source_start_block
        ? Number(routeForm.source_start_block)
        : null,
      poll_interval: Number(routeForm.poll_interval || 5),
      dest_chain_type: routeForm.dest_chain_type,
      dest_identity_id: routeForm.dest_identity_id,
      dest_adapter: routeForm.dest_adapter,
      dest_chain_id: routeForm.dest_chain_id ? Number(routeForm.dest_chain_id) : null,
      metadata: routeForm.metadata
    };
    const res = await fetch(`${API_BASE}/routes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      showNotice("Failed to save route.", "error");
      return;
    }
    setRouteForm(initialRoute);
    await loadRoutes();
    showNotice("Route saved.");
  }

  async function deleteRoute(id) {
    if (!window.confirm("Delete route?")) {
      return;
    }
    const res = await fetch(`${API_BASE}/routes/${id}`, { method: "DELETE" });
    if (!res.ok) {
      showNotice("Delete failed.", "error");
      return;
    }
    await loadRoutes();
    showNotice("Route deleted.");
  }

  async function reloadLogs(routeId) {
    setLogFilter(routeId);
    await loadLogs(routeId);
  }

  const stats = useMemo(
    () => ({
      identities: identities.length,
      routes: routes.length,
      logs: logs.length
    }),
    [identities, routes, logs]
  );

  return (
    <div className="app-shell">
      <aside className="side-nav">
        <div className="brand">
          <div className="brand-mark">RX</div>
          <div>
            <div className="brand-title">Relayer</div>
            <div className="brand-sub">Control Plane</div>
          </div>
        </div>
        <nav>
          {sections.map((item) => (
            <button
              key={item.id}
              className={active === item.id ? "nav-btn active" : "nav-btn"}
              onClick={() => setActive(item.id)}
            >
              {item.label}
            </button>
          ))}
        </nav>
        <div className="side-footer">
          <div className="muted">API</div>
          <div className="mono">{API_BASE || "same-origin"}</div>
        </div>
      </aside>

      <main className="main">
        {notice && (
          <div className={`notice ${notice.type}`}>
            {notice.text}
            <button onClick={() => setNotice(null)}>x</button>
          </div>
        )}

        {active === "overview" && (
          <section>
            <h1>Relay Overview</h1>
            <p className="lead">
              Configure identities, define relay routes, and monitor cross-chain call delivery.
            </p>
            <div className="stats-grid">
              <div className="stat-card">
                <div className="stat-label">Identities</div>
                <div className="stat-value">{stats.identities}</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">Routes</div>
                <div className="stat-value">{stats.routes}</div>
              </div>
              <div className="stat-card">
                <div className="stat-label">Logs (latest)</div>
                <div className="stat-value">{stats.logs}</div>
              </div>
            </div>
            <div className="panel-grid">
              <div className="panel">
                <h3>Quick Notes</h3>
                <ul>
                  <li>Source adapters emit XCallRequested events.</li>
                  <li>Relayer collects signatures and forwards to destination.</li>
                  <li>Result callback is optional via metadata.</li>
                </ul>
              </div>
              <div className="panel">
                <h3>Next Steps</h3>
                <ul>
                  <li>Register chain identities first.</li>
                  <li>Create a route and keep it enabled.</li>
                  <li>Watch logs to verify delivery.</li>
                </ul>
              </div>
            </div>
          </section>
        )}

        {active === "identities" && (
          <section>
            <h1>Identities</h1>
            <div className="grid-two">
              <div className="card">
                <h3>Register Identity</h3>
                <form onSubmit={submitIdentity} className="form">
                  <label>Name</label>
                  <input
                    value={identityForm.name}
                    onChange={(e) => setIdentityForm({ ...identityForm, name: e.target.value })}
                    required
                  />
                  <label>Chain Type</label>
                  <select
                    value={identityForm.chain_type}
                    onChange={(e) =>
                      setIdentityForm({ ...identityForm, chain_type: e.target.value })
                    }
                  >
                    <option value="evm">EVM</option>
                    <option value="fabric">Fabric</option>
                  </select>

                  {identityForm.chain_type === "evm" && (
                    <>
                      <label>RPC URL</label>
                      <input
                        value={identityForm.rpc_url}
                        onChange={(e) =>
                          setIdentityForm({ ...identityForm, rpc_url: e.target.value })
                        }
                      />
                      <label>Private Key</label>
                      <input
                        value={identityForm.private_key}
                        onChange={(e) =>
                          setIdentityForm({ ...identityForm, private_key: e.target.value })
                        }
                      />
                    </>
                  )}

                  {identityForm.chain_type === "fabric" && (
                    <div className="form-grid">
                      <div>
                        <label>Gateway URL</label>
                        <input
                          value={identityForm.metadata.gateway_url}
                          onChange={(e) =>
                            setIdentityForm({
                              ...identityForm,
                              metadata: { ...identityForm.metadata, gateway_url: e.target.value }
                            })
                          }
                        />
                      </div>
                      <div>
                        <label>Channel Name</label>
                        <input
                          value={identityForm.metadata.channel_name}
                          onChange={(e) =>
                            setIdentityForm({
                              ...identityForm,
                              metadata: { ...identityForm.metadata, channel_name: e.target.value }
                            })
                          }
                        />
                      </div>
                      <div>
                        <label>Chaincode Name</label>
                        <input
                          value={identityForm.metadata.chaincode_name}
                          onChange={(e) =>
                            setIdentityForm({
                              ...identityForm,
                              metadata: { ...identityForm.metadata, chaincode_name: e.target.value }
                            })
                          }
                        />
                      </div>
                      <div>
                        <label>MSP ID</label>
                        <input
                          value={identityForm.metadata.msp_id}
                          onChange={(e) =>
                            setIdentityForm({
                              ...identityForm,
                              metadata: { ...identityForm.metadata, msp_id: e.target.value }
                            })
                          }
                        />
                      </div>
                      <div>
                        <label>Cert Path</label>
                        <input
                          value={identityForm.metadata.cert_path}
                          onChange={(e) =>
                            setIdentityForm({
                              ...identityForm,
                              metadata: { ...identityForm.metadata, cert_path: e.target.value }
                            })
                          }
                        />
                      </div>
                      <div>
                        <label>Key Path</label>
                        <input
                          value={identityForm.metadata.key_path}
                          onChange={(e) =>
                            setIdentityForm({
                              ...identityForm,
                              metadata: { ...identityForm.metadata, key_path: e.target.value }
                            })
                          }
                        />
                      </div>
                    </div>
                  )}

                  <label>Address</label>
                  <input
                    value={identityForm.address}
                    onChange={(e) =>
                      setIdentityForm({ ...identityForm, address: e.target.value })
                    }
                  />
                  <label>Notes</label>
                  <textarea
                    rows="3"
                    value={identityForm.notes}
                    onChange={(e) =>
                      setIdentityForm({ ...identityForm, notes: e.target.value })
                    }
                  />
                  <button type="submit">Save Identity</button>
                </form>
              </div>
              <div className="card">
                <h3>Registered</h3>
                <div className="list">
                  {identities.map((item) => (
                    <div className="list-item" key={item.id}>
                      <div>
                        <div className="list-title">{item.name}</div>
                        <div className="muted">{item.chain_type}</div>
                        <div className="mono">{item.rpc_url || item.metadata?.gateway_url}</div>
                      </div>
                      <button className="ghost" onClick={() => deleteIdentity(item.id)}>
                        Delete
                      </button>
                    </div>
                  ))}
                  {identities.length === 0 && (
                    <div className="empty">No identities registered.</div>
                  )}
                </div>
              </div>
            </div>
          </section>
        )}

        {active === "routes" && (
          <section>
            <h1>Relay Routes</h1>
            <div className="grid-two">
              <div className="card">
                <h3>Create Route</h3>
                <form onSubmit={submitRoute} className="form">
                  <label>Name</label>
                  <input
                    value={routeForm.name}
                    onChange={(e) => setRouteForm({ ...routeForm, name: e.target.value })}
                    required
                  />
                  <label>Enabled</label>
                  <select
                    value={routeForm.enabled ? "yes" : "no"}
                    onChange={(e) =>
                      setRouteForm({ ...routeForm, enabled: e.target.value === "yes" })
                    }
                  >
                    <option value="yes">Yes</option>
                    <option value="no">No</option>
                  </select>

                  <div className="form-grid">
                    <div>
                      <label>Source Chain</label>
                      <select
                        value={routeForm.source_chain_type}
                        onChange={(e) =>
                          setRouteForm({ ...routeForm, source_chain_type: e.target.value })
                        }
                      >
                        <option value="evm">EVM</option>
                        <option value="fabric">Fabric</option>
                      </select>
                    </div>
                    <div>
                      <label>Source Identity</label>
                      <select
                        value={routeForm.source_identity_id}
                        onChange={(e) =>
                          setRouteForm({ ...routeForm, source_identity_id: e.target.value })
                        }
                      >
                        {identities.map((item) => (
                          <option key={item.id} value={item.id}>
                            {item.name}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                  <label>Source Adapter</label>
                  <input
                    value={routeForm.source_adapter}
                    onChange={(e) =>
                      setRouteForm({ ...routeForm, source_adapter: e.target.value })
                    }
                  />
                  <div className="form-grid">
                    <div>
                      <label>Source Chain ID</label>
                      <input
                        value={routeForm.source_chain_id}
                        onChange={(e) =>
                          setRouteForm({ ...routeForm, source_chain_id: e.target.value })
                        }
                      />
                    </div>
                    <div>
                      <label>Start Block</label>
                      <input
                        value={routeForm.source_start_block}
                        onChange={(e) =>
                          setRouteForm({ ...routeForm, source_start_block: e.target.value })
                        }
                      />
                    </div>
                  </div>
                  <label>Poll Interval (sec)</label>
                  <input
                    value={routeForm.poll_interval}
                    onChange={(e) =>
                      setRouteForm({ ...routeForm, poll_interval: e.target.value })
                    }
                  />
                  <label>Source Event Name</label>
                  <input
                    value={routeForm.metadata.source_event_name}
                    onChange={(e) =>
                      setRouteForm({
                        ...routeForm,
                        metadata: {
                          ...routeForm.metadata,
                          source_event_name: e.target.value
                        }
                      })
                    }
                  />

                  <div className="form-grid">
                    <div>
                      <label>Destination Chain</label>
                      <select
                        value={routeForm.dest_chain_type}
                        onChange={(e) =>
                          setRouteForm({ ...routeForm, dest_chain_type: e.target.value })
                        }
                      >
                        <option value="evm">EVM</option>
                        <option value="fabric">Fabric</option>
                      </select>
                    </div>
                    <div>
                      <label>Destination Identity</label>
                      <select
                        value={routeForm.dest_identity_id}
                        onChange={(e) =>
                          setRouteForm({ ...routeForm, dest_identity_id: e.target.value })
                        }
                      >
                        {identities.map((item) => (
                          <option key={item.id} value={item.id}>
                            {item.name}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>
                  <label>Destination Adapter</label>
                  <input
                    value={routeForm.dest_adapter}
                    onChange={(e) =>
                      setRouteForm({ ...routeForm, dest_adapter: e.target.value })
                    }
                  />
                  <label>Destination Chain ID</label>
                  <input
                    value={routeForm.dest_chain_id}
                    onChange={(e) =>
                      setRouteForm({ ...routeForm, dest_chain_id: e.target.value })
                    }
                  />

                  <label>Relay Signers (comma)</label>
                  <input
                    value={routeForm.metadata.relay_signers.join(",")}
                    onChange={(e) =>
                      setRouteForm({
                        ...routeForm,
                        metadata: {
                          ...routeForm.metadata,
                          relay_signers: e.target.value
                            .split(",")
                            .map((item) => item.trim())
                            .filter(Boolean)
                        }
                      })
                    }
                  />
                  <label>Result Callback Target</label>
                  <input
                    value={routeForm.metadata.result_callback.target}
                    onChange={(e) =>
                      setRouteForm({
                        ...routeForm,
                        metadata: {
                          ...routeForm.metadata,
                          result_callback: {
                            ...routeForm.metadata.result_callback,
                            target: e.target.value
                          }
                        }
                      })
                    }
                  />
                  <label>Result Callback Method</label>
                  <input
                    value={routeForm.metadata.result_callback.method}
                    onChange={(e) =>
                      setRouteForm({
                        ...routeForm,
                        metadata: {
                          ...routeForm.metadata,
                          result_callback: {
                            ...routeForm.metadata.result_callback,
                            method: e.target.value
                          }
                        }
                      })
                    }
                  />
                  <button type="submit">Save Route</button>
                </form>
              </div>
              <div className="card">
                <h3>Configured Routes</h3>
                <div className="list">
                  {routes.map((route) => (
                    <div className="list-item" key={route.id}>
                      <div>
                        <div className="list-title">{route.name}</div>
                        <div className="muted">
                          {route.source_chain_type} -> {route.dest_chain_type}
                        </div>
                        <div className="mono">{route.source_adapter}</div>
                      </div>
                      <div className="actions">
                        <button
                          className="ghost"
                          onClick={() => reloadLogs(route.id)}
                        >
                          Logs
                        </button>
                        <button className="ghost" onClick={() => deleteRoute(route.id)}>
                          Delete
                        </button>
                      </div>
                    </div>
                  ))}
                  {routes.length === 0 && <div className="empty">No routes yet.</div>}
                </div>
              </div>
            </div>
          </section>
        )}

        {active === "logs" && (
          <section>
            <h1>Relay Logs</h1>
            <div className="card">
              <div className="toolbar">
                <select
                  value={logFilter}
                  onChange={(e) => reloadLogs(e.target.value)}
                >
                  <option value="">All Routes</option>
                  {routes.map((route) => (
                    <option key={route.id} value={route.id}>
                      {route.name}
                    </option>
                  ))}
                </select>
                <button onClick={() => reloadLogs(logFilter)}>Refresh</button>
              </div>
              <div className="log-list">
                {logs.map((log) => (
                  <div className="log-row" key={log.id}>
                    <div>
                      <div className="log-title">{log.message_id}</div>
                      <div className="muted">
                        {log.direction} · {log.status}
                      </div>
                    </div>
                    <div className="mono">{new Date(log.created_at * 1000).toLocaleString()}</div>
                  </div>
                ))}
                {logs.length === 0 && <div className="empty">No logs yet.</div>}
              </div>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}
