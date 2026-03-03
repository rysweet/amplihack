# pyright: reportMissingImports=false, reportOptionalMemberAccess=false
#!/usr/bin/env python3
"""Hive Mind Agent Runner -- Container entrypoint for Azure Container Apps.

Each container runs one LearningAgent with LLM-backed fact extraction and
answer synthesis. Configuration via environment variables:

    AGENT_ID              -- unique identifier (e.g. "biology_1")
    AGENT_DOMAIN          -- knowledge domain (e.g. "biology")
    SERVICE_BUS_CONN_STR  -- Azure Service Bus connection string
    DATA_DIR              -- mounted directory for the agent's Kuzu database
    ANTHROPIC_API_KEY     -- required for LLM operations
    EVAL_MODEL            -- model to use (default: claude-sonnet-4-5-20250929)

The agent:
  1. Starts a FastAPI server on :8080
  2. Creates a LearningAgent with CognitiveMemory (Kuzu DB) + shared hive
  3. /learn endpoint: LLM extracts facts from content, stores in Kuzu,
     auto-promotes to local hive, publishes to Service Bus
  4. /query endpoint: LLM synthesizes answer from local + hive facts
  5. Event bus polling thread receives facts from other agents into hive
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import time

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("agent_runner")

# ---------------------------------------------------------------------------
# Configuration from environment
# ---------------------------------------------------------------------------

AGENT_ID = os.environ.get("AGENT_ID", "unknown")
AGENT_DOMAIN = os.environ.get("AGENT_DOMAIN", "general")
SERVICE_BUS_CONN_STR = os.environ.get("SERVICE_BUS_CONN_STR", "")
DATA_DIR = os.environ.get("DATA_DIR", "/data")
EVAL_MODEL = os.environ.get("EVAL_MODEL", "claude-sonnet-4-5-20250929")

# Group for federated mode: agents only incorporate facts from same group.
_hive_group = ""

# ---------------------------------------------------------------------------
# Agent + Hive setup (lazy -- initialized at startup)
# ---------------------------------------------------------------------------

_agent = None  # LearningAgent
_hive = None  # InMemoryHiveGraph (receives facts from other agents via bus)
_event_bus = None


def _init_agent():
    """Initialize the LearningAgent with hive_store for distributed memory."""
    global _agent, _hive, _event_bus
    from pathlib import Path

    sys.path.insert(0, "/app/hive_mind_core")
    sys.path.insert(0, "/app")
    from event_bus import create_event_bus
    from hive_graph import InMemoryHiveGraph

    # Local hive receives facts from other agents via event bus
    _hive = InMemoryHiveGraph(hive_id=f"hive-{AGENT_ID}")
    _hive.register_agent(AGENT_ID, domain=AGENT_DOMAIN)

    # LearningAgent with Kuzu DB + hive_store
    # CognitiveAdapter.search() merges local Kuzu + hive facts
    # CognitiveAdapter.store_fact() auto-promotes to hive
    from amplihack.agents.goal_seeking.learning_agent import LearningAgent

    storage_path = Path(DATA_DIR) / AGENT_ID
    storage_path.mkdir(parents=True, exist_ok=True)

    _agent = LearningAgent(
        agent_name=AGENT_ID,
        model=EVAL_MODEL,
        storage_path=storage_path,
        use_hierarchical=True,
        hive_store=_hive,
    )
    logger.info(
        "LearningAgent initialized: agent=%s domain=%s model=%s",
        AGENT_ID,
        AGENT_DOMAIN,
        EVAL_MODEL,
    )

    # Connect event bus
    if SERVICE_BUS_CONN_STR:
        _event_bus = create_event_bus(
            "azure",
            connection_string=SERVICE_BUS_CONN_STR,
            topic_name="hive-events",
        )
        _event_bus.subscribe(AGENT_ID)
        logger.info("Connected to Azure Service Bus event bus")
    else:
        _event_bus = create_event_bus("local")
        _event_bus.subscribe(AGENT_ID)
        logger.info("Using local event bus (no SERVICE_BUS_CONN_STR)")


# ---------------------------------------------------------------------------
# FastAPI application
# ---------------------------------------------------------------------------

app = FastAPI(title=f"Hive Agent: {AGENT_ID}", version="2.0.0")


class LearnContentRequest(BaseModel):
    content: str  # Raw content for LLM extraction


class LearnFactRequest(BaseModel):
    concept: str
    content: str
    confidence: float = 0.9


class QueryRequest(BaseModel):
    query: str
    limit: int = 10


class FactList(BaseModel):
    facts: list[LearnFactRequest]


class SetGroupRequest(BaseModel):
    group: str


@app.get("/health")
def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "agent_id": AGENT_ID,
        "domain": AGENT_DOMAIN,
        "agent_ready": _agent is not None,
        "model": EVAL_MODEL,
        "version": "2.0.0-learning-agent",
    }


def _publish_fact(content: str, concept: str, confidence: float) -> None:
    """Publish a FACT_PROMOTED event to the event bus."""
    if _event_bus is None:
        return
    import uuid as _uuid

    from event_bus import BusEvent

    evt = BusEvent(
        event_id=_uuid.uuid4().hex,
        event_type="FACT_PROMOTED",
        source_agent=AGENT_ID,
        timestamp=time.time(),
        payload={
            "content": content,
            "concept": concept,
            "confidence": confidence,
            "group": _hive_group,
        },
    )
    try:
        _event_bus.publish(evt)
    except Exception:
        logger.exception("Failed to publish FACT_PROMOTED event")


@app.post("/learn")
def learn(req: LearnContentRequest):
    """Feed content to the LearningAgent for LLM-based fact extraction.

    This triggers real LLM calls (~3 per call):
    1. Extract temporal metadata
    2. Extract structured facts
    3. Generate summary concept map

    Extracted facts are stored in Kuzu, auto-promoted to hive, and
    published to the event bus for other agents.
    """
    if _agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    result = _agent.learn_from_content(req.content)
    facts_stored = result.get("facts_stored", 0)

    # Publish extracted facts to event bus for cross-agent sharing
    # (auto-promotion to local hive already happened in CognitiveAdapter.store_fact)
    if facts_stored > 0 and _event_bus is not None:
        try:
            all_facts = _agent.memory.get_all_facts(limit=facts_stored)
            for f in all_facts[-facts_stored:]:
                fact_text = f.get("outcome", f.get("fact", ""))
                concept = f.get("context", "")
                if fact_text:
                    _publish_fact(fact_text, concept, f.get("confidence", 0.8))
        except Exception:
            logger.exception("Failed to publish extracted facts")

    return {
        "status": "learned",
        "agent_id": AGENT_ID,
        "facts_extracted": result.get("facts_extracted", 0),
        "facts_stored": facts_stored,
    }


@app.post("/learn_fact")
def learn_fact(req: LearnFactRequest):
    """Store a single pre-extracted fact (bypasses LLM extraction)."""
    if _agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    _agent.memory.store_fact(
        context=req.concept,
        fact=req.content,
        confidence=req.confidence,
    )
    _publish_fact(req.content, req.concept, req.confidence)
    return {"status": "stored", "agent_id": AGENT_ID, "concept": req.concept}


@app.post("/learn_batch")
def learn_batch(req: FactList):
    """Store multiple pre-extracted facts."""
    if _agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    stored = 0
    for fact in req.facts:
        _agent.memory.store_fact(
            context=fact.concept,
            fact=fact.content,
            confidence=fact.confidence,
        )
        _publish_fact(fact.content, fact.concept, fact.confidence)
        stored += 1
    return {"status": "stored", "agent_id": AGENT_ID, "count": stored}


@app.post("/query")
def query(req: QueryRequest):
    """Ask the LearningAgent a question using LLM synthesis.

    This triggers real LLM calls (~2 per call):
    1. Intent classification
    2. Answer synthesis from retrieved facts (local + hive)
    """
    if _agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")

    try:
        result = _agent.answer_question(req.query)
        answer = result[0] if isinstance(result, tuple) else str(result)
    except Exception as e:
        logger.exception("Failed to answer question")
        answer = f"Error: {e}"

    return {
        "agent_id": AGENT_ID,
        "answer": answer,
    }


@app.get("/stats")
def stats():
    """Return agent and hive statistics."""
    agent_stats = {}
    if _agent is not None:
        try:
            agent_stats = _agent.get_memory_stats()
        except Exception:
            logger.warning("Failed to get agent memory stats", exc_info=True)

    hive_stats = {}
    if _hive is not None:
        hive_stats = _hive.get_stats()

    return {
        "agent_id": AGENT_ID,
        "group": _hive_group,
        "model": EVAL_MODEL,
        "agent_stats": agent_stats,
        "hive_stats": hive_stats,
    }


@app.post("/set_group")
def set_group(req: SetGroupRequest):
    """Set the agent's group for federated mode."""
    global _hive_group
    _hive_group = req.group
    return {"agent_id": AGENT_ID, "group": _hive_group}


@app.post("/reset")
def reset_agent():
    """Reset the agent (recreate LearningAgent + hive)."""
    if _agent is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    _init_agent()
    return {"agent_id": AGENT_ID, "status": "reset"}


# ---------------------------------------------------------------------------
# Event bus polling (background thread)
# ---------------------------------------------------------------------------


def _poll_events():
    """Background thread: poll Service Bus for incoming hive events.

    When a FACT_PROMOTED event is received from another agent, the fact
    is stored directly in the local hive (InMemoryHiveGraph). The
    LearningAgent's CognitiveAdapter will see these facts via _search_hive()
    when answering questions.
    """
    if _event_bus is None:
        return
    logger.info("Event polling thread started for agent %s", AGENT_ID)
    while True:
        try:
            events = _event_bus.poll(AGENT_ID)
            for event in events:
                if event.event_type == "FACT_PROMOTED":
                    payload = event.payload
                    # In federated mode, only accept facts from same group
                    fact_group = payload.get("group", "")
                    if _hive_group and fact_group and fact_group != _hive_group:
                        continue

                    from hive_graph import HiveFact

                    _hive.promote_fact(
                        AGENT_ID,
                        HiveFact(
                            fact_id="",
                            content=payload.get("content", ""),
                            concept=payload.get("concept", "shared"),
                            confidence=payload.get("confidence", 0.5),
                        ),
                    )
        except Exception:
            logger.exception("Error polling events")
        time.sleep(2)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logger.info(
        "Starting LearningAgent: id=%s domain=%s model=%s",
        AGENT_ID,
        AGENT_DOMAIN,
        EVAL_MODEL,
    )
    _init_agent()

    # Start event polling in background
    poll_thread = threading.Thread(target=_poll_events, daemon=True, name="event-poll")
    poll_thread.start()

    # Run HTTP server
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
