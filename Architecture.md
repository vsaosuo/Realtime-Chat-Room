# Chat Server Communication Documentation

## Overview
This is a **WebSocket-based multi-room chat server** built with Python's `asyncio` and `websockets` library. The server supports real-time communication between multiple clients organized into chat rooms.

---

## Architecture

### Connection Model
- **Protocol**: WebSocket (ws://)
- **Default Address**: `localhost:8765`
- **Connection Type**: Persistent bidirectional communication
- **Message Format**: JSON

### Data Structures

The server maintains three key in-memory data structures:

1. **`clients`**: Maps client IDs to WebSocket connections
   ```python
   {client_id: websocket_connection}
   ```

2. **`rooms`**: Stores room information and members
   ```python
   {
     room_id: {
       "clients": set([client_id1, client_id2, ...]),
       "metadata": {
         "name": "Room Name",
         "created_at": "timestamp",
         "created_by": "creator_client_id"
       }
     }
   }
   ```

3. **`client_rooms`**: Tracks which room each client is in
   ```python
   {client_id: room_id}
   ```

---

## Communication Flow

### 1. **Connection Phase**

```
Client                          Server
  |                               |
  |-------- WebSocket Connect --->|
  |                               |
  |<------ Welcome Message -------|
  |  {                            |
  |    "status": "connected",     |
  |    "client_id": "abc123",     |
  |    "message": "Welcome!"      |
  |  }                            |
```

- Server generates unique 8-character client ID (UUID-based)
- Client receives welcome message with assigned ID
- WebSocket connection persists for bidirectional communication

### 2. **Action Messages**

All client messages follow this JSON format:

```json
{
  "action": "create|join|leave|message",
  "body": {
    // Action-specific data
  }
}
```

#### Available Actions:

| Action | Body Format | Purpose |
|--------|-------------|---------|
| `create` | `"room_name"` (string) | Create a new chat room |
| `join` | `{"room_id": "string"}` | Join an existing room |
| `leave` | N/A | Leave current room |
| `message` | `"message_text"` (string) | Send message to room; client can also send message as JSON string which allows customed messaging format. |

### 3. **Response Format**

Server responses follow this structure:

```json
{
  "status": "success|error",
  "message": "Human-readable message",
  "room_id": "optional-room-id"
}
```

---

## Visual Communication Diagram

```
┌───────────────────────────────────────────────────────────────────┐
│                         CHAT SERVER (Port 8765)                   │
│                                                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │
│  │   clients    │  │    rooms     │  │client_rooms  │             │
│  │  {id: ws}    │  │{id: {data}}  │  │ {id: room}   │             │
│  └──────────────┘  └──────────────┘  └──────────────┘             │
│                                                                   │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │              handle_connection(websocket)                   │  │
│  │  • Assigns client_id                                        │  │
│  │  • Sends welcome message                                    │  │
│  │  • Processes incoming messages                              │  │
│  │  • Routes to action_handlers()                              │  │
│  └─────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────┘
                                │
                                │ WebSocket (JSON Messages)
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
┌───────────────┐      ┌───────────────┐      ┌───────────────┐
│  Client A     │      │  Client B     │      │  Client C     │
│  (ID: abc123) │      │  (ID: def456) │      │  (ID: ghi789) │
└───────────────┘      └───────────────┘      └───────────────┘
        │                       │                       │
        │                       │                       │
        └───────────────────────┴───────────────────────┘
                                │
                        Room "Test Room"
                          (ID: room001)
```

---

## Sequence Diagram: Message Broadcasting

```
Client A              Server                 Client B        Client C
   │                    │                       │               │
   │─── create room ───>│                       │               │
   │<─── room_id ───────│                       │               │
   │                    │<─── join room ────────│               │
   │                    │──── success ─────────>│               │
   │                    │<─────── join room ────────────────────│
   │                    │──── success ─────────────────────────>│
   │                    │                       │               │
   │─── message ───────>│                       │               │
   │<─── success ───────│                       │               │
   │                    │──── broadcast ───────>│               │
   │                    │──── broadcast ───────────────────────>│
   │                    │   {from: "abc123",    │               │
   │                    │    body: "Hello"}     │               │
```

---

## Detailed Flow Examples

### Example 1: Creating and Joining a Room

**Step 1: Client A creates a room**
```
Client A → Server:
{
  "action": "create",
  "body": "Game Night"
}

Server → Client A:
{
  "status": "success",
  "room_id": "a1b2c3d4",
  "message": "Room 'Game Night' created"
}
```

**Step 2: Client B joins the room**
```
Client B → Server:
{
  "action": "join",
  "body": {"room_id": "a1b2c3d4"}
}

Server → Client B:
{
  "status": "success",
  "message": "Joined room 'Game Night'",
  "room_id": "a1b2c3d4"
}
```

### Example 2: Broadcasting Messages

**Client A sends a message**
```
Client A → Server:
{
  "action": "message",
  "body": "Hello everyone!"
}

Server → Client A:
{
  "status": "success",
  "message": "Message sent"
}

Server → Client B (broadcast):
{
  "from": "abc123",
  "body": "Hello everyone!"
}
```

**Note**: The sender (Client A) does NOT receive their own message broadcast.

---

## Key Features

### 1. **Room Management**
- Rooms are created on-demand with unique 8-character IDs
- Rooms are automatically deleted when the last member leaves
- Each client can only be in one room at a time
- Joining a new room automatically leaves the previous room

### 2. **Message Broadcasting**
- Messages are sent to all room members except the sender
- Uses `asyncio.gather()` for concurrent delivery
- Exceptions during broadcast are caught and handled gracefully
- Includes timestamp and sender information

### 3. **Connection Lifecycle**
- Each connection gets a unique client ID
- Automatic cleanup on disconnect (leaves room, removes from clients dict)
- Persistent WebSocket connections for real-time communication

### 4. **Error Handling**
- JSON parsing errors
- Invalid actions
- Room not found
- Client not in room
- All errors return structured error responses

---

## Future Extension Points

The server includes placeholders for additional features:

```python
# NOTE: Moderator module can be added here to filter or log messages
# TODO: Implement message moderation
```

This architecture allows for easy integration of:
- **Content moderation** (filtering inappropriate messages)
- **Message logging** (storing chat history)
- **Rate limiting** (preventing spam)

---

## Technical Details

- **Language**: Python 3.7+
- **Key Libraries**: 
  - `websockets.asyncio.server` for WebSocket server
  - `asyncio` for asynchronous operations
  - `json` for message serialization
  - `uuid` for unique ID generation
- **Concurrency Model**: Async/await with event loop
- **State Management**: In-memory (not persistent across server restarts)
