import { useEffect, useMemo, useState } from "react";
import {
  createCa,
  createEthNode,
  createFabricNode,
  fetchNetworks,
} from "./api";
import "./App.css";

const defaultFabric = {
  node_type: "fabric-peer",
  name: "",
  img: "hyperledger/fabric-peer:2.2",
  cmd: "peer node start",
  port_map: '{"7051/tcp": 7051, "7052/tcp": 7052}',
};

const defaultEth = {
  name: "",
  port_map: '{"8545": 18545, "30303": 30303}',
};

const defaultCa = {
  ca_name: "",
  port_map: '{"7054": 17054, "17054": 27054}',
};

const quickActions = [
  {
    id: "fabric-peer",
    label: "Fabric Peer",
    description: "Hyperledger Fabric peer node",
    icon: "hub",
  },
  {
    id: "fabric-orderer",
    label: "Fabric Orderer",
    description: "Ordering service node",
    icon: "device_hub",
  },
  {
    id: "ethereum",
    label: "Ethereum",
    description: "Geth validator instance",
    icon: "hexagon",
  },
  {
    id: "fabric-ca",
    label: "Fabric CA",
    description: "Certificate authority",
    icon: "verified_user",
  },
];

function App() {
  const [networks, setNetworks] = useState([]);
  const [loading, setLoading] = useState(false);
  const [fabricForm, setFabricForm] = useState(defaultFabric);
  const [ethForm, setEthForm] = useState(defaultEth);
  const [caForm, setCaForm] = useState(defaultCa);
  const [status, setStatus] = useState({ type: "", text: "" });

  const fetchData = async () => {
    try {
      setLoading(true);
      const res = await fetchNetworks();
      setNetworks(Object.values(res.res?.data || {}));
    } catch (err) {
      setStatus({ type: "error", text: err.message });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleFabricSubmit = async (e) => {
    e.preventDefault();
    try {
      setStatus({ type: "info", text: "Launching Fabric node..." });
      await createFabricNode(fabricForm);
      setStatus({ type: "success", text: "Fabric node created." });
      setFabricForm(defaultFabric);
      fetchData();
    } catch (err) {
      setStatus({ type: "error", text: err.message });
    }
  };

  const handleEthSubmit = async (e) => {
    e.preventDefault();
    try {
      setStatus({ type: "info", text: "Launching Ethereum node..." });
      await createEthNode(ethForm);
      setStatus({ type: "success", text: "Ethereum node created." });
      setEthForm(defaultEth);
      fetchData();
    } catch (err) {
      setStatus({ type: "error", text: err.message });
    }
  };

  const handleCaSubmit = async (e) => {
    e.preventDefault();
    try {
      setStatus({ type: "info", text: "Launching Fabric CA..." });
      await createCa(caForm);
      setStatus({ type: "success", text: "Fabric CA created." });
      setCaForm(defaultCa);
      fetchData();
    } catch (err) {
      setStatus({ type: "error", text: err.message });
    }
  };

  const quickLaunch = async (action) => {
    const suggested = `${action.id.replace(/[^a-z]/gi, "-")}-${
      Date.now().toString().slice(-4)
    }`;
    const name = window.prompt(`Name for ${action.label}`, suggested);
    if (!name) return;
    try {
      setStatus({ type: "info", text: `Launching ${action.label}...` });
      if (action.id === "fabric-peer" || action.id === "fabric-orderer") {
        await createFabricNode({
          ...defaultFabric,
          node_type: action.id,
          name,
        });
      } else if (action.id === "ethereum") {
        await createEthNode({ ...defaultEth, name });
      } else if (action.id === "fabric-ca") {
        await createCa({ ...defaultCa, ca_name: name });
      }
      setStatus({ type: "success", text: `${action.label} launched.` });
      fetchData();
    } catch (err) {
      setStatus({ type: "error", text: err.message });
    }
  };

  const fabricCount = useMemo(
    () =>
      networks.filter((n) =>
        String(n.image || "").toLowerCase().includes("hyperledger/fabric")
      ).length,
    [networks]
  );

  const ethCount = useMemo(
    () =>
      networks.filter((n) =>
        String(n.image || "").toLowerCase().includes("ethereum")
      ).length,
    [networks]
  );

  const showDocs = () =>
    setStatus({
      type: "info",
      text: "Refer to README for API usage and deployment instructions.",
    });

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar__brand">
          <span className="material-symbols-rounded">blur_on</span>
          MultiChain Agent
        </div>
        <nav className="sidebar__nav">
          <button onClick={() => document.getElementById("overview")?.scrollIntoView({ behavior: "smooth" })}>
            <span className="material-symbols-rounded">dashboard</span>
            Fleet Overview
          </button>
          <button onClick={() => document.getElementById("quick-actions")?.scrollIntoView({ behavior: "smooth" })}>
            <span className="material-symbols-rounded">bolt</span>
            Quick Actions
          </button>
          <button onClick={() => document.getElementById("forms")?.scrollIntoView({ behavior: "smooth" })}>
            <span className="material-symbols-rounded">tune</span>
            Advanced Forms
          </button>
        </nav>
        <footer className="sidebar__footer">
          <p>Connected workspace</p>
          <strong>developer@local</strong>
        </footer>
      </aside>

      <div className="main">
        <header className="topbar">
          <div>
            <p className="muted">Infrastructure / Agent</p>
            <h1>Resource Control Room</h1>
          </div>
          <div className="topbar__actions">
            <button className="ghost" onClick={showDocs}>
              <span className="material-symbols-rounded">help</span>
              Docs
            </button>
            <button className="primary" onClick={fetchData} disabled={loading}>
              <span className="material-symbols-rounded">refresh</span>
              {loading ? "Refreshing..." : "Refresh"}
            </button>
          </div>
        </header>

        <main className="content">
          <Message type={status.type} message={status.text} />

          <OverviewCard
            id="overview"
            networks={networks}
            fabricCount={fabricCount}
            ethCount={ethCount}
          />

          <QuickActionsCard
            id="quick-actions"
            actions={quickActions}
            onQuickLaunch={quickLaunch}
          />

          <AdvancedForms
            id="forms"
            fabricForm={fabricForm}
            setFabricForm={setFabricForm}
            ethForm={ethForm}
            setEthForm={setEthForm}
            caForm={caForm}
            setCaForm={setCaForm}
            onFabricSubmit={handleFabricSubmit}
            onEthSubmit={handleEthSubmit}
            onCaSubmit={handleCaSubmit}
          />
        </main>
      </div>
    </div>
  );
}

function OverviewCard({ id, networks, fabricCount, ethCount }) {
  return (
    <section className="card" id={id}>
      <header className="card__header">
        <div>
          <h3>Fleet Overview</h3>
          <p>Live containers across Fabric, Ethereum and auxiliary services.</p>
        </div>
        <span className="pill success">Live</span>
      </header>
      <div className="stats-grid wide">
        <article>
          <p>Total containers</p>
          <strong>{networks.length}</strong>
          <small>running across the agent</small>
        </article>
        <article>
          <p>Fabric nodes</p>
          <strong>{fabricCount}</strong>
          <small>peer + orderer roles</small>
        </article>
        <article>
          <p>Ethereum nodes</p>
          <strong>{ethCount}</strong>
          <small>geth validators</small>
        </article>
      </div>
      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Image</th>
              <th>Status</th>
              <th>Ports</th>
            </tr>
          </thead>
          <tbody>
            {networks.length === 0 && (
              <tr>
                <td colSpan={4}>No containers detected.</td>
              </tr>
            )}
            {networks.map((c) => (
              <tr key={c.id}>
                <td>{c.name}</td>
                <td>{c.image}</td>
                <td>
                  <span className={`pill ${c.status}`}>{c.status}</span>
                </td>
                <td>
                  {Object.entries(c.attrs?.NetworkSettings?.Ports || {}).map(
                    ([port, binding]) => (
                      <div key={port}>
                        {port} → {binding?.[0]?.HostPort || "-"}
                      </div>
                    )
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function QuickActionsCard({ id, actions, onQuickLaunch }) {
  return (
    <section className="card" id={id}>
      <header className="card__header">
        <div>
          <h3>Quick Actions</h3>
          <p>Provision common container types with sensible defaults.</p>
        </div>
      </header>
      <div className="quick-actions">
        {actions.map((action) => (
          <button
            key={action.id}
            className="quick-action"
            onClick={() => onQuickLaunch(action)}
          >
            <span className="material-symbols-rounded">{action.icon}</span>
            <div>
              <strong>{action.label}</strong>
              <p>{action.description}</p>
            </div>
          </button>
        ))}
      </div>
    </section>
  );
}

function Field({ label, hint, textarea, ...props }) {
  return (
    <label className="field">
      <span>{label}</span>
      {textarea ? <textarea {...props} /> : <input {...props} />}
      {hint && <small>{hint}</small>}
    </label>
  );
}

function AdvancedForms({
  id,
  fabricForm,
  setFabricForm,
  ethForm,
  setEthForm,
  caForm,
  setCaForm,
  onFabricSubmit,
  onEthSubmit,
  onCaSubmit,
}) {
  return (
    <section className="card" id={id}>
      <header className="card__header">
        <div>
          <h3>Advanced Provisioning</h3>
          <p>Customize parameters for Fabric, Ethereum and CA nodes.</p>
        </div>
      </header>
      <div className="forms-grid">
        <form onSubmit={onFabricSubmit}>
          <h4>Fabric Node</h4>
          <label className="field">
            <span>Node Type</span>
            <select
              value={fabricForm.node_type}
              onChange={(e) =>
                setFabricForm((prev) => ({
                  ...prev,
                  node_type: e.target.value,
                }))
              }
            >
              <option value="fabric-peer">Fabric Peer</option>
              <option value="fabric-orderer">Fabric Orderer</option>
            </select>
          </label>
          <Field
            label="Name"
            value={fabricForm.name}
            onChange={(e) =>
              setFabricForm((prev) => ({ ...prev, name: e.target.value }))
            }
            required
          />
          <Field
            label="Image"
            value={fabricForm.img}
            onChange={(e) =>
              setFabricForm((prev) => ({ ...prev, img: e.target.value }))
            }
          />
          <Field
            label="Command"
            value={fabricForm.cmd}
            onChange={(e) =>
              setFabricForm((prev) => ({ ...prev, cmd: e.target.value }))
            }
          />
          <Field
            label="Port Map (JSON)"
            textarea
            value={fabricForm.port_map}
            onChange={(e) =>
              setFabricForm((prev) => ({ ...prev, port_map: e.target.value }))
            }
            hint='e.g. {"7051/tcp":7051}'
          />
          <button type="submit" className="primary">
            Launch Fabric Node
          </button>
        </form>

        <form onSubmit={onEthSubmit}>
          <h4>Ethereum Node</h4>
          <Field
            label="Name"
            value={ethForm.name}
            onChange={(e) =>
              setEthForm((prev) => ({ ...prev, name: e.target.value }))
            }
            required
          />
          <Field
            label="Port Map (JSON)"
            textarea
            value={ethForm.port_map}
            onChange={(e) =>
              setEthForm((prev) => ({ ...prev, port_map: e.target.value }))
            }
          />
          <button type="submit" className="primary">
            Launch Ethereum Node
          </button>
        </form>

        <form onSubmit={onCaSubmit}>
          <h4>Fabric CA</h4>
          <Field
            label="CA Name"
            value={caForm.ca_name}
            onChange={(e) =>
              setCaForm((prev) => ({ ...prev, ca_name: e.target.value }))
            }
            required
          />
          <Field
            label="Port Map (JSON)"
            textarea
            value={caForm.port_map}
            onChange={(e) =>
              setCaForm((prev) => ({ ...prev, port_map: e.target.value }))
            }
          />
          <button type="submit" className="primary">
            Launch CA
          </button>
        </form>
      </div>
    </section>
  );
}

function Message({ message, type = "info" }) {
  if (!message) return null;
  return <div className={`message ${type}`}>{message}</div>;
}

export default App;
