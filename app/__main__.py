import os

import uvicorn

if __name__ == "__main__":
    # localhost by default; the dev container sets HOST=0.0.0.0 so Codespaces port forwarding can reach it
    uvicorn.run("app.server:app", host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", "8000")))
