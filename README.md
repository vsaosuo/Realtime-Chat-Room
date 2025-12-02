# Chat Server (Python)

A simple WebSocket-based chat server and client implementation in Python. This project allows multiple clients to connect, create/join rooms, and exchange messages in real-time.

## Project Structure

```
├── server.py          # WebSocket chat server
├── client.py          # Chat client library
├── manual_test.py     # Interactive CLI chat client example
├── logger.py          # Logging utility
└── test_benches/      # Performance testing scripts
    ├── messages_latency.py   # Latency benchmark test
    └── data/                 # Test results and data
```

## Getting Started

### Prerequisites

- Python 3.8+
- `websockets` library

Install dependencies:
```bash
pip install websockets pandas
```

### Running the Server

Start the chat server on `localhost:8765`:

```bash
python server.py
```

## Components

### Chat Server (`server.py`)

The server handles:
- Client connections with unique IDs
- Room creation and management
- Joining/leaving rooms
- Broadcasting messages to room participants

**Message Protocol:**
```json
{"action": "create|join|leave|message", "body": "..."}
```

### Chat Client (`client.py`)

A `ChatClient` class providing:
- `connect()` - Connect to the server
- `create_room(name)` - Create a new chat room
- `join_room(room_id)` - Join an existing room
- `leave_room()` - Leave the current room
- `send_message(text)` - Send a message to the room
- `read_messages()` - Async generator for incoming messages

### Interactive Example (`manual_test.py`)

A CLI chat client for manual testing:

```bash
# Create a new room
python manual_test.py

# Join an existing room
python manual_test.py --join <room_id>
```

Commands:
- Type a message and press Enter to send
- `leave` - Leave the current room
- `quit` - Exit the client

## Testing

### Latency Benchmark

Run the message latency test to measure server performance:

```bash
cd test_benches
python messages_latency.py
```

Or use the helper script to save results:
```bash
cd test_benches
./execute_and_save.sh messages_latency.py data
```

The benchmark tests:
- Multiple concurrent clients
- Message throughput at configurable rates
- Round-trip latency measurements
- Dropped message detection

Results are saved to `test_benches/data/`.
