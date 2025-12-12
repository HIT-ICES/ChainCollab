import React, { useMemo, useState } from "react";
import {
  AppBar,
  Avatar,
  Box,
  CssBaseline,
  Divider,
  Drawer,
  IconButton,
  MenuItem,
  Select,
  Stack,
  Toolbar,
  Typography,
} from "@mui/material";
import MenuIcon from "@mui/icons-material/Menu";
import Brightness4Icon from "@mui/icons-material/Brightness4";
import Brightness7Icon from "@mui/icons-material/Brightness7";
import { Outlet, useNavigate } from "react-router-dom";
import MainMenu from "@/views/Layout/MainMenu";
import MainBreadcrumbs from "@/views/Layout/MainBreadcrumbs";
import UserInfo from "@/views/Layout/UserInfo";
import logo from "@/assets/react.svg";
import NotificationCenter from "../NotificationCenter";
import "./style.css";
import { useTranslation } from "react-i18next";

const drawerWidth = 264;

const View: React.FC = () => {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [themeMode, setThemeMode] = useState<"light" | "dark">("light");
  const navigate = useNavigate();
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
          overflow: "hidden",
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
