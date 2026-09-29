from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()

agent_connection = None


@app.get("/")
async def root():
    return {
        "service": "MCP Relay",
        "status": "online"
    }


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "agent_connected": agent_connection is not None
    }


@app.websocket("/agent")
async def agent(ws: WebSocket):

    global agent_connection

    await ws.accept()

    agent_connection = ws

    print("Agent connected")

    try:
        while True:
            data = await ws.receive_text()

            print(
                "Agent message:",
                data
            )

    except WebSocketDisconnect:

        print("Agent disconnected")

        agent_connection = None
