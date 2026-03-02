from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.jwt import verify_token
from app.core.ws_manager import manage

router = APIRouter(prefix="/notifications", tags=["Notifications WS"])

@router.websocket("/ws")
async def notifications_socket(websocket: WebSocket):
    token = websocket.query_params.get("token")

    if not token:
        await websocket.close()
        return
    
    payload = verify_token(token)

    if not payload:
        await websocket.close()
        return
    
    user_id = int(payload.get("sub"))

    await manage.connect_user(user_id, websocket)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manage.disconnect_user(user_id)

        