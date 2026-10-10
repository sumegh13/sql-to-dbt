import os

# The web app only ever uses the key a user enters for their own job: never .env, a Codespaces secret or the
# environment. Set before anything imports harness.translate, which otherwise loads .env.
os.environ["SQLTODBT_NO_DOTENV"] = "1"
os.environ.pop("ANTHROPIC_API_KEY", None)

import uvicorn  # noqa: E402

if __name__ == "__main__":
    # localhost by default; the dev container sets HOST=0.0.0.0 so Codespaces port forwarding can reach it
    uvicorn.run("app.server:app", host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", "8000")))
