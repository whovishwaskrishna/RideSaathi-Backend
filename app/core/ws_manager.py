from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.route_connections = {}   # route_id → set of websockets
        self.user_connections = {}    # user_id → websocket

    # -------------------------
    # ROUTE CONNECTIONS
    # -------------------------
    async def connect_route(self, route_id: int, websocket: WebSocket):
        await websocket.accept()
        if route_id not in self.route_connections:
            self.route_connections[route_id] = set()
        self.route_connections[route_id].add(websocket)

    def disconnect_route(self, route_id: int, websocket: WebSocket):
        if route_id in self.route_connections:
            self.route_connections[route_id].discard(websocket)

    async def broadcast_route(self, route_id: int, message: dict):
        if route_id in self.route_connections:
            for connection in list(self.route_connections[route_id]):
                await connection.send_json(message)

    # -------------------------
    # USER CONNECTIONS
    # -------------------------
    async def connect_user(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        self.user_connections[user_id] = websocket

    def disconnect_user(self, user_id: int):
        if user_id in self.user_connections:
            del self.user_connections[user_id]

    async def send_to_user(self, user_id: int, message: dict):
        if user_id in self.user_connections:
            await self.user_connections[user_id].send_json(message)


manage = ConnectionManager()