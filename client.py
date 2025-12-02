"""Client module for connecting to the server."""
import asyncio
from websockets.asyncio.client import connect
import json
from enum import Enum

class LogLevel(Enum):
    """Log level enumeration."""
    NONE = 0
    INFO = 1
    DEBUG = 2


class ChatClient:
    def __init__(self, uri, log_level='DEBUG'):
        self.uri = uri
        self.client_id = None
        self._set_log_level(log_level)

    def _set_log_level(self, level):
        """Set the logging level."""
        if isinstance(level, LogLevel):
            self.log_level = level
        elif isinstance(level, str):
            level_map = {
                'DEBUG': LogLevel.DEBUG,
                'INFO': LogLevel.INFO,
                'NONE': LogLevel.NONE,
                None: LogLevel.NONE
            }
            self.log_level = level_map.get(level.upper() if level else None, LogLevel.DEBUG)
        else:
            self.log_level = LogLevel.NONE

    def _log(self, message, level=LogLevel.DEBUG):
        """Log a message if the current log level permits."""
        if self.log_level.value >= level.value:
            print(message)

    async def connect(self):
        """
        Connect to the server and retrieve client ID.
        Return the client ID upon successful connection.
        """
        self._log(f"Attempting to connect to {self.uri}...", LogLevel.DEBUG)
        self.websocket = await connect(self.uri)
        welcome_message = await self.websocket.recv()
        self._log(f"Connected to server: {welcome_message}", LogLevel.DEBUG)

        msg = json.loads(welcome_message)
        if msg.get("status") == "connected":
            self.client_id = msg.get("client_id")
            self._log(f"Assigned client ID: {self.client_id}", LogLevel.INFO)
            return self.client_id
        else:
            raise Exception("Failed to connect to server")
    
    async def create_room(self, room_name):
        """
        Create a new chat room. 
        Return the room ID upon successful creation.
        """
        request = {
            "action": "create",
            "body": {
                "room_name": room_name
            }
        }

        self._log(f"Sending create room request: {request}", LogLevel.DEBUG)
        await self.websocket.send(json.dumps(request))
        response = await self.websocket.recv()
        msg = json.loads(response)

        if msg.get("status") != "success":
            raise Exception(f"Failed to create room: {msg.get('message')}")
        
        self.roomId = msg.get("room_id")

        self._log(f"Create room response: {response}", LogLevel.DEBUG)
        self._log(f"Room created with ID: {self.roomId}", LogLevel.INFO)
        return self.roomId
    
    async def join_room(self, room_id):
        """Join an existing chat room."""
        request = {
            "action": "join",
            "body": {
                "room_id": room_id
            }
        }

        self._log(f"Sending join room request: {request}", LogLevel.DEBUG)
        await self.websocket.send(json.dumps(request))
        response = await self.websocket.recv()
        msg = json.loads(response)
        if msg.get("status") != "success":
            raise Exception(f"Failed to join room: {msg.get('message')}")
        
        self.roomId = room_id
        self._log(f"Join room response: {response}", LogLevel.DEBUG)
        self._log(f"Joined room: {room_id}", LogLevel.INFO)
        return json.loads(response)
    
    async def leave_room(self):
        """Send leave room request (fire and forget)."""
        request = {
            "action": "leave",
            "body": {}
        }
        self._log(f"Sending leave room request", LogLevel.DEBUG)
        await self.websocket.send(json.dumps(request))
        self._log(f"Left room", LogLevel.INFO)
    
    async def send_message(self, message_text):
        """Send a message to the current chat room (fire and forget)."""
        request = {
            "action": "message",
            "body": message_text
        }

        self._log(f"Sending message: {message_text}", LogLevel.DEBUG)
        await self.websocket.send(json.dumps(request))

    
    async def read_messages(self):       
        """Continuously read messages from the server as an async generator. These messages are client messages who are connected to the room."""
        try:
            async for message in self.websocket:
                self._log(f"Received message: {message}", LogLevel.DEBUG)
                yield message
        except Exception as e:
            self._log(f"Error reading messages: {e}", LogLevel.INFO)
