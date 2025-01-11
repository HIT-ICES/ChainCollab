import React, { useState } from "react";
import axios from "axios";

const StateMachineExecutor = () => {
  const [machineDescription, setMachineDescription] = useState("");
  const [serializedSnapshot, setSerializedSnapshot] = useState("");
  const [event, setEvent] = useState("");
  const [result, setResult] = useState(null);

  const handleSubmit = async () => {
    try {
      const payload = {
        machineDescription: JSON.parse(machineDescription),
        serializedSnapshot: serializedSnapshot, 
        event: event, 
      };

      const response = await axios.post(
        "http://172.29.240.229:3000/transition", 
        payload
      );

      setResult(response.data);
    } catch (error) {
      alert(`Error: ${error.message}`);
      setResult(null);
    }
  };

  return (
    <div>
      <label>
        <strong>State Machine Description (JSON):</strong>
      </label>
      <textarea
        value={machineDescription}
        onChange={(e) => setMachineDescription(e.target.value)}
        rows="6"
        cols="50"
      />

      <label>
        <strong>Serialized Snapshot (JSON):</strong>
      </label>
      <textarea
        value={serializedSnapshot}
        onChange={(e) => setSerializedSnapshot(e.target.value)}
        rows="6"
        cols="50"
      />

      <label>
        <strong>Event (String):</strong>
      </label>
      <textarea
        value={event}
        onChange={(e) => setEvent(e.target.value)}
        rows="6"
        cols="50"
      />

      <button onClick={handleSubmit}>Execute State Machine</button>

      {result && (
        <div
          style={{
            marginTop: "20px",
            padding: "10px",
            border: "1px solid #ddd",
            background: "#f9f9f9",
          }}
        >
          <h2>Result</h2>
          <p>
            <strong>Next Snapshot:</strong>
          </p>
          <pre>{JSON.stringify(result.newSerializedSnapshot, null, 2)}</pre>
        </div>
      )}
    </div>
  );
};

export default StateMachineExecutor;
