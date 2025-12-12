import React, { useEffect, useMemo, useState } from "react";
import { useLocation } from "react-router-dom";
import { ChorModelerApp } from "bpmn-chor-app";
import "bpmn-chor-app/dist/bpmn-chor-app.css";
import { useAppSelector } from "@/redux/hooks";
import { selectOrg } from "@/redux/slices/orgSlice";
import { selectConsortium } from "@/redux/slices/consortiumSlice";
import { backendBaseUrl, translatorBaseUrl } from "@/api/apiConfig";

const ChorModelerView: React.FC = () => {
  const { currentOrgId } = useAppSelector(selectOrg);
  const { currentConsortiumId } = useAppSelector(selectConsortium);
  const [orgId, setOrgId] = useState(currentOrgId || "");
  const [consortiumId, setConsortiumId] = useState(currentConsortiumId || "");
  const location = useLocation();

  useEffect(() => {
    if (currentOrgId) {
      setOrgId(currentOrgId);
    }
  }, [currentOrgId]);

  useEffect(() => {
    if (currentConsortiumId) {
      setConsortiumId(currentConsortiumId);
    }
  }, [currentConsortiumId]);

  useEffect(() => {
    setOrgId(currentOrgId || "");
    setConsortiumId(currentConsortiumId || "");
  }, [location.pathname]);

  const token = useMemo(() => {
    const value = localStorage.getItem("token");
    if (!value) return "";
    return value.replace(/^"(.*)"$/, "$1");
  }, []);

  const effectiveOrgId = orgId.trim();
  const effectiveConsortiumId = consortiumId.trim();
  const contextMissing = !effectiveOrgId || !effectiveConsortiumId;

  const serviceOverrides = useMemo(() => {
    if (!contextMissing) {
      return undefined;
    }
    return {
      addBpmn: async () => {
        throw new Error("Provide Org & Consortium IDs to enable BPMN upload.");
      },
      addDmn: async () => {
        throw new Error("Provide Org & Consortium IDs to enable DMN upload.");
      },
      getParticipantsByContent: async () => {
        throw new Error("Provide Org & Consortium IDs to enable translator service.");
      },
    };
  }, [contextMissing]);

  return (
    <div style={{ display: "flex", flexDirection: "column", flex: 1, minHeight: 0 }}>
      <div
        style={{
          display: "flex",
          gap: "16px",
          flexWrap: "wrap",
          marginBottom: "16px",
          alignItems: "flex-end",
        }}
      >
        <label style={{ display: "flex", flexDirection: "column", fontSize: 12, color: "#475569" }}>
          Organization ID
          <input
            value={orgId}
            onChange={(e) => setOrgId(e.target.value)}
            placeholder="Enter organization id"
            style={{
              border: "1px solid #cbd5f5",
              borderRadius: 6,
              padding: "6px 10px",
              minWidth: 240,
            }}
          />
        </label>
        <label style={{ display: "flex", flexDirection: "column", fontSize: 12, color: "#475569" }}>
          Consortium ID
          <input
            value={consortiumId}
            onChange={(e) => setConsortiumId(e.target.value)}
            placeholder="Enter consortium id"
            style={{
              border: "1px solid #cbd5f5",
              borderRadius: 6,
              padding: "6px 10px",
              minWidth: 240,
            }}
          />
        </label>
        {contextMissing && (
          <div style={{ color: "#b45309", fontSize: 13 }}>
            Editing仍可进行，但上传/翻译需提供真实 Org & Consortium ID。
          </div>
        )}
      </div>
      <div style={{ width: "100%", flex: 1, minHeight: 0 }}>
        <ChorModelerApp
          consortiumId={effectiveConsortiumId || "preview-consortium"}
          orgId={effectiveOrgId || "preview-org"}
          apiBaseUrl={`${backendBaseUrl}/api/v1`}
          translatorBaseUrl={`${translatorBaseUrl}/api/v1`}
          authToken={token}
          serviceOverrides={serviceOverrides}
          embedded
        />
      </div>
    </div>
  );
};

export default ChorModelerView;
