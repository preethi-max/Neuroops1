"""NeuroOps Design Department agents."""
from __future__ import annotations

from core import Task
from core.base_agent import BaseAgent


class UIUXDesignerAgent(BaseAgent):
    department = "design"
    description = "Designs user interfaces, layouts, and user experiences."
    capabilities = ["ui_design", "ux_research", "wireframing", "prototyping", "design_systems"]
    tools = ["figma", "design_tokens", "color_palette"]
    model_preference = "gemini"

    def think(self, task: Task) -> tuple[str, float]:
        self.log("Designing UI/UX...")
        resp = self.call_model(
            "You are a UI/UX designer. Propose a design approach with layout and interaction details.",
            f"Task: {task.title}\nDescription: {task.description}",
        )
        self.log("UI/UX design proposed.")
        return resp.content, resp.confidence


class AccessibilityAgent(BaseAgent):
    department = "design"
    description = "Audits and improves accessibility (WCAG, ARIA, contrast)."
    capabilities = ["wcag_audit", "aria_review", "contrast_analysis", "screen_reader_testing"]
    tools = ["axe_core", "lighthouse", "screen_reader"]
    model_preference = "gemini"

    def think(self, task: Task) -> tuple[str, float]:
        self.log("Auditing accessibility...")
        resp = self.call_model(
            "You are an accessibility specialist. Identify WCAG issues and propose fixes.",
            f"Task: {task.title}\nDescription: {task.description}",
        )
        self.log("Accessibility audit complete.")
        return resp.content, resp.confidence
