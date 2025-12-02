# Message Latency Benchmark Report

## Overview

This experiment measures end-to-end message latency in a WebSocket chat server, from sender through the server to receivers.

**Source code:** `messages_latency.py`

## Methodology

Latency is measured by embedding timestamps in message bodies. The receiver computes the difference between receive time and send time for each message.

### Test Parameters

| Parameter | Value |
|-----------|-------|
| Clients | 4 |
| Messages per second | 30 |
| Test duration | 60 seconds |
| Total messages sent | 1,800 |
| Expected receives | 5,400 (1,800 × 3 receivers) |

### Treatments

Two independent variables were tested:
1. **Moderator delay**: None vs. 10ms simulated processing delay
2. **Queue size**: `max_queue=4` (small) vs. `max_queue=None` (unlimited)

---

## Results

| Treatment | Min (ms) | Max (ms) | Avg (ms) | Dropped |
|-----------|----------|----------|----------|---------|
| No moderator, unlimited queue | 0.34 | 26.04 | **1.87** | No |
| No moderator, small queue | 0.34 | 13.68 | **2.15** | No |
| 10ms moderator, unlimited queue | 10.53 | 30.80 | **13.66** | No |
| 10ms moderator, small queue | 10.84 | 30.92 | **13.70** | No |

All configurations received 5,400 messages with no drops.

---

## Analysis

### Effect of Moderator Delay
The 10ms moderator delay adds ~11-12ms to average latency, as expected. This confirms the delay is applied per-message during broadcast. Also note that with the builtin ```websocket``` queue mechanism, the message were queued in the memory and no messages were dropped.

### Effect of Queue Size
Queue size has minimal impact on average latency where unlimited queue size tend to yield better average latency.

### Key Observations
1. At 30 msg/s with 10ms processing, the server can handle the load without drops (theoretical max: 100 msg/s)
2. Small queues provide backpressure, preventing latency spikes from queue buildup
3. The moderator delay dominates latency when enabled (~10ms floor)

---

## Conclusion

For this workload, the average latency without a moderation model takes aboue 1.87ms at large queue. This is latency has little affects on the real time nature of the application, as it still less than 50ms standard. In general, the larger queue size tend to yield better performances, but finding the sweet-spot that balanced between memory usage and performance is something that future work could focus on.