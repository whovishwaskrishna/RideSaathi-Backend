from fastapi import WebSocket
from collections import defaultdict

class ConnectionManager:
    def __init__(self):
        self.active_connections = defaultdict(list)

    async def connect(self, route_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[route_id].append(websocket)

    def disconnect(self, route_id:int, websocket:WebSocket):
        if websocket in self.active_connections[route_id]:
            self.active_connections[route_id].remove(websocket)

    async def broadcast(self, route_id:int, data:dict):
        for connection in self.active_connections[route_id]:
            await connection.send_json(data)

manage = ConnectionManager()