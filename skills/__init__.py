"""
Skill interface and loader for AgentZero. Skills are modular, API-agnostic, and loaded locally.
"""
from typing import Any, Dict, Callable

class Skill:
    def __init__(self, name: str, description: str, run: Callable):
        self.name = name
        self.description = description
        self.run = run

def load_skills() -> Dict[str, Skill]:
    # Dynamically load skill modules from skills/ directory
    # For now, return a static example
    from .task_planner import AddTaskSkill
    return {
        "add_task": AddTaskSkill(),
        # ...add more skills...
    }
