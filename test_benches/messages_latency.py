"""
Messaging Latency Test Benchmark

This benchmark measures the round-trip latency of message delivery in the chat server.
It creates multiple clients that join a room and send messages at a configured rate.
Latency is measured by embedding timestamps in message bodies (Approach C).

Test Phases:
1. Setup: Create room, connect all participants
2. Execution: Send messages at configured rate, record latencies
3. Cooldown: Stop sending, drain remaining messages
4. Analysis: Calculate and report latency statistics
"""

import asyncio
import json
import time
import sys
import pandas as pd
from dataclasses import dataclass, field
from typing import List

# Add parent directory to path to import client module
sys.path.insert(0, '..')
from client import ChatClient


# =============================================================================
# Configuration
# =============================================================================

SERVER_URI = "ws://localhost:8765"
ROOM_NAME = "testing-latency-room"
NUM_CLIENTS = 4
MESSAGES_PER_SECOND = 30
TEST_DURATION_SECONDS = 60


# =============================================================================
# Data Collection
# =============================================================================

@dataclass
class LatencyRecord:
    """Single latency measurement."""
    msg_id: str
    sender_id: str
    receiver_id: str
    send_time: float
    receive_time: float
    
    @property
    def latency_ms(self) -> float:
        return (self.receive_time - self.send_time) * 1000


# Shared list to collect all latency records (thread-safe with asyncio)
latency_records: List[LatencyRecord] = []


# =============================================================================
# Setup Phase: Create room and join all participants
# =============================================================================

async def setup_room(num_clients: int) -> tuple[str, list[ChatClient]]:
    """
    Create a room and have all clients join.
    
    Args:
        num_clients: Number of clients to create and join
        
    Returns:
        Tuple of (room_id, list of connected ChatClient instances)
    """
    clients = []
    room_id = None
    
    for i in range(num_clients):
        # Create and connect client
        client = ChatClient(SERVER_URI, log_level='NONE')
        client_id = await client.connect()
        print(f"[Setup] Client {i+1}/{num_clients} connected (ID: {client_id})")
        
        if i == 0:
            # First client creates the room
            room_id = await client.create_room(ROOM_NAME)
            print(f"[Setup] Room created: {room_id}")
        else:
            # Other clients join the room
            await client.join_room(room_id)
            print(f"[Setup] Client {i+1} joined room {room_id}")
        
        clients.append(client)
    
    print(f"[Setup] Complete! {num_clients} clients in room {room_id}")
    return room_id, clients

# =============================================================================
# Latency Analysis Tasks
# =============================================================================
def determine_dropped_messages(received_records: List[LatencyRecord]) -> bool:
    """
    Determine if any messages were dropped based on received latency records.
    
    Args:
        received_records: List of LatencyRecord instances received.
    Returns:
        True if any messages were dropped, False otherwise.
    """
    # Group by receiver
    records_by_receiver = {}
    for record in received_records:
        records_by_receiver.setdefault(record.receiver_id, []).append(record)
    
    # Check for missing messages per receiver
    dropped = False
    message_id_commonly_dropped = set()
    for receiver_id, records in records_by_receiver.items():
        sent_msg_ids = set(r.msg_id for r in records)
        expected_msg_ids = set(f"test-{i}" for i in range(TEST_DURATION_SECONDS * MESSAGES_PER_SECOND))
        
        missing_msg_ids = expected_msg_ids - sent_msg_ids
        if missing_msg_ids:
            if not dropped:
                print(f"\n*** Determining Dropped Messages ***")

            print(f"[Analysis] Receiver {receiver_id} missing {len(missing_msg_ids)} messages")
            dropped = True
            message_id_commonly_dropped.update(missing_msg_ids)
    if dropped:
        print(f"[Analysis] Commonly dropped message IDs: {sorted(message_id_commonly_dropped)}")
    return dropped

# =============================================================================
# Listener Task: One per user to receive messages and compute latency
# =============================================================================

async def listener_task(client: ChatClient, client_index: int, stop_event: asyncio.Event):
    """
    Listener task for a single user. Receives messages and computes latency.
    
    Args:
        client: The ChatClient instance for this user
        client_index: Index of this client (for logging)
        stop_event: Event to signal when to stop listening
    """
    receiver_id = client.client_id
    
    try:
        async for message in client.read_messages():
            # Check if we should stop
            if stop_event.is_set():
                break
            
            # Parse the message
            try:
                msg = json.loads(message)
                body = msg.get("body")
                
                # Check if this is a test message with embedded timestamp
                if isinstance(body, str):
                    try:
                        body = json.loads(body)
                    except json.JSONDecodeError:
                        continue  # Not a JSON body, skip
                
                if body and "send_time" in body:
                    receive_time = time.time()
                    
                    # Create latency record
                    record = LatencyRecord(
                        msg_id=body.get("msg_id", "unknown"),
                        sender_id=body.get("sender_id", msg.get("from", "unknown")),
                        receiver_id=receiver_id,
                        send_time=body["send_time"],
                        receive_time=receive_time
                    )
                    
                    latency_records.append(record)
                    print(f"[Client {client_index}] Received msg {record.msg_id} | Latency: {record.latency_ms:.2f}ms")
                    
            except json.JSONDecodeError:
                continue  # Skip non-JSON messages
                
    except Exception as e:
        if not stop_event.is_set():
            print(f"[Client {client_index}] Listener error: {e}")


# =============================================================================
# Main Entry Point
# =============================================================================

async def main():
    """Main entry point for the latency test."""
    print(f"\n{'='*50}")
    print(f"  Latency Test - Parameters")
    print(f"{'='*50}\n")
    print(f"Server URI: {SERVER_URI}")
    print(f"Room Name: {ROOM_NAME}")
    print(f"Number of Clients: {NUM_CLIENTS}")
    print(f"Messages per Second: {MESSAGES_PER_SECOND}")
    print(f"Test Duration (seconds): {TEST_DURATION_SECONDS}")

    print(f"\n{'='*50}")
    print(f"  Latency Test - Setup Phase")
    print(f"{'='*50}\n")
    
    # Setup: Create room and join all clients
    room_id, clients = await setup_room(NUM_CLIENTS)
    
    print(f"\nRoom ID: {room_id}")
    print(f"Connected clients: {len(clients)}")
    
    # Phase 2 - Execution: Start listener tasks for each user
    print(f"\n{'='*50}")
    print(f"  Starting Listener Tasks")
    print(f"{'='*50}\n")
    
    stop_event = asyncio.Event()
    listener_tasks = []
    
    # Create a listener task for each client
    for i, client in enumerate(clients):
        task = asyncio.create_task(listener_task(client, i, stop_event))
        listener_tasks.append(task)
    
    print(f"[Execution] {len(listener_tasks)} listener tasks started")
    
    # TODO: Add sender tasks to send messages with timestamps
    # For now, let's do a simple test - have client 0 send a few messages
    delay_time = 1.0 / MESSAGES_PER_SECOND
    num_messages = TEST_DURATION_SECONDS * MESSAGES_PER_SECOND
    print(f"\n[Test] Sending test messages from client 0...")
    for msg_num in range(num_messages):
        test_message = json.dumps({
            "msg_id": f"test-{msg_num}",
            "sender_id": clients[0].client_id,
            "send_time": time.time(),
            "payload": f"Test message {msg_num}"
        })
        await clients[0].send_message(test_message)
        await asyncio.sleep(delay_time)
    
    # Wait a bit for messages to be received
    await asyncio.sleep(30)
    
    # Signal listeners to stop
    stop_event.set()
    
    # Cancel listener tasks
    for task in listener_tasks:
        task.cancel()
    
    # Wait for tasks to complete
    await asyncio.gather(*listener_tasks, return_exceptions=True)
    
    # Phase 4 - Analysis: Print results
    print(f"\n{'='*50}")
    print(f"  Results")
    print(f"{'='*50}\n")
    
    # export results to CSV
    data_frame = pd.DataFrame([r.__dict__ for r in latency_records])
    print(data_frame.head())
    data_frame.to_csv("data/latency_results.csv", index=False)

    # Determine dropped messages
    dropped = determine_dropped_messages(latency_records)

    if latency_records:
        latencies = [r.latency_ms for r in latency_records]
        print(f"Total messages received: {len(latency_records)}")
        print(f"Min latency: {min(latencies):.2f}ms")
        print(f"Max latency: {max(latencies):.2f}ms")
        print(f"Avg latency: {sum(latencies)/len(latencies):.2f}ms")
        print(f"Dropped messages detected: {'Yes' if dropped else 'No'}")
    else:
        print("No latency records collected.")
    
    
    # Cleanup
    print(f"\n[Cleanup] Disconnecting clients...")
    for i, client in enumerate(clients):
        await client.leave_room()
    print(f"[Cleanup] Done!")

if __name__ == "__main__":
    asyncio.run(main())
