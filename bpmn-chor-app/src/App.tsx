import ChorModelerApp from './ChorModelerApp';

const getQueryParam = (name: string, fallback: string) => {
  const params = new URLSearchParams(window.location.search);
  return params.get(name) ?? fallback;
};

const sanitizeToken = (token: string | null) => {
  if (!token) {
    return undefined;
  }
  return token.replace(/^"(.*)"$/, '$1');
};

const App = () => {
  const consortiumId = getQueryParam('consortiumid', '1');
  const orgId = getQueryParam('orgid', '1');
  const apiBaseUrl = import.meta.env.VITE_BPMN_API_BASE_URL ?? 'http://127.0.0.1:8000/api/v1';
  const translatorBaseUrl = import.meta.env.VITE_TRANSLATOR_API_BASE_URL ?? 'http://127.0.0.1:9999/api/v1';
  const authToken = sanitizeToken(window.localStorage.getItem('token'));

  return (
    <ChorModelerApp
      consortiumId={consortiumId}
      orgId={orgId}
      apiBaseUrl={apiBaseUrl}
      translatorBaseUrl={translatorBaseUrl}
      authToken={authToken}
    />
  );
};

export default App;
