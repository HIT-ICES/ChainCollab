from __future__ import annotations

import uvicorn


def main() -> None:
    uvicorn.run("relayer_node.backend.app:app", host="0.0.0.0", port=8082, reload=False)


if __name__ == "__main__":
    main()
