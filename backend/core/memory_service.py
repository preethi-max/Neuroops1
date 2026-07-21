"""NeuroOps Memory System.

Four memory types:
  A) Episodic Memory   — previous conversations, execution history, agent decisions
  B) Semantic Memory   — documents, code knowledge, technical information
  C) Project Memory    — project structure, completed tasks, previous states
  D) Agent Memory      — per-agent: previous tasks, success rate, learned preferences

Supports "Continue yesterday's project" by retrieving previous project state,
loading previous agent activities, and continuing from the last checkpoint.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from core import MemoryEntry, MemoryType
from core.event_bus import event_bus
from core.storage import session_store


class MemoryService:
    """Unified memory service backed by SessionStore (DB-ready)."""

    # ---- Episodic Memory ----
    def store_episode(self, content: str, agent_id: Optional[str] = None, metadata: Optional[dict] = None) -> MemoryEntry:
        entry = MemoryEntry(
            memory_id=f"ep-{uuid.uuid4().hex[:8]}",
            memory_type=MemoryType.EPISODIC,
            content=content,
            agent_id=agent_id,
            metadata=metadata or {},
        )
        session_store.add_memory(entry)
        event_bus.emit(
            "memory:accessed",
            source="MemoryService",
            message=f"Episodic memory stored: {content[:60]}",
            agent_id=agent_id,
            data={"memory_type": "episodic", "memory_id": entry.memory_id},
        )
        return entry

    def recall_episodes(self, agent_id: Optional[str] = None) -> List[MemoryEntry]:
        return session_store.get_memory(memory_type="episodic", agent_id=agent_id)

    # ---- Semantic Memory ----
    def store_knowledge(self, content: str, metadata: Optional[dict] = None) -> MemoryEntry:
        entry = MemoryEntry(
            memory_id=f"sem-{uuid.uuid4().hex[:8]}",
            memory_type=MemoryType.SEMANTIC,
            content=content,
            metadata=metadata or {},
        )
        session_store.add_memory(entry)
        event_bus.emit(
            "memory:accessed",
            source="MemoryService",
            message=f"Semantic memory stored: {content[:60]}",
            data={"memory_type": "semantic", "memory_id": entry.memory_id},
        )
        return entry

    def recall_knowledge(self) -> List[MemoryEntry]:
        return session_store.get_memory(memory_type="semantic")

    # ---- Project Memory ----
    def store_project_state(self, content: str, project_id: Optional[str] = None, metadata: Optional[dict] = None) -> MemoryEntry:
        entry = MemoryEntry(
            memory_id=f"proj-{uuid.uuid4().hex[:8]}",
            memory_type=MemoryType.PROJECT,
            content=content,
            project_id=project_id,
            metadata=metadata or {},
        )
        session_store.add_memory(entry)
        event_bus.emit(
            "memory:accessed",
            source="MemoryService",
            message=f"Project state stored: {content[:60]}",
            data={"memory_type": "project", "memory_id": entry.memory_id, "project_id": project_id},
        )
        return entry

    def recall_project(self, project_id: Optional[str] = None) -> List[MemoryEntry]:
        entries = session_store.get_memory(memory_type="project")
        if project_id:
            entries = [e for e in entries if e.project_id == project_id]
        return entries

    def get_last_checkpoint(self) -> Optional[MemoryEntry]:
        """Return the most recent project memory entry (checkpoint)."""
        entries = self.recall_project()
        return entries[-1] if entries else None

    # ---- Agent Memory ----
    def store_agent_memory(self, agent_id: str, content: str, metadata: Optional[dict] = None) -> MemoryEntry:
        entry = MemoryEntry(
            memory_id=f"agent-{uuid.uuid4().hex[:8]}",
            memory_type=MemoryType.AGENT,
            content=content,
            agent_id=agent_id,
            metadata=metadata or {},
        )
        session_store.add_memory(entry)
        event_bus.emit(
            "memory:accessed",
            source="MemoryService",
            message=f"Agent memory stored for {agent_id}: {content[:60]}",
            agent_id=agent_id,
            data={"memory_type": "agent", "memory_id": entry.memory_id},
        )
        return entry

    def recall_agent_memory(self, agent_id: str) -> List[MemoryEntry]:
        return session_store.get_memory(memory_type="agent", agent_id=agent_id)

    # ---- Retrieval helpers ----
    def get_all_memory(self) -> List[MemoryEntry]:
        return session_store.get_memory()

    def get_memory_by_type(self, memory_type: str) -> List[MemoryEntry]:
        return session_store.get_memory(memory_type=memory_type)

    def search_memory(self, query: str) -> List[MemoryEntry]:
        """Simple keyword search (placeholder for vector DB in future phase)."""
        q = query.lower()
        return [m for m in session_store.get_memory() if q in m.content.lower()]

    # ---- Continuation support ----
    def prepare_continuation_context(self) -> Dict[str, Any]:
        """Gather previous project state + agent activities for 'continue' requests."""
        checkpoint = self.get_last_checkpoint()
        episodes = self.recall_episodes()
        agent_memories = session_store.get_memory(memory_type="agent")
        return {
            "last_checkpoint": checkpoint.to_dict() if checkpoint else None,
            "episode_count": len(episodes),
            "agent_memory_count": len(agent_memories),
            "recent_episodes": [e.to_dict() for e in episodes[-5:]],
            "recent_agent_memories": [m.to_dict() for m in agent_memories[-5:]],
        }


# Singleton memory service
memory_service = MemoryService()
