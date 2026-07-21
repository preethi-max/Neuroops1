"""NeuroOps Design Department agents."""
from __future__ import annotations

from core import Task
from core.base_agent import BaseAgent


class UISuggestionAgent(BaseAgent):
    department = "design"
    description = "Suggests UI improvements and component layouts."

    def think(self, task: Task) -> tuple[str, float]:
        self.log("Analyzing UI requirements...")
        suggestions = [
            "## UI Suggestions",
            "",
            f"**Context:** {task.title}",
            "",
            "1. Use a consistent 8px spacing grid.",
            "2. Ensure WCAG AA contrast ratios on all text.",
            "3. Add hover and focus states to interactive elements.",
            "4. Consider a sticky header for navigation.",
            "5. Use progressive disclosure for complex forms.",
        ]
        self.log("Generated 5 UI suggestions.")
        return "\n".join(suggestions), 0.79


class WireframeAgent(BaseAgent):
    department = "design"
    description = "Produces text-based wireframe layouts."

    def think(self, task: Task) -> tuple[str, float]:
        self.log("Drafting wireframe...")
        wireframe = [
            "## Wireframe",
            "",
            "+------------------------------------------+",
            "|  [Logo]   Nav: Home  About  Contact      |",
            "+------------------------------------------+",
            "|                                          |",
            "|   +------------------+  +-----------+    |",
            "|   |  Main Content    |  |  Sidebar  |    |",
            "|   |                  |  |           |    |",
            "|   +------------------+  +-----------+    |",
            "|                                          |",
            "+------------------------------------------+",
            "|              Footer                      |",
            "+------------------------------------------+",
            "",
            f"Layout for: {task.title}",
        ]
        self.log("Wireframe complete.")
        return "\n".join(wireframe), 0.75
