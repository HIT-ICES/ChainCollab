import i18n from "i18next";
import { initReactI18next } from "react-i18next";

const resources = {
  en: {
    translation: {
      layout: {
        title: "LFBaaS Control Plane",
        subtitle: "Manage organizations, consortia and BPMN executions",
        footer: "LFBaaS ©2023 Created by Linked Future",
      },
    },
  },
  zh: {
    translation: {
      layout: {
        title: "LFBaaS 控制平面",
        subtitle: "统一管理组织、联盟与 BPMN 执行",
        footer: "LFBaaS ©2023 由 Linked Future 构建",
      },
    },
  },
};

i18n.use(initReactI18next).init({
  resources,
  lng: "zh",
  fallbackLng: "en",
  interpolation: {
    escapeValue: false,
  },
});

export default i18n;
