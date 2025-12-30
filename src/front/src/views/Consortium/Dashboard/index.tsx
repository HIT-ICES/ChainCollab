import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Row, Col, Card, Typography } from "antd";
import Env from "./Env";
import { getMembershipList } from "@/api/platformAPI";
import { useAppSelector } from "@/redux/hooks";
import { selectConsortium } from "@/redux/slices/consortiumSlice";
import { selectOrg } from "@/redux/slices/orgSlice";
import ReactFlow, { applyNodeChanges, Background, Controls, NodeChange } from "reactflow";
import "reactflow/dist/style.css";

const { Title, Text } = Typography;

const Dashboard: React.FC = () => {
  const navigate = useNavigate();
  const currentConsortiumId = useAppSelector(selectConsortium).currentConsortiumId;
  const currentConsortiumName = useAppSelector(selectConsortium).currentConsortiumName;
  const currentOrgName = useAppSelector(selectOrg).currentOrgName;
  const currentOrgId = useAppSelector(selectOrg).currentOrgId;
  const [membershipList, setMembershipList] = useState<any[]>([]);
  const [membershipLoading, setMembershipLoading] = useState(false);

  useEffect(() => {
    if (!currentConsortiumId) {
      setMembershipList([]);
      return;
    }
    let mounted = true;
    const fetchMemberships = async () => {
      try {
        setMembershipLoading(true);
        const res = await getMembershipList(currentConsortiumId);
        if (mounted) {
          setMembershipList(Array.isArray(res) ? res : []);
        }
      } finally {
        if (mounted) {
          setMembershipLoading(false);
        }
      }
    };
    fetchMemberships();
    return () => {
      mounted = false;
    };
  }, [currentConsortiumId]);

  const membershipNames = membershipList.map((item) => item.name ?? item.id);

  const orgGroups = useMemo(() => {
    const map = new Map<string, { id: string; name: string; memberships: any[] }>();
    membershipList.forEach((membership) => {
      const orgId = membership.loleido_organization || membership.orgId;
      if (!orgId) {
        return;
      }
      const orgName =
        membership.organization_name ||
        membership.orgName ||
        membership.org ||
        orgId;
      if (!map.has(orgId)) {
        map.set(orgId, { id: orgId, name: orgName, memberships: [] });
      }
      map.get(orgId)?.memberships.push(membership);
    });

    if (map.size === 0 && currentOrgId) {
      map.set(currentOrgId, {
        id: currentOrgId,
        name: currentOrgName || "Org",
        memberships: [],
      });
    }

    return Array.from(map.values());
  }, [membershipList, currentOrgId, currentOrgName]);

  const [relationshipNodes, setRelationshipNodes] = useState<any[]>([]);

  const buildRelationshipNodes = useCallback(() => {
    const nodes: any[] = [
      {
        id: "consortium",
        data: {
          label: (
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <span style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.08em", color: "#64748b" }}>
                Consortium
              </span>
              <span>{currentConsortiumName || "未选择"}</span>
            </div>
          ),
          dimensions: { width: 220, height: 64 },
        },
        position: { x: 0, y: 0 },
        style: {
          minWidth: 220,
          padding: "12px 16px",
          borderRadius: 14,
          background: "linear-gradient(145deg, #ffffff, #f8fafc)",
          border: "1px solid #e2e8f0",
          boxShadow: "0 10px 24px rgba(15,23,42,0.08)",
          fontWeight: 600,
        },
      },
    ];

    const orgCount = Math.max(1, orgGroups.length);
    const orgSpread = orgCount - 1;
    const orgSpacing = 260;
    const membershipSpacing = 220;

    orgGroups.forEach((org, index) => {
      const orgX = (index - orgSpread / 2) * orgSpacing;
      nodes.push({
        id: `org-${org.id}`,
        data: {
          label: (
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <span style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.08em", color: "#64748b" }}>
                Organization
              </span>
              <span>{org.name}</span>
            </div>
          ),
          orgId: org.id,
          dimensions: { width: 220, height: 64 },
        },
        position: { x: orgX, y: 120 },
        style: {
          minWidth: 220,
          padding: "12px 16px",
          borderRadius: 14,
          background: "linear-gradient(145deg, #ffffff, #f8fafc)",
          border: "1px solid #e2e8f0",
          boxShadow: "0 10px 24px rgba(15,23,42,0.08)",
          fontWeight: 600,
        },
      });

      const memberships =
        org.memberships.length > 0
          ? org.memberships
          : [{ id: `empty-${org.id}`, name: "暂无", placeholder: true }];
      const membershipSpread = memberships.length - 1;

      memberships.forEach((membership, memberIndex) => {
        nodes.push({
          id: `membership-${membership.id}`,
          data: {
            label: (
              <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
                <span style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.08em", color: "#64748b" }}>
                  Membership
                </span>
                <span>{membership.name}</span>
              </div>
            ),
            membershipId: membership.id,
            orgId: org.id,
            dimensions: { width: 200, height: 56 },
          },
          position: {
            x: orgX + (memberIndex - membershipSpread / 2) * membershipSpacing,
            y: 260,
          },
          style: {
            minWidth: 200,
            padding: "10px 14px",
            borderRadius: 14,
            background: membership.placeholder
              ? "linear-gradient(145deg, #f8fafc, #e2e8f0)"
              : "linear-gradient(145deg, #ffffff, #f8fafc)",
            border: "1px solid #e2e8f0",
            boxShadow: "0 10px 24px rgba(15,23,42,0.08)",
            opacity: membership.placeholder ? 0.7 : 1,
          },
        });
      });
    });

    return nodes;
  }, [currentConsortiumName, orgGroups]);

  useEffect(() => {
    setRelationshipNodes(buildRelationshipNodes());
  }, [buildRelationshipNodes]);

  const relationshipEdges = useMemo(() => {
    const orgEdges = relationshipNodes
      .filter((node) => node.id.startsWith("org-"))
      .map((node) => ({
        id: `consortium-${node.id}`,
        source: "consortium",
        target: node.id,
        animated: false,
        style: { stroke: "#60a5fa" },
      }));

    const membershipEdges = relationshipNodes
      .filter((node) => node.id.startsWith("membership-"))
      .map((node) => {
        const orgId = node.data?.orgId;
        return {
          id: `org-${orgId}-${node.id}`,
          source: `org-${orgId}`,
          target: node.id,
          animated: false,
          style: { stroke: "#94a3b8" },
        };
      });

    return [...orgEdges, ...membershipEdges];
  }, [relationshipNodes]);

  const onNodesChange = useCallback((changes: NodeChange[]) => {
    setRelationshipNodes((nodes) => applyNodeChanges(changes, nodes));
  }, []);

  const resolveOverlap = useCallback((draggedNode: any, nodes: any[]) => {
    const draggedDims = draggedNode.data?.dimensions || { width: 200, height: 56 };
    const margin = 16;
    let nextPosition = { ...draggedNode.position };
    let iterations = 0;
    let hasOverlap = true;

    while (hasOverlap && iterations < 20) {
      hasOverlap = false;
      for (const node of nodes) {
        if (node.id === draggedNode.id) {
          continue;
        }
        const nodeDims = node.data?.dimensions || { width: 200, height: 56 };
        const dx = Math.abs(nextPosition.x - node.position.x);
        const dy = Math.abs(nextPosition.y - node.position.y);
        const minX = (draggedDims.width + nodeDims.width) / 2 + margin;
        const minY = (draggedDims.height + nodeDims.height) / 2 + margin;
        if (dx < minX && dy < minY) {
          hasOverlap = true;
          nextPosition = {
            x: nextPosition.x + (dx < minX ? minX - dx + 12 : 0),
            y: nextPosition.y + minY - dy + 12,
          };
          break;
        }
      }
      iterations += 1;
    }

    return nextPosition;
  }, []);

  const handleNodeDragStop = useCallback((_: any, node: any) => {
    setRelationshipNodes((nodes) => {
      const resolvedPosition = resolveOverlap(node, nodes);
      return nodes.map((item) =>
        item.id === node.id ? { ...item, position: resolvedPosition } : item
      );
    });
  }, [resolveOverlap]);

  const handleNodeClick = (_: any, node: any) => {
    if (node.id === "consortium" && currentConsortiumId) {
      const targetOrgId = currentOrgId || orgGroups[0]?.id;
      if (targetOrgId) {
        navigate(`/orgs/${targetOrgId}/consortia/${currentConsortiumId}/dashboard`);
      }
      return;
    }
    if (node.id.startsWith("org-") && node.data?.orgId) {
      navigate(`/orgs/${node.data.orgId}/dashboard`);
      return;
    }
    if (node.id.startsWith("membership-") && currentOrgId && currentConsortiumId) {
      navigate(`/orgs/${currentOrgId}/consortia/${currentConsortiumId}/memberships`);
    }
  };

  return (
    <div style={{ padding: 8 }}>
      <Card
        bordered={false}
        style={{
          borderRadius: 18,
          boxShadow: "0 16px 46px rgba(15,23,42,0.16)",
          border: "1px solid #e2e8f0",
          marginBottom: 16,
          background: "linear-gradient(120deg, #0f172a, #1f2937 50%, #0ea5e9)",
          color: "#e2e8f0",
        }}
        title={<Title level={3} style={{ margin: 0, color: "#f8fafc" }}>Consortium Dashboard</Title>}
      >
        <Text style={{ color: "#cbd5f5" }}>查看当前联盟的环境与应用概况。</Text>
      </Card>

      <Row gutter={16} style={{ marginBottom: 20 }}>
        <Col span={12}>
          <Card
            title="Consortium Relationship"
            bordered={false}
            style={{
              borderRadius: 16,
              boxShadow: "0 14px 40px rgba(15,23,42,0.12)",
              border: "1px solid #e2e8f0",
              height: "100%",
            }}
          >
            <div style={{ height: 320 }}>
              <ReactFlow
                nodes={relationshipNodes}
                edges={relationshipEdges}
                fitView
                onNodeClick={handleNodeClick}
                onNodesChange={onNodesChange}
                onNodeDragStop={handleNodeDragStop}
                nodesDraggable
                nodesConnectable={false}
                elementsSelectable={false}
                snapToGrid
                snapGrid={[12, 12]}
              >
                <Controls showInteractive={false} />
                <Background gap={16} color="#e2e8f0" />
              </ReactFlow>
            </div>
          </Card>
        </Col>
        <Col span={12}>
          <Env />
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;
