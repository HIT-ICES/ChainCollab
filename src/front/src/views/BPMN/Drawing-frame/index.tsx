import { useDispatch } from "react-redux";
import React, { useState } from "react";
import { FloatButton } from "antd";
import { set } from "lodash";
import { useAppSelector } from "@/redux/hooks.ts";
import { current_ip } from "@/api/apiConfig";

const Darwing = () => {
  // TODO: request new BPMN Model and get ID
  // TODO:
  const [uploadOpen, setUploadOpen] = useState(false);

  const consortiumid = useAppSelector((state) => state.consortium).currentConsortiumId;
  const orgid = useAppSelector((state) => state.org).currentOrgId;
  const iframeSrc = `${current_ip}:4913?consortiumid=` + consortiumid + "&orgid=" + orgid;
  return (
    <div>
      <div
        style={{
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          height: "calc(100vh - 160px)",
          background: "white",
        }}
      >
        <iframe
          width="100%"
          height="100%"
          src={iframeSrc}
          title="Modeler"
        />
      </div>
    </div>
  );
};

export default Darwing;
