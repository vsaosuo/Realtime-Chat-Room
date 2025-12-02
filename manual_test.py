from client import ChatClient
import asyncio
import json
import argparse
import sys

async def handle_user_input(client):
    """Handle keyboard input from the user."""
    loop = asyncio.get_event_loop()
    
    print("SESSION ONLINE\n- Type your message and press Enter. \n- Type 'quit' to exit and 'leave' to leave the room.")
    print(f"----------------------------------")
    while True:
        # Read input asynchronously (non-blocking)
        line = await loop.run_in_executor(None, sys.stdin.readline)
        line = line.strip()
        
        if not line:
            continue
        
        if line.lower() == 'quit':
            print("Exiting chat...")
            break
        elif line.lower() == 'leave':
            await client.leave_room()
        else:
            await client.send_message(line)
            print(f"< You: {line}")

async def handle_incoming_messages(client):
    """Handle incoming messages from the server."""
    try:
        async for msg in client.read_messages():
            msg = json.loads(msg)
            if msg.get("body"):
                # For client messages which contain 'body'
                print(f"> {msg.get('from', 'server')}: {msg.get('body')}")
            else:
                # For server message status updates without 'body'
                print(f"> {msg.get('from', 'server')}: {msg.get('message', msg)}")
    except Exception as e:
        print(f"Connection closed: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chat client test")
    parser.add_argument("--join", type=str, help="Room ID to join")
    args = parser.parse_args()

    async def test_client():
        client = ChatClient("ws://localhost:8765", log_level='NONE')
        client_id = await client.connect()

        if args.join:
            # Join an existing room
            response = await client.join_room(args.join)
        else:
            # Create a new room
            room_id = await client.create_room("Test Room")
        print(f"----------------------------------")
        print(f"CONNECTION INFO \n- Client ID: {client_id}\n- Room ID: {room_id if not args.join else args.join}\n\n")

        # Run both input handler and message receiver concurrently
        input_task = asyncio.create_task(handle_user_input(client))
        receive_task = asyncio.create_task(handle_incoming_messages(client))
        
        # Wait for either task to complete (user quits or connection closes)
        done, pending = await asyncio.wait(
            [input_task, receive_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Cancel remaining tasks
        for task in pending:
            task.cancel()
        
    asyncio.run(test_client())
