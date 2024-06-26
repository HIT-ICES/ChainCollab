import React, { lazy } from "react";
import Top from "@/views/Layout/Top";
import Login from "@/views/Login";
import SkeletonLoading from "@/views/SkeletonLoading";
import { Navigate } from "react-router-dom";
import { routesType } from "@/types/route";

const Error404 = lazy(() => import("@/views/Error/404"));
// const App = lazy(() => import("@/views/Environment/App"));
const Chaincode = lazy(() => import("@/views/Environment/Fabric/Chaincode"));
const Channel = lazy(() => import("@/views/Environment/Fabric/Channel"));
const Node = lazy(() => import("@/views/Environment/Fabric/Node"));
const Firefly = lazy(() => import("@/views/Environment/Firefly"));
const FireflyDetail = lazy(() => import("@/views/Environment/Firefly/Detail"));
const Files = lazy(() => import("@/views/Files"));
const UsersManage = lazy(() => import("@/views/Organization/UsersManage"));
const OrgSettings = lazy(() => import("@/views/Organization/Settings"));
const OrgDashboard = lazy(() => import("@/views/Organization/Dashboard"));
const Home = lazy(() => import("@/views/Home"));
const NetworkDashboard = lazy(() => import("@/views/Network/Dashboard"));
const Memberships = lazy(() => import("@/views/Network/Memberships"));
const FabricUsers = lazy(() => import("@/views/Network/FabricUsers"));
const MembershipDetail = lazy(
  () => import("@/views/Network/Memberships/Detail")
);
const NetworkSettings = lazy(() => import("@/views/Network/Settings"));
const Drawing = lazy(() => import("@/views/BPMN/Drawing"));
const Execution = lazy(() => import("@/views/BPMN/Execution"));
const Translation = lazy(() => import("@/views/BPMN/Translation"));
const SvgComponent = lazy(() => import("@/views/BPMN/Execution/SvgComponent"));
const ChorJs = lazy(() => import("@/views/BPMN/Chor-js"));
const ResourceSet = lazy(() => import("@/views/Environment/ResourceSet"));
const EnvDashboard = lazy(() => import("@/views/Environment/Dashboard"));
const MembershipDetailInEnv = lazy(() => import("@/views/Environment/Dashboard/Overview/MembershipDetail"));
// const Register = lazy(() => import("@/views/BPMN/Register"));
const BPMNInstanceOverview = lazy(() => import("@/views/BPMN/Translation/Detail"));
const withLoadingComponent = (Comp: JSX.Element) => (
  <React.Suspense fallback={<SkeletonLoading />}>{Comp}</React.Suspense>
);
const MembershipCardInEnv = lazy(() => import("@/views/Environment/Dashboard/Overview/MembershipDetail/Detail"));

const routes: routesType[] = [
  {
    path: "/",
    element: <Navigate to="/login" />,
  },
  {
    path: "*",
    element: <Navigate to="/404" />,
  },
  {
    path: "/404",
    element: <Error404 />,
  },
  {
    path: "/login",
    element: <Login />,
  },
  {
    path: "/",
    element: <Top />,
    exact: true,
    name: "menuRoutes",
    children: [
      {
        path: "/home",
        element: withLoadingComponent(<Home />),
        meta: {
          title: "Home",
        },
      },
      {
        path: "/orgs/:org_id",
        meta: {
          title: "Organization",
        },
        children: [
          {
            // ！！！: 不需要从/开始的完整路径，只需要相对于父级元素的路径就可以了
            path: "dashboard",
            element: withLoadingComponent(<OrgDashboard />),
            meta: {
              title: "Dashboard",
            },
          },
          {
            path: "usersmanage",
            element: withLoadingComponent(<UsersManage />),
            meta: {
              title: "Manage Users",
            },
          },
          {
            path: "settings",
            element: withLoadingComponent(<OrgSettings />),
            meta: {
              title: "Settings",
            },
          },

          // Consortia
          {
            path: "/orgs/:org_id/consortia/:consortium_id",
            meta: {
              title: "Consortium",
            },
            children: [
              {
                path: "/orgs/:org_id/consortia/:consortium_id/dashboard",
                element: withLoadingComponent(<NetworkDashboard />),
                meta: {
                  title: "Dashboard",
                },
              },
              {
                path: "/orgs/:org_id/consortia/:consortium_id/memberships",
                element: withLoadingComponent(<Memberships />),
                meta: {
                  title: "Memberships",
                },
              },
              {
                path: "/orgs/:org_id/consortia/:consortium_id/memberships/:membership_id",
                element: withLoadingComponent(<MembershipDetail />),
                meta: {
                  title: "Detail",
                },
              },
              {
                path: "/orgs/:org_id/consortia/:consortium_id/memberships/:membership_id/fabricusers",
                element: withLoadingComponent(<FabricUsers />),
                meta: {
                  title: "FabricUsers",
                },
              },
              {
                path: "/orgs/:org_id/consortia/:consortium_id/settings",
                element: withLoadingComponent(<NetworkSettings />),
                meta: {
                  title: "Settings",
                },
              },

              // Environments
              {
                path: "/orgs/:org_id/consortia/:consortium_id/envs/:env_id",
                meta: {
                  title: "Environment",
                },
                children: [
                  {
                    path: "/orgs/:org_id/consortia/:consortium_id/envs/:env_id/envdashboard",
                    element: withLoadingComponent(<EnvDashboard />),
                    meta: {
                      title: "EnvDashboard",
                    },
                  },
                  {
                    path: "/orgs/:org_id/consortia/:consortium_id/envs/:env_id/envdashboard/:memberships_details_id",
                    element: withLoadingComponent(<MembershipDetailInEnv />),
                    meta: {
                      title: "Memberships",
                    },
                  },
                  {
                    path: "/orgs/:org_id/consortia/:consortium_id/envs/:env_id/envdashboard/:memberships_details_id/:membership_id",
                    element: withLoadingComponent(<MembershipCardInEnv />),
                    meta: {
                      title: "MembershipDetail",
                    },
                  },
                  {
                    path: "/orgs/:org_id/consortia/:consortium_id/envs/:env_id/resourceset",
                    element: withLoadingComponent(<ResourceSet />),
                    meta: {
                      title: "ResourceSet",
                    },
                  },

                  {
                    path: "/orgs/:org_id/consortia/:consortium_id/envs/:env_id/fabric",
                    meta: {
                      title: "Fabric",
                    },
                    children: [
                      {
                        path: "/orgs/:org_id/consortia/:consortium_id/envs/:env_id/fabric/channel",
                        element: withLoadingComponent(<Channel />),
                        meta: {
                          title: "Channel",
                        },
                      },
                      {
                        path: "/orgs/:org_id/consortia/:consortium_id/envs/:env_id/fabric/chaincode",
                        element: withLoadingComponent(<Chaincode />),
                        meta: {
                          title: "Chaincode",
                        },
                      },
                      {
                        path: "/orgs/:org_id/consortia/:consortium_id/envs/:env_id/fabric/node",
                        element: withLoadingComponent(<Node />),
                        meta: {
                          title: "Node",
                        },
                      },
                    ],
                  },
                  {
                    path: "/orgs/:org_id/consortia/:consortium_id/envs/:env_id/firefly",
                    element: withLoadingComponent(<Firefly />),
                    meta: {
                      title: "Firefly",
                    },
                  },
                  {
                    path: "/orgs/:org_id/consortia/:consortium_id/envs/:env_id/firefly/:id",
                    element: withLoadingComponent(<FireflyDetail />),
                    meta: {
                      title: "FireflyDetail",
                    },
                  },
                ],
              },
            ],
          },
        ],
      },
      {
        path: "/bpmn",
        meta: {
          title: "BPMN",
        },
        children: [
          {
            path: "/bpmn/drawing",
            element: withLoadingComponent(<Drawing />),
            meta: {
              title: "Drawing",
            },
          },
          {
            path: "/bpmn/chor-js",
            element: withLoadingComponent(<ChorJs />),
            meta: {
              title: "Chor-js",
            },
          },
          {
            path: "/bpmn/translation",
            element: withLoadingComponent(<Translation />),
            meta: {
              title: "Translation",
            },
          },
          {
            path: "/bpmn/translation/:id",
            element: withLoadingComponent(<BPMNInstanceOverview />),
            meta: {
              title: "Translation Detail",
            },
          },
          {
            path: "/bpmn/execution",
            element: withLoadingComponent(<Execution />),
            meta: {
              title: "Execution",
            },
          },
          {
            path: "/bpmn/execution/:id",
            element: withLoadingComponent(<SvgComponent />),
            meta: {
              title: "SvgComponent",
            },
          },
        ],
      },
    ],
  },
];

export default routes;
