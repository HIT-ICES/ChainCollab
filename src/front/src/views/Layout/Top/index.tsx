import React, { useMemo, useState } from "react";
import {
  AppBar,
  Avatar,
  Box,
  CssBaseline,
  Divider,
  Drawer,
  IconButton,
  Menu,
  MenuItem,
  Select,
  Stack,
  Toolbar,
  Typography,
  Button as MUIButton,
} from "@mui/material";
import MenuIcon from "@mui/icons-material/Menu";
import Brightness4Icon from "@mui/icons-material/Brightness4";
import Brightness7Icon from "@mui/icons-material/Brightness7";
import RocketLaunchIcon from "@mui/icons-material/RocketLaunch";
import { Outlet, useNavigate } from "react-router-dom";
import MainMenu from "@/views/Layout/MainMenu";
import MainBreadcrumbs from "@/views/Layout/MainBreadcrumbs";
import UserInfo from "@/views/Layout/UserInfo";
import logo from "@/assets/react.svg";
import NotificationCenter from "../NotificationCenter";
import "./style.css";
import { useTranslation } from "react-i18next";
import { message } from "antd";
import {
  createOrg,
  createConsortium,
  createEnvironment,
  createEthEnvironment,
  createMembership,
} from "@/api/platformAPI";
import { login, register } from "@/api/loginAPI";
import { useAppDispatch } from "@/redux/hooks";
import { activateOrg } from "@/redux/slices/orgSlice";
import { activateConsortium } from "@/redux/slices/consortiumSlice";
import { activateEnv } from "@/redux/slices/envSlice";

const drawerWidth = 264;

const View: React.FC = () => {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [themeMode, setThemeMode] = useState<"light" | "dark">("light");
  const [autoLoading, setAutoLoading] = useState(false);
  const [setupMenuAnchor, setSetupMenuAnchor] = useState<null | HTMLElement>(null);
  const [membershipCount, setMembershipCount] = useState(1);
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const { t, i18n } = useTranslation();

  const handleDrawerToggle = () => {
    setMobileOpen((prevState) => !prevState);
  };

  const toggleTheme = () => {
    setThemeMode((prev) => (prev === "light" ? "dark" : "light"));
  };

  const toggleLanguage = (value: string) => {
    i18n.changeLanguage(value);
  };

  const handleOneClickSetup = async (envType: "Fabric" | "Ethereum") => {
    try {
      setAutoLoading(true);
      const bootstrapUser = {
        username: "logres",
        email: "logres_king@126.com",
        password: "123",
      };
      try {
        await register(bootstrapUser.email, bootstrapUser.username, bootstrapUser.password);
      } catch (err: any) {
        const msg = err?.response?.data?.message || err?.message || "";
        if (!String(msg).toLowerCase().includes("exist")) {
          throw err;
        }
      }
      const loginResult = await login(bootstrapUser.email, bootstrapUser.password);
      if (!loginResult.isSuccess) {
        throw new Error("Login failed after one-click registration");
      }
      const suffix = Math.random().toString(36).slice(2, 5).toUpperCase();
      const orgName = `Atlas-${suffix}`;
      const consortiumName = `Aegis-${suffix}`;
      const envName = `Forge-${suffix}`;
      const baseMembershipLabels = ["Core", "Ops", "Labs"];
      const targetCount = Math.max(1, membershipCount);
      const membershipLabels =
        targetCount <= baseMembershipLabels.length
          ? baseMembershipLabels.slice(0, targetCount)
          : [
              ...baseMembershipLabels,
              ...Array.from(
                { length: targetCount - baseMembershipLabels.length },
                (_, index) => `Member${index + 1}`
              ),
            ];

      const org = await createOrg(orgName);
      dispatch(activateOrg({ currentOrgId: org.id, currentOrgName: org.name }));

      const consortium = await createConsortium(org.id, consortiumName);
      dispatch(
        activateConsortium({
          currentConsortiumId: consortium.id,
          currentConsortiumName: consortium.name,
        })
      );

      const membershipTasks: Promise<void>[] = [];
      membershipLabels.forEach((label) => {
        membershipTasks.push(
          createMembership(org.id, consortium.id, `${orgName}-${label}`)
        );
      });
      await Promise.all(membershipTasks);

      const env =
        envType === "Ethereum"
          ? await createEthEnvironment(consortium.id, envName)
          : await createEnvironment(consortium.id, envName);
      dispatch(
        activateEnv({
          currentEnvId: env.id,
          currentEnvName: env.name,
          currentEnvType: envType,
        })
      );

      message.success("One-click setup completed");
      navigate(`/orgs/${org.id}/consortia/${consortium.id}/envs/${env.id}/envdashboard`);
    } catch (error: any) {
      message.error(error?.message || "One-click setup failed");
    } finally {
      setAutoLoading(false);
    }
  };

  const handleOpenSetupMenu = (event: React.MouseEvent<HTMLButtonElement>) => {
    setSetupMenuAnchor(event.currentTarget);
  };

  const handleCloseSetupMenu = () => {
    setSetupMenuAnchor(null);
  };

  const handleSelectSetupType = (envType: "Fabric" | "Ethereum") => {
    handleCloseSetupMenu();
    handleOneClickSetup(envType);
  };

  const appBarStyles = useMemo(
    () =>
      themeMode === "light"
        ? {
            bgcolor: "rgba(255,255,255,0.95)",
            color: "#0f172a",
            borderBottom: "1px solid #dbe0ea",
            subtitle: "#475569",
          }
        : {
            bgcolor: "rgba(8,14,28,0.92)",
            color: "#e2e8f0",
            borderBottom: "1px solid rgba(148,163,184,0.25)",
            subtitle: "#cbd5f5",
          },
    [themeMode]
  );

  const drawer = (
    <Box
      className={`portal-drawer portal-drawer--${themeMode}`}
      role="presentation"
    >
      <Box className="portal-logo" onClick={() => navigate("/home")}>
        <Avatar
          src={logo}
          variant="rounded"
          sx={{ width: 40, height: 40, bgcolor: "transparent" }}
        />
        <div>
          <Typography variant="subtitle1" className="portal-logo__title">
            LFBaaS
          </Typography>
          <Typography variant="caption" className="portal-logo__sub">
            Linked Future
          </Typography>
        </div>
      </Box>
      <Divider />
      <Box className="portal-menu">
        <MainMenu />
      </Box>
    </Box>
  );

  return (
    <Box
      className={`portal-root portal-root--${themeMode}`}
      sx={{
        display: "flex",
        height: "100vh",
        overflow: "hidden",
        bgcolor: themeMode === "light" ? "#f4f6fb" : "#050914",
        transition: "background 0.3s ease",
      }}
    >
      <CssBaseline />
      <AppBar
        position="fixed"
        elevation={0}
        color="default"
        sx={{
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          ml: { sm: `${drawerWidth}px` },
          bgcolor: appBarStyles.bgcolor,
          color: appBarStyles.color,
          boxShadow:
            themeMode === "light"
              ? "0 10px 30px rgba(15,23,42,0.12)"
              : "0 18px 40px rgba(0,0,0,0.45)",
          borderBottom: appBarStyles.borderBottom,
          backdropFilter: "saturate(180%) blur(16px)",
        }}
      >
        <Toolbar sx={{ minHeight: 88 }}>
          <IconButton
            color="inherit"
            edge="start"
            onClick={handleDrawerToggle}
            sx={{ mr: 2, display: { sm: "none" } }}
          >
            <MenuIcon />
          </IconButton>
          <Box>
            <Typography variant="h6" sx={{ fontWeight: 700, color: appBarStyles.color }}>
              {t("layout.title")}
            </Typography>
            <Typography variant="body2" sx={{ color: appBarStyles.subtitle }}>
              {t("layout.subtitle")}
            </Typography>
          </Box>
          <Box sx={{ flexGrow: 1, px: 4 }}>
            <MainBreadcrumbs />
          </Box>
          <Stack direction="row" spacing={2} alignItems="center">
            <MUIButton
              size="small"
              variant="contained"
              color="primary"
              startIcon={<RocketLaunchIcon />}
              onClick={handleOpenSetupMenu}
              disabled={autoLoading}
              sx={{ textTransform: "none" }}
            >
              {autoLoading ? "Creating..." : "One-click Setup"}
            </MUIButton>
            <Menu
              anchorEl={setupMenuAnchor}
              open={Boolean(setupMenuAnchor)}
              onClose={handleCloseSetupMenu}
              anchorOrigin={{ vertical: "bottom", horizontal: "left" }}
              transformOrigin={{ vertical: "top", horizontal: "left" }}
            >
              <MenuItem
                disableRipple
                onClick={(event) => event.stopPropagation()}
                sx={{ gap: 2 }}
              >
                <Typography variant="body2" sx={{ minWidth: 110 }}>
                  Memberships
                </Typography>
                <Select
                  size="small"
                  value={membershipCount}
                  onChange={(event) => setMembershipCount(Number(event.target.value))}
                  onClick={(event) => event.stopPropagation()}
                  sx={{ minWidth: 80 }}
                >
                  {[1, 2, 3, 4, 5, 6].map((count) => (
                    <MenuItem key={count} value={count}>
                      {count}
                    </MenuItem>
                  ))}
                </Select>
              </MenuItem>
              <MenuItem
                onClick={() => handleSelectSetupType("Fabric")}
                disabled={autoLoading}
              >
                Fabric
              </MenuItem>
              <MenuItem
                onClick={() => handleSelectSetupType("Ethereum")}
                disabled={autoLoading}
              >
                Ethereum (ETH)
              </MenuItem>
            </Menu>
            <Select
              size="small"
              value={i18n.language}
              onChange={(e) => toggleLanguage(e.target.value)}
              sx={{
                minWidth: 80,
                background: "rgba(255,255,255,0.2)",
                color: "inherit",
                "& .MuiSelect-icon": { color: "inherit" },
              }}
            >
              <MenuItem value="zh">中文</MenuItem>
              <MenuItem value="en">English</MenuItem>
            </Select>
            <IconButton color="inherit" onClick={toggleTheme}>
              {themeMode === "light" ? <Brightness4Icon /> : <Brightness7Icon />}
            </IconButton>
            <NotificationCenter />
            <UserInfo />
          </Stack>
        </Toolbar>
      </AppBar>
      <Box
        component="nav"
        sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }}
        aria-label="sidebar navigation"
      >
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{
            keepMounted: true,
          }}
          sx={{
            display: { xs: "block", sm: "none" },
            "& .MuiDrawer-paper": {
              boxSizing: "border-box",
              width: drawerWidth,
              borderRight: 0,
            },
          }}
        >
          {drawer}
        </Drawer>
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: "none", sm: "block" },
            "& .MuiDrawer-paper": {
              boxSizing: "border-box",
              width: drawerWidth,
              borderRight: 0,
            },
          }}
          open
        >
          {drawer}
        </Drawer>
      </Box>
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          display: "flex",
          flexDirection: "column",
          p: { xs: 2, md: 4 },
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          mt: { xs: 8, sm: 10 },
          overflow: "auto",
        }}
      >
        <Box className="portal-main-surface">
          <Outlet />
        </Box>
        <Typography className="portal-footer">
          {t("layout.footer")}
        </Typography>
      </Box>
    </Box>
  );
};

export default View;
