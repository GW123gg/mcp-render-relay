from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
    HTTPException,
)

import os
import json
import time


app = FastAPI()


# ============================
# Configuration
# ============================

RELAY_TOKEN = os.getenv(
    "RELAY_AGENT_TOKEN",
    ""
)


# 현재 연결된 Agent
agent_connection: WebSocket | None = None


# 마지막 heartbeat
last_heartbeat = None



# ============================
# Basic HTTP
# ============================


@app.get("/")
async def root():

    return {
        "service": "MCP Relay",
        "status": "online",
        "agent_connected":
            agent_connection is not None
    }



@app.get("/health")
async def health():

    return {
        "status": "ok",

        "agent_connected":
            agent_connection is not None,

        "last_heartbeat":
            last_heartbeat
    }



# ============================
# Agent WebSocket
# ============================


@app.websocket("/agent")
async def agent_socket(
    websocket: WebSocket
):

    global agent_connection
    global last_heartbeat


    # -------------------------
    # Token Check
    # -------------------------

    auth = websocket.headers.get(
        "authorization"
    )


    expected = (
        f"Bearer {RELAY_TOKEN}"
    )


    if RELAY_TOKEN:

        if auth != expected:

            await websocket.close(
                code=1008,
                reason="Invalid token"
            )

            print(
                "Rejected agent connection"
            )

            return



    # -------------------------
    # Accept
    # -------------------------

    await websocket.accept()


    agent_connection = websocket


    print(
        "Agent connected"
    )


    try:

        while True:

            message = await websocket.receive_text()


            try:

                data = json.loads(
                    message
                )


            except Exception:


                print(
                    "Invalid JSON:",
                    message
                )

                continue



            msg_type = data.get(
                "type"
            )


            # ---------------------
            # Heartbeat
            # ---------------------

            if msg_type == "heartbeat":


                last_heartbeat = time.time()


                await websocket.send(
                    json.dumps(
                        {
                            "type":
                                "heartbeat_ack",

                            "timestamp":
                                last_heartbeat
                        }
                    )
                )


                continue



            # ---------------------
            # Debug
            # ---------------------

            print(
                "Agent message:",
                data
            )



    except WebSocketDisconnect:


        print(
            "Agent disconnected"
        )


    finally:

        if agent_connection == websocket:

            agent_connection = None



# ============================
# Future MCP Forwarding
# ============================


@app.post("/mcp")
async def mcp_forward(
    payload: dict
):


    if agent_connection is None:


        raise HTTPException(
            status_code=503,
            detail="Agent offline"
        )


    request_id = (
        str(time.time())
    )


    message = {

        "type":
            "request",

        "id":
            request_id,

        "payload":
            payload
    }


    await agent_connection.send_text(
        json.dumps(message)
    )


    return {

        "status":
            "sent",

        "id":
            request_id
    }
