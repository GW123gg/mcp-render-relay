from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
import os
import json
import asyncio
import uuid
import time

app = FastAPI()

TOKEN = os.getenv("RELAY_AGENT_TOKEN", "")

agent_connection = None

pending = {}


@app.get("/")
async def root():
    return {
        "service": "MCP Relay",
        "agent_connected": agent_connection is not None
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

    auth = ws.headers.get("authorization")

    if TOKEN and auth != f"Bearer {TOKEN}":
        await ws.close(code=1008)
        return

    await ws.accept()

    agent_connection = ws

    print("Agent connected")

    try:
        while True:
            msg = await ws.receive_text()

            data = json.loads(msg)

            if data.get("type") == "response":

                request_id = data.get("id")

                if request_id in pending:
                    pending[request_id].set_result(data)

    except WebSocketDisconnect:
        print("Agent disconnected")

    finally:
        if agent_connection == ws:
            agent_connection = None



@app.post("/mcp")
async def mcp_forward(payload: dict):

    if agent_connection is None:
        raise HTTPException(
            status_code=503,
            detail="Agent offline"
        )

    request_id = str(uuid.uuid4())

    future = asyncio.get_event_loop().create_future()

    pending[request_id] = future

    await agent_connection.send_text(
        json.dumps({
            "type":"request",
            "id":request_id,
            "payload":payload
        })
    )

    try:
        result = await asyncio.wait_for(
            future,
            timeout=120
        )

        return result["result"]

    except asyncio.TimeoutError:

        raise HTTPException(
            status_code=504,
            detail="MCP timeout"
        )

    finally:
        pending.pop(
            request_id,
            None
        )
