## BPMN Chor-js Standalone Frontend

This package extracts the BPMN choreography modeler (with DMN editing) from the monolithic `IBC-FRONT` application and turns it into an installable React library plus a runnable demo shell.

### Features
- Full `chor-js` modeler with palette, properties panel, and built-in validator overlays.
- DMN authoring popup backed by `dmn-js`, including staged DMN uploads.
- API abstraction for BPMN/DMN uploads (`createDefaultChorApiClient`) that can be replaced or extended by the host.
- Ready-to-embed React component (`ChorModelerApp`) and Vite dev server for iframe hosting (`npm run dev`).

### Local Development
```bash
npm install        # already run for you
npm run dev        # serves the demo shell on http://localhost:5173
npm run build      # type-check + library bundle in dist/
```

The dev shell (`src/App.tsx`) reads `?consortiumid=` & `?orgid=` from the URL and falls back to `1/1`. Override API endpoints by exporting:
```
VITE_BPMN_API_BASE_URL=http://127.0.0.1:8000/api/v1
VITE_TRANSLATOR_API_BASE_URL=http://127.0.0.1:9999/api/v1
```

### Consuming the Package
After publishing (or via a workspace link) you can import the component:
```tsx
import { ChorModelerApp } from 'bpmn-chor-app';

<ChorModelerApp
  consortiumId="consortium-1"
  orgId="org-1"
  apiBaseUrl="https://backend/api/v1"
  translatorBaseUrl="https://translator/api/v1"
  authToken="<jwt-token>"
/>
```

#### Props
| Prop | Description |
| --- | --- |
| `consortiumId`, `orgId` | Required identifiers to tag BPMN/DMN uploads. |
| `apiBaseUrl`, `translatorBaseUrl` | Full REST base URLs (include `/api/v1`). |
| `authToken`, `authScheme` | Optional auth header (`JWT` by default). |
| `headers`, `fetchImpl` | Override request headers or supply a custom `fetch`. |
| `defaultDiagramXml` | Provide initial BPMN XML (defaults to the blank diagram). |
| `serviceOverrides` | Inject custom implementations for `addBpmn`, `addDmn`, or `getParticipantsByContent`. |
| `onBpmnUpload` | Callback that receives the API response after a BPMN upload. |

All BPMN / DMN API calls go through `createDefaultChorApiClient`. If your backend differs, provide replacements via `serviceOverrides`.

### Referencing from the Existing Monorepo
1. Build & publish (or `npm link`) `bpmn-chor-app`.
2. Add it to `IBC-FRONT` (`npm install ../bpmn-chor-app` for local testing).
3. Replace the iframe in `src/front/src/views/BPMN/Drawing-frame/index.tsx` with a direct import:
```tsx
import { ChorModelerApp } from 'bpmn-chor-app';
// ...
<ChorModelerApp
  consortiumId={consortiumId}
  orgId={orgId}
  apiBaseUrl={`${current_ip}/api/v1`}
  translatorBaseUrl={`${current_ip_translator}/api/v1`}
  authToken={token}
/>
```

Alternatively keep the iframe flow: deploy this project (e.g., `npm run dev -- --host --port 4913`) and point the existing iframe to the hosted URL. The standalone shell still honors the same query parameters for compatibility.

### Notes
- The heavy pop-up editors (`DmnModal`, `MessageModal`, etc.) remain JavaScript-heavy; `// @ts-nocheck` prevents TypeScript noise without touching upstream logic.
- Built artifacts land in `dist/` (`.es.js` and `.cjs` bundles + CSS + types). They are included on publish through the `files` list.
- The custom `chor-js` fork (under `src/modeler/chor-js`) stays vendored so that changes remain deterministic and upgradable independently from upstream `chor-js`.
