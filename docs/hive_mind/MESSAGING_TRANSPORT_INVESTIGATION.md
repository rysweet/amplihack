# Messaging Transport Investigation: Hive Mind Distributed Architecture

**Branch:** `feat/distributed-hive-mind`
**Date:** 2026-03-07
**Status:** Complete

---

## Executive Summary

This document captures research and recommendations for the messaging transport layer of the distributed hive mind architecture. After analyzing the existing codebase, comparing Azure Event Hubs vs Service Bus, evaluating abstraction libraries (Dapr, CloudEvents), and verifying the provisioned Azure infrastructure, the **recommendation is:**

- **Primary transport: Azure Service Bus Premium** (already provisioned; already used in codebase)
- **Abstraction layer: Dapr pub/sub** (optional, for future cloud-portability)
- **Event schema: CloudEvents v1.0** (via Dapr automatically, or manually via `BusEvent.to_json()`)
- **Secondary transport: Azure Event Hubs** (for telemetry streams and broadcast replay)

---

## 1. Existing Transport Layer in Haymaker Repo

### Architecture Overview

The distributed hive mind already has a **transport-agnostic event bus** in place with three backend implementations:

| Backend                   | File                                                       | Use Case                |
| ------------------------- | ---------------------------------------------------------- | ----------------------- |
| `LocalEventBus`           | `src/amplihack/agents/goal_seeking/hive_mind/event_bus.py` | Testing, single-machine |
| `AzureServiceBusEventBus` | same                                                       | Production on Azure     |
| `RedisEventBus`           | same                                                       | Low-latency dev/staging |

**Factory function:**

```python
from amplihack.agents.goal_seeking.hive_mind.event_bus import create_event_bus

bus = create_event_bus(
    backend="azure",          # "local" | "azure" | "redis"
    connection_string="...",  # Service Bus conn str
    topic_name="hive-graph",  # Default topic
)
```

### Core Abstractions

**`BusEvent` (immutable data model):**

```python
@dataclass(frozen=True)
class BusEvent:
    event_id: str       # UUID4 hex
    event_type: str     # FACT_LEARNED, QUERY, SEARCH_QUERY, etc.
    source_agent: str   # Originating agent ID
    timestamp: float    # Unix epoch
    payload: dict       # Event-specific data
```

**`EventBus` Protocol (transport interface):**

```python
class EventBus(Protocol):
    def publish(self, event: BusEvent) -> None: ...
    def subscribe(self, agent_id: str, event_types: list[str] | None = None) -> None: ...
    def unsubscribe(self, agent_id: str) -> None: ...
    def poll(self, agent_id: str) -> list[BusEvent]: ...
    def close(self) -> None: ...
```

### Service Bus Implementation Details

The `AzureServiceBusEventBus` backend uses:

- **Topic:** `hive-graph` (configurable via `topic_name` kwarg)
- **Per-agent subscriptions:** `agent-{i}` — one subscription per agent
- **SQL filter rules:** Server-side filtering by `event_type` on each subscription
- **Dead-lettering:** Malformed messages are automatically dead-lettered
- **Peek-lock:** Messages locked during processing (5s max wait per poll)
- **Message completion:** Automatic after successful deserialization
- **Tier used:** **Premium** (1 capacity unit) per `main.bicep`

### Transport Configuration

Transport is selected via environment variables (or explicit kwargs):

```bash
AMPLIHACK_MEMORY_TRANSPORT=azure_service_bus       # "local" | "redis" | "azure_service_bus"
AMPLIHACK_MEMORY_CONNECTION_STRING=Endpoint=sb://...
AMPLIHACK_MEMORY_TOPOLOGY=distributed
AMPLIHACK_MEMORY_BACKEND=cognitive
```

### Event Types Published

| Event Type                      | Direction | Purpose                               |
| ------------------------------- | --------- | ------------------------------------- |
| `network_graph.create_node`     | broadcast | Replicate node creation to all agents |
| `network_graph.create_edge`     | broadcast | Replicate edge creation to all agents |
| `network_graph.search_query`    | fan-out   | Request knowledge from peer agents    |
| `network_graph.search_response` | reply     | Return search results to requester    |
| `QUERY`                         | fan-out   | Ask hive a question (OODA loop)       |
| `QUERY_RESPONSE`                | reply     | Answer hive query                     |
| `LEARN_CONTENT`                 | broadcast | Notify agents of new learned content  |

### Transport Layer File Map

```
src/amplihack/agents/goal_seeking/hive_mind/
├── event_bus.py              # EventBus protocol + 3 backend implementations
├── distributed_hive_graph.py # DHT-sharded hive graph (local bus only)
├── hive_graph.py             # HiveGraph protocol (abstract)
├── dht.py                    # Consistent hashing (HashRing, DHTRouter)
├── gossip.py                 # Bloom-filter gossip for convergence
└── controller.py             # Multi-hive orchestration

src/amplihack/memory/
├── network_store.py          # NetworkGraphStore: wraps GraphStore + event bus
├── facade.py                 # Memory: high-level API used by OODA loop
└── config.py                 # MemoryConfig: transport selection + env vars

deploy/azure_hive/
├── main.bicep                # IaC: Service Bus Premium + Container Apps
└── agent_entrypoint.py       # OODA loop: observe/orient (events) + act
```

---

## 2. Event Hubs vs Service Bus: Comparison

### Feature Matrix

| Feature                 | Azure Event Hubs                                              | Azure Service Bus                                |
| ----------------------- | ------------------------------------------------------------- | ------------------------------------------------ |
| **Model**               | Append-only log (Kafka-like)                                  | Message broker (AMQP)                            |
| **Fan-out / Broadcast** | Excellent — consumer groups read independently                | Via topics + subscriptions (up to 2,000 subs)    |
| **Competing consumers** | Complex — requires partition coordination                     | Native — queue peek-lock                         |
| **Message replay**      | Yes — rewind to any offset in retention window                | No — messages deleted on consumption             |
| **Ordering guarantee**  | Per-partition FIFO only                                       | Per-session FIFO (sessions), else best-effort    |
| **Dead-letter queue**   | Not native — must implement in app code                       | Built-in DLQ on every queue and subscription     |
| **Request/Reply (RPC)** | Not supported                                                 | Native — `ReplyTo` + `ReplyToSessionId`          |
| **Per-message routing** | No server-side filter rules                                   | SQL filter rules on subscriptions                |
| **Duplicate detection** | None at service layer                                         | Configurable window per entity                   |
| **Transactions**        | None                                                          | Multi-entity atomic transactions                 |
| **Message size**        | Up to 1 MB (Standard), higher on Premium                      | 256 KB (Standard), up to 100 MB (Premium)        |
| **Throughput ceiling**  | Millions/sec (horizontal via partitions)                      | High but not extreme — reliability first         |
| **Retention**           | 1–7 days (Standard), up to 90 days (Premium)                  | Until consumed or TTL expires                    |
| **Pricing (base)**      | Throughput Units / Processing Units                           | Per operation (Standard) or per MU-day (Premium) |
| **Dapr support**        | `pubsub.azure.eventhubs` (needs Blob Storage for checkpoints) | `pubsub.azure.servicebus.topics` (first-class)   |

### Pattern Suitability for Hive Mind

| Communication Pattern                          | Hive Mind Use                  | Best Fit                                               |
| ---------------------------------------------- | ------------------------------ | ------------------------------------------------------ |
| Fan-out: broadcast LEARN_CONTENT to all agents | All agents receive new facts   | **Event Hubs** (consumer groups) or Service Bus topics |
| Fan-out search query to peer agents            | `network_graph.search_query`   | Service Bus topics + filter subs                       |
| Request/reply: `QUERY` → `QUERY_RESPONSE`      | Agent asks hive a question     | **Service Bus** sessions                               |
| Competing-consumer task dispatch               | Agent pool picks up work items | **Service Bus** queues                                 |
| Dead-letter poisoned events                    | Malformed `BusEvent`           | **Service Bus** built-in DLQ                           |
| Replay for new agent types bootstrapping       | New agent reads full history   | **Event Hubs**                                         |
| Telemetry / observability streams              | High-volume agent logs/metrics | **Event Hubs**                                         |
| Ordered multi-step task chains                 | OODA tick ordering per agent   | **Service Bus** sessions                               |

### Recommendation

**Service Bus is the primary transport for inter-agent coordination.** It directly supports the hive mind's key patterns: fan-out search queries, request/reply queries, dead-lettering, and per-subscription SQL filters. The existing code already implements this correctly.

**Event Hubs should be used as a secondary stream** for telemetry, observability, and enabling new agent types to replay history. It is not a replacement for Service Bus in the hive mind's messaging patterns.

---

## 3. Abstraction Library Evaluation

### 3.1 Dapr Pub/Sub

**What it is:** A CNCF-graduated distributed runtime that abstracts messaging behind a sidecar HTTP/gRPC API. Applications call `localhost:3500/publish`; the sidecar handles the actual broker interaction.

**Dapr pub/sub with Service Bus:**

```yaml
# dapr/components/pubsub.yaml
apiVersion: dapr.io/v1alpha1
kind: Component
metadata:
  name: hive-pubsub
spec:
  type: pubsub.azure.servicebus.topics
  version: v1
  metadata:
    - name: connectionString
      secretKeyRef:
        name: sb-secret
        key: connectionString
```

**Agent code (before Dapr):**

```python
# Direct Azure SDK
sender = ServiceBusSender(conn_str, topic_name="hive-graph")
sender.send_messages(ServiceBusMessage(json.dumps(event.to_dict())))
```

**Agent code (after Dapr):**

```python
# Dapr sidecar — no Azure SDK
import httpx
httpx.post("http://localhost:3500/v1.0/publish/hive-pubsub/hive-graph",
           json=event.to_dict())
```

**Pros:**

- Transport portability: swap Service Bus for Kafka/Redis/RabbitMQ by changing one YAML
- Built-in at-least-once delivery regardless of backend capabilities
- Dead-letter topics managed by Dapr uniformly
- CloudEvents 1.0 envelope added automatically
- **Dapr Agents** (March 2025): virtual actor model purpose-built for multi-agent coordination
- Built-in distributed tracing (OpenTelemetry), metrics, and service-to-service encryption

**Cons:**

- Sidecar overhead: each agent pod needs a sidecar (adds ~50–200 MB RAM per agent)
- Local development requires `dapr run` or Docker Compose
- Dapr Agents is new (announced March 2025); production maturity is still evolving
- Adds operational surface: Dapr control plane (operator, sentry, placement) on Kubernetes
- The existing `EventBus` protocol already provides the same abstraction at the Python level

**Verdict:** Dapr is **recommended for future adoption** when the hive mind needs cloud-portability or Kubernetes-native deployment at scale. For the current Container Apps deployment backed by Service Bus, the existing `EventBus` protocol provides equivalent abstraction with no sidecar overhead. Migrate to Dapr when multi-cloud or on-prem portability becomes a requirement, or when adopting the Dapr Agents framework for actor-based state management.

### 3.2 CloudEvents Specification

**What it is:** A CNCF-graduated specification (v1.0, graduated January 2024) that standardizes the event envelope schema. It is **not** a transport or delivery system — purely a schema contract.

**Required CloudEvents fields:**

```json
{
  "specversion": "1.0",
  "id": "abc123",
  "source": "/agents/agent-0",
  "type": "com.amplihack.hive.fact_learned",
  "time": "2026-03-07T10:00:00Z",
  "datacontenttype": "application/json",
  "data": { ... }
}
```

**Relationship to existing `BusEvent`:**

```python
# Current BusEvent fields
@dataclass(frozen=True)
class BusEvent:
    event_id: str       # → CloudEvents "id"
    event_type: str     # → CloudEvents "type"
    source_agent: str   # → CloudEvents "source"
    timestamp: float    # → CloudEvents "time"
    payload: dict       # → CloudEvents "data"
```

`BusEvent` is structurally equivalent to a CloudEvents envelope. Adopting CloudEvents would require adding `specversion: "1.0"` and a URI `source` format — a minimal change.

**Azure support:**

- Service Bus: CloudEvents payloads supported natively (message body is schema-agnostic)
- Event Hubs: CloudEvents supported via Kafka protocol binding
- Event Grid: Native CloudEvents v1.0 as both input and output schema

**Dapr relationship:** Dapr automatically wraps all pub/sub messages in CloudEvents 1.0 format. Using Dapr means CloudEvents adoption is automatic.

**Verdict:** CloudEvents is **recommended as the standard event envelope** for all hive mind inter-agent messages. The migration from current `BusEvent` is minimal (add `specversion`, normalize `source` to a URI). If Dapr is adopted, CloudEvents compliance comes for free. If staying with the direct Service Bus SDK, add a CloudEvents serializer wrapper around `BusEvent.to_json()`.

### 3.3 Abstraction Comparison

| Dimension                | Dapr                     | CloudEvents                     | Existing EventBus Protocol |
| ------------------------ | ------------------------ | ------------------------------- | -------------------------- |
| **What it abstracts**    | Transport (which broker) | Schema (envelope format)        | Transport (which broker)   |
| **Language**             | Any (HTTP/gRPC sidecar)  | Any (JSON/binary spec)          | Python only                |
| **Overhead**             | Sidecar process per pod  | Zero (schema contract only)     | Zero                       |
| **Lock-in reduction**    | Full broker portability  | Interoperability across systems | Python-level portability   |
| **Production readiness** | High (CNCF graduated)    | High (CNCF graduated)           | Medium (internal only)     |
| **Already in use**       | No                       | No (but BusEvent is compatible) | Yes                        |

---

## 4. Provisioned Azure Infrastructure

### Premium Service Bus Namespace

A Premium Service Bus namespace is provisioned and active for the hive mind deployment:

| Property           | Value                                                            |
| ------------------ | ---------------------------------------------------------------- |
| **Namespace name** | `hive-sb-prem-dj2qo2w7vu5zi`                                     |
| **Resource group** | `hive-mind-rg`                                                   |
| **Location**       | East US                                                          |
| **SKU**            | Premium                                                          |
| **Capacity**       | 1 Messaging Unit                                                 |
| **Status**         | Active                                                           |
| **Endpoint**       | `https://hive-sb-prem-dj2qo2w7vu5zi.servicebus.windows.net:443/` |

This namespace is provisioned via `deploy/azure_hive/main.bicep` and matches the `AzureServiceBusEventBus` backend configuration in the code.

**Why Premium tier:**

- Dedicated resources (no noisy neighbors)
- Message size up to 100 MB (vs 256 KB on Standard)
- VNet integration for network isolation
- Flat pricing per messaging unit (predictable cost at scale)
- Required for production Container Apps deployment

### Existing Standard Namespace (staging/dev)

| Property           | Value                   |
| ------------------ | ----------------------- |
| **Namespace name** | `hive-sb-dj2qo2w7vu5zi` |
| **Resource group** | `hive-mind-rg`          |
| **Location**       | West US 2               |
| **SKU**            | Standard                |
| **Use**            | Development / staging   |

---

## 5. Recommendations Summary

### Immediate (current state is good)

1. **Keep Service Bus Premium as primary transport** — the existing `AzureServiceBusEventBus` implementation is correct and well-designed. No changes needed.

2. **Keep the `EventBus` protocol** — the three-backend design (`local`/`redis`/`azure`) provides the right abstraction for testing and production without sidecar overhead.

3. **Adopt CloudEvents schema for `BusEvent`** — add `specversion: "1.0"` and normalize `source_agent` to a URI (e.g., `/agents/{agent_id}`) in `BusEvent.to_json()`. This enables interoperability with Event Grid, external consumers, and future Dapr migration.

### Near-term

4. **Add Event Hubs for telemetry** — route agent metrics, OODA tick counts, and memory stats to an Event Hubs namespace for stream analytics and dashboarding via Azure Monitor / Stream Analytics.

5. **Evaluate Dapr Agents** — once Dapr Agents (March 2025) reaches GA stability, evaluate replacing the `NetworkGraphStore` background thread model with Dapr virtual actors. This would give durable state, retry, and multi-agent workflow orchestration.

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│  Azure Container Apps (hive mind agents)                            │
│                                                                     │
│  ┌───────────┐   ┌───────────┐   ┌───────────┐   ┌───────────┐    │
│  │  Agent-0  │   │  Agent-1  │   │  Agent-2  │   │  Agent-N  │    │
│  │  OODA     │   │  OODA     │   │  OODA     │   │  OODA     │    │
│  │  Memory   │   │  Memory   │   │  Memory   │   │  Memory   │    │
│  └─────┬─────┘   └─────┬─────┘   └─────┬─────┘   └─────┬─────┘   │
│        │               │               │               │           │
│  ┌─────▼───────────────▼───────────────▼───────────────▼─────┐    │
│  │              AzureServiceBusEventBus                       │    │
│  │  (EventBus Protocol → Topic: hive-graph)                   │    │
│  └─────────────────────────┬───────────────────────────────────┘   │
└────────────────────────────│────────────────────────────────────────┘
                             │ AMQP / Service Bus SDK
┌────────────────────────────▼────────────────────────────────────────┐
│  Azure Service Bus Premium  (hive-sb-prem-dj2qo2w7vu5zi, eastus)   │
│                                                                      │
│  Topic: hive-graph                                                   │
│  ├── Subscription: agent-0  [SQL filter: eventtype IN (...)]        │
│  ├── Subscription: agent-1  [SQL filter: eventtype IN (...)]        │
│  ├── ...                                                             │
│  └── Dead-letter queue (auto): malformed events                     │
└──────────────────────────────────────────────────────────────────────┘
                                                         ▲
                     Future: CloudEvents envelope        │
                     Future: Dapr sidecar abstraction   │
                     Future: Event Hubs telemetry sidecar
```

---

## 6. References

- [Azure Service Bus vs Event Hubs - Microsoft Learn](https://learn.microsoft.com/en-us/azure/service-bus-messaging/compare-messaging-services)
- [Service Bus Premium tier - Microsoft Learn](https://learn.microsoft.com/en-us/azure/service-bus-messaging/service-bus-premium-messaging)
- [Event Hubs features and tiers - Microsoft Learn](https://learn.microsoft.com/en-us/azure/event-hubs/compare-tiers)
- [Dapr pub/sub overview - Dapr Docs](https://docs.dapr.io/developing-applications/building-blocks/pubsub/pubsub-overview/)
- [Dapr AI Agents announcement - CNCF (March 2025)](https://www.cncf.io/blog/2025/03/12/announcing-dapr-ai-agents/)
- [CloudEvents v1.0 specification - GitHub](https://github.com/cloudevents/spec)
- [Hive Mind Architecture](./ARCHITECTURE.md)
- [Hive Mind Design](./DESIGN.md)
- Transport layer code: `src/amplihack/agents/goal_seeking/hive_mind/event_bus.py`
- Network store: `src/amplihack/memory/network_store.py`
- Azure IaC: `deploy/azure_hive/main.bicep`
