"""NeuroOps Research Department agents."""
from __future__ import annotations

from core import Task
from core.base_agent import BaseAgent


class ResearchAgent(BaseAgent):
    department = "research"
    description = "Researches topics, gathers information, and synthesizes findings."
    capabilities = ["information_retrieval", "literature_review", "fact_checking", "summarization"]
    tools = ["search_engine", "document_index", "web_scraper"]
    model_preference = "gemini"

    def think(self, task: Task) -> tuple[str, float]:
        self.log("Researching topic...")
        resp = self.call_model(
            "You are a research analyst. Provide key findings and relevant context.",
            f"Task: {task.title}\nDescription: {task.description}",
        )
        self.log("Research complete.")
        return resp.content, resp.confidence


class DocumentationAgent(BaseAgent):
    department = "research"
    description = "Generates documentation from code, specs, or task descriptions."
    capabilities = ["technical_writing", "api_documentation", "readme_generation", "examples"]
    tools = ["markdown_editor", "doc_generator"]
    model_preference = "openai"

    def think(self, task: Task) -> tuple[str, float]:
        self.log("Drafting documentation...")
        resp = self.call_model(
            "You are a technical writer. Generate clear, structured documentation.",
            f"Task: {task.title}\nDescription: {task.description}",
        )
        self.log("Documentation generated.")
        return resp.content, resp.confidence
