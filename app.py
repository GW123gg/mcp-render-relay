from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def root():
    return {
        "service": "MCP Relay",
        "status": "online"
    }


@app.get("/health")
async def health():
    return {
        "status": "ok"
    }
