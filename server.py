import asyncio
import json
import uuid
from datetime import datetime
from websockets.asyncio.server import serve
from logger import Logger

# Initialize logger (can be changed to 'INFO' or 'NONE')
logger = Logger('INFO')

# In-memory storage for connected clients and chat rooms
# clients stores websocket connections of each client, it follows the structure: 
# {client_id: websocket_connection}
clients = {}

# rooms stores rooms information, it follows the structure: 
# {
#   room_id: {
#       "clients": set([client_id1, client_id2, ...]), 
#       "metadata": {
#           "name": "Room Name", 
#           "created_at": "timestamp", 
#           ...}
#   }
# }
rooms = {}

# client_rooms tracks which room each client is in
# {client_id: room_id}
client_rooms = {}

# SETUP NOTE
# This server is designed to handle multiple chat rooms. Each client can join a specific room,
# and messages will be broadcast only to clients within the same room.
# The server maintains a mapping of clients to rooms and ensures that messages are routed correctly.
# 
# Each message from a client should include the follows the format:
# {"client_id": "string", "action": "create/join/leave/message", "body": "string or room_id"}

def create_room(client_id, room_name):
    """Create a new room and add the creator to it."""
    room_id = str(uuid.uuid4())[:8]  # Short unique ID
    rooms[room_id] = {
        "clients": set([client_id]),
        "metadata": {
            "name": room_name,
            "created_at": datetime.now().isoformat(),
            "created_by": client_id
        }
    }
    client_rooms[client_id] = room_id
    logger.info(f"Room '{room_name}' created with ID: {room_id} by client {client_id}")
    logger.debug(f"Room metadata: {rooms[room_id]['metadata']}")
    return {"status": "success", "room_id": room_id, "message": f"Room '{room_name}' created"}

def join_room(client_id, room_id):
    """Add a client to a room."""
    if room_id not in rooms:
        logger.debug(f"Client {client_id} tried to join non-existent room: {room_id}")
        return {"status": "error", "message": f"Room {room_id} does not exist"}
    
    # Leave current room if in one
    if client_id in client_rooms:
        logger.debug(f"Client {client_id} leaving current room before joining new one")
        leave_room(client_id)
    
    rooms[room_id]["clients"].add(client_id)
    client_rooms[client_id] = room_id
    room_name = rooms[room_id]["metadata"]["name"]
    logger.info(f"Client {client_id} joined room '{room_name}' ({room_id})")
    logger.debug(f"Room {room_id} now has {len(rooms[room_id]['clients'])} clients")
    return {"status": "success", "message": f"Joined room '{room_name}'", "room_id": room_id}

def leave_room(client_id):
    """Remove a client from their current room."""
    if client_id not in client_rooms:
        logger.debug(f"Client {client_id} tried to leave but is not in any room")
        return {"status": "error", "message": "Not in any room"}
    
    room_id = client_rooms[client_id]
    if room_id in rooms:
        rooms[room_id]["clients"].discard(client_id)
        # Clean up empty rooms
        if len(rooms[room_id]["clients"]) == 0:
            room_name = rooms[room_id]["metadata"]["name"]
            del rooms[room_id]
            logger.info(f"Room '{room_name}' ({room_id}) deleted (empty)")
    
    del client_rooms[client_id]
    logger.info(f"Client {client_id} left room {room_id}")
    return {"status": "success", "message": "Left room"}

async def broadcast_to_room(client_id, message_body):
    """Broadcast a message to all clients in the same room."""
    if client_id not in client_rooms:
        logger.debug(f"Client {client_id} tried to send message but is not in any room")
        return {"status": "error", "message": "You must join a room first"}
    
    room_id = client_rooms[client_id]
    if room_id not in rooms:
        logger.debug(f"Client {client_id}'s room {room_id} no longer exists")
        return {"status": "error", "message": "Room no longer exists"}
    

    # NOTE: Moderator module can be added here to filter or log messages
    # TODO: Implement message moderation
    # banded_words = ['shit', 'stupid', 'shutup', 'olo']  # Example banned words
    # if any(bad_word in message_body.lower() for bad_word in banded_words):
    #     logger.info(f"Message from {client_id} filtered due to inappropriate content")
    #     logger.debug(f"Original message: {message_body[:100]}")
    #     message_body = "[Message removed due to inappropriate content]"
    # await asyncio.sleep(0.01)  # Small delay to simulate processing @ 10ms

    # Get all clients in the room except the sender
    room_clients = rooms[room_id]["clients"] - {client_id}
    
    # Send message to all clients in the room
    message_data = json.dumps({
        "from": client_id,
        "body": message_body,
    })

    logger.debug(f"Broadcasting message from {client_id} to {len(room_clients)} clients in room {room_id}")
    logger.debug(f"Message content: {message_body[:50]}{'...' if len(message_body) > 50 else ''}")
    
    await asyncio.gather(
        *[clients[cid].send(message_data) for cid in room_clients if cid in clients],
        return_exceptions=True
    )
    
    logger.debug(f"Message broadcast completed for client {client_id}")
    return {"status": "success", "message": "Message sent"}

async def action_handlers(client_id, message):
    """Define action handlers for different message types."""
    
    logger.debug(f"Received message from client {client_id}: {message[:100]}{'...' if len(message) > 100 else ''}")
    
    # Parse for JSON message
    try:
        data = json.loads(message)
        action = data.get("action")
        body = data.get("body")

        logger.debug(f"Parsed action: {action}, body type: {type(body).__name__}")

        if action not in ["create", "join", "leave", "message"]:
            logger.debug(f"Invalid action '{action}' from client {client_id}")
            return {"status": "error", "message": "Invalid action"}
        
        if action == "create":
            return create_room(client_id, body)
        elif action == "join":
            return join_room(client_id, body.get("room_id") if body else None)
        elif action == "leave":
            return leave_room(client_id)
        elif action == "message":
            return await broadcast_to_room(client_id, body)
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error from client {client_id}: {e}")
        return {"status": "error", "message": "Invalid JSON format"}
    except Exception as e:
        logger.error(f"Server error handling message from {client_id}: {e}")
        return {"status": "error", "message": f"Server error: {str(e)}"}

async def handle_connection(websocket):
    # Generate a unique client ID for this connection
    client_id = str(uuid.uuid4())[:8]
    clients[client_id] = websocket
    logger.info(f"New client connected: {client_id}. Total clients: {len(clients)}")
    logger.debug(f"Client {client_id} websocket info: {websocket.remote_address}")
    
    # Send welcome message with client ID
    await websocket.send(json.dumps({
        "status": "connected",
        "client_id": client_id,
        "message": "Welcome!"
    }))
    logger.debug(f"Sent welcome message to client {client_id}")

    try:
        async for message in websocket:
            # Handle the message and get response
            response = await action_handlers(client_id, message)
            
            # Send response back to the client
            if response:
                await websocket.send(json.dumps(response))
                logger.debug(f"Sent response to client {client_id}: {response.get('status')}")
                
    except Exception as e:
        logger.error(f"Error handling connection for {client_id}: {e}")
        logger.debug(f"Exception details: {type(e).__name__}: {e}")
    finally:
        # Clean up when client disconnects
        if client_id in client_rooms:
            leave_room(client_id)
        if client_id in clients:
            del clients[client_id]
        logger.info(f"Client {client_id} disconnected. Total clients: {len(clients)}")
        
async def main():
    logger.info("Starting chat server on localhost:8765")
    async with serve(handle_connection, "localhost", 8765, max_queue=None) as server:
        logger.info("Server started successfully")
        await server.serve_forever()
    
if __name__ == "__main__":
    asyncio.run(main())