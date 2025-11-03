from __future__ import annotations

from channels.generic.websocket import AsyncJsonWebsocketConsumer


class QuizConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.room_code = self.scope["url_route"]["kwargs"]["room_code"].upper()
        self.group_name = f"quiz_{self.room_code}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()
        await self.send_json({"event": "connected", "room_code": self.room_code})

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive_json(self, content, **kwargs):
        # Clients can send ping/pong or ack events if needed
        event = content.get("event")
        if event == "ping":
            await self.send_json({"event": "pong"})

    async def quiz_event(self, event):
        await self.send_json({"event": event["event"], "payload": event["payload"]})
