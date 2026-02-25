Initial BPMN seed directory.

Backend loader imports this folder when you trigger:
- `POST /api/v1/consortiums/{consortium_id}/bpmns/import-initial`
- Frontend button: `BPMN -> Deploy -> Load Initial BPMN From Folder`

Rules:
1. Put BPMN files as `*.bpmn`.
2. Optional sidecar SVG: same basename with `.svg`.
   Example:
   - `OrderFlow.bpmn`
   - `OrderFlow.svg`
3. Import is idempotent per consortium by filename.
   If a BPMN with the same `name` already exists in that consortium, it will be skipped.

Override directory:
- Set env var `BPMN_INITIAL_DIR=/your/path`
