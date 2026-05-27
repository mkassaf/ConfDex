from __future__ import annotations

import os
from pathlib import Path


def main() -> None:
    import uvicorn
    from confscraper.web.app import create_app

    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    db_path = Path(os.environ.get("DB_PATH", "confdex.db"))

    app = create_app(db_path=db_path)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
