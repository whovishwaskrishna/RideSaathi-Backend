from fastapi import WebSocket
from collections import defaultdict

class ConnectionManager:
    def __init__(self):
        self.route_connections = {}
        self.user_connections = {}

    async def connect_route(self, route_id: int, websocket):
        if route_id not in self.route_connections:
            self.route_connections[route_id] = set()
        self.route_connections[route_id].add(websocket)

    async def connect_user(self, user_id: int, websocket):
        self.user_connections[user_id] = websocket

    def disconnect_route(self, route_id: int, websocket):
        if route_id in self.route_connections:
            self.route_connections[route_id].discard(websocket)

    def disconnect_user(self, user_id: int):
        if user_id in self.user_connections:
            del self.user_connections[user_id]

    async def broadcast_route(self, route_id: int, message: dict):
        if route_id in self.route_connections:
            for connection in list(self.route_connections[route_id]):
                await connection.send_json(message)

    async def send_to_user(self, user_id: int, message: dict):
        if user_id in self.user_connections:
            await self.user_connections[user_id].send_json(message)


manage = ConnectionManager()