from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Response, Request
import os
import json
import asyncio
import uuid

app = FastAPI()

TOKEN = os.getenv("RELAY_AGENT_TOKEN", "")

agent_connection = None
pending = {}


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

            data = json.loads(
                await ws.receive_text()
            )

            if data.get("type") == "response":

                future = pending.get(
                    data.get("id")
                )

                if future:
                    future.set_result(data)

    except WebSocketDisconnect:
        print("Agent disconnected")

    finally:

        if agent_connection == ws:
            agent_connection = None



@app.post("/mcp")
async def mcp_forward(
    request: Request,
    payload: dict
):

    if agent_connection is None:
        raise HTTPException(
            status_code=503,
            detail="Agent offline"
        )


    request_id = str(uuid.uuid4())

    future = asyncio.get_event_loop().create_future()

    pending[request_id] = future


    incoming_headers = {
        "mcp-session-id":
            request.headers.get(
                "mcp-session-id"
            ),
        "content-type":
            request.headers.get(
                "content-type"
            )
    }


    await agent_connection.send_text(
        json.dumps(
            {
                "type":"request",
                "id":request_id,
                "payload":payload,
                "headers":incoming_headers
            }
        )
    )


    try:

        result = await asyncio.wait_for(
            future,
            timeout=120
        )


        return Response(
            content=result.get(
                "body",
                ""
            ),
            headers=result.get(
                "headers",
                {}
            ),
            media_type=result.get(
                "headers",
                {}
            ).get(
                "content-type",
                "text/event-stream"
            )
        )

    finally:

        pending.pop(
            request_id,
            None
        )
