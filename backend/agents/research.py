"""NeuroOps Research Department agents."""
from __future__ import annotations

from core import Task
from core.base_agent import BaseAgent


class DocumentSearchAgent(BaseAgent):
    department = "research"
    description = "Searches available documents for relevant information."

    def think(self, task: Task) -> tuple[str, float]:
        self.log("Searching document index...")
        query = task.title + " " + (task.description or "")
        # Simulated retrieval (no vector DB yet — placeholder for Phase 3+)
        findings = [
            f"## Document Search Results for: {task.title}",
            "",
            "1. [Internal] Architecture overview mentions related concepts.",
            "2. [Spec] Requirement doc aligns with this task.",
            "3. [History] A similar request was processed previously.",
            "",
            f"Query terms: {query[:80]}",
            "",
            "Note: Vector DB integration pending (Phase 3).",
        ]
        self.log("Retrieved 3 simulated matches.")
        return "\n".join(findings), 0.72


class SummarizerAgent(BaseAgent):
    department = "research"
    description = "Summarizes long text into concise points."

    def think(self, task: Task) -> tuple[str, float]:
        self.log("Summarizing content...")
        source = task.description or task.title
        sentences = [s.strip() for s in source.split(".") if s.strip()]
        summary_lines = ["## Summary", ""]
        if not sentences:
            summary_lines.append("- No content to summarize.")
        else:
            for i, s in enumerate(sentences[:5], 1):
                summary_lines.append(f"{i}. {s[:100]}")
        summary_lines.append("")
        summary_lines.append(f"Condensed from {len(sentences)} sentence(s).")
        self.log("Summary generated.")
        return "\n".join(summary_lines), 0.86
