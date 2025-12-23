export const API_BASE =
  import.meta.env.VITE_TRANSLATOR_API_BASE?.replace(/\/$/, '') || 'http://localhost:9999/api/v1';

export const ROUTES = {
  generate: '/chaincode/generate',
  participants: '/chaincode/getPartByBpmnC',
  messages: '/chaincode/getMessagesByBpmnC',
  businessRules: '/chaincode/getBusinessRulesByBpmnC',
  decisions: '/chaincode/getDecisions',
};
