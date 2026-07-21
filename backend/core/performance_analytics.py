"""NeuroOps Performance Analytics tracker.

Tracks per-agent and system-wide metrics:
  - tasks completed
  - success rate
  - average confidence
  - execution time
  - failures

This data feeds back into the CEO's future agent selection decisions.
"""
from __future__ import annotations

from typing import Any, Dict

from core.storage import session_store


class PerformanceAnalytics:
    """Aggregates performance metrics from the SessionStore."""

    def get_agent_stats(self, agent_id: str) -> Dict[str, Any]:
        perf = session_store.get_agent_performance(agent_id)
        if not perf:
            return {
                "agent_id": agent_id,
                "tasks_completed": 0,
                "tasks_failed": 0,
                "success_rate": 0.0,
                "avg_confidence": 0.0,
                "avg_exec_time_ms": 0.0,
            }
        return {
            "agent_id": agent_id,
            "tasks_completed": perf.get("tasks_completed", 0),
            "tasks_failed": perf.get("tasks_failed", 0),
            "success_rate": perf.get("success_rate", 0.0),
            "avg_confidence": perf.get("avg_confidence", 0.0),
            "avg_exec_time_ms": perf.get("avg_exec_time_ms", 0.0),
        }

    def get_system_stats(self) -> Dict[str, Any]:
        all_perf = session_store.get_all_performance()
        total_completed = sum(p.get("tasks_completed", 0) for p in all_perf.values())
        total_failed = sum(p.get("tasks_failed", 0) for p in all_perf.values())
        total_tasks = total_completed + total_failed
        all_conf = [p.get("avg_confidence", 0) for p in all_perf.values() if p.get("avg_confidence")]
        all_times = [p.get("avg_exec_time_ms", 0) for p in all_perf.values() if p.get("avg_exec_time_ms")]
        return {
            "total_tasks": total_tasks,
            "total_completed": total_completed,
            "total_failed": total_failed,
            "system_success_rate": total_completed / max(1, total_tasks),
            "system_avg_confidence": sum(all_conf) / max(1, len(all_conf)),
            "system_avg_exec_time_ms": sum(all_times) / max(1, len(all_times)),
            "active_agents": len(all_perf),
        }

    def get_all_agent_stats(self) -> Dict[str, Any]:
        all_perf = session_store.get_all_performance()
        return {aid: self.get_agent_stats(aid) for aid in all_perf}


# Singleton
performance_analytics = PerformanceAnalytics()
