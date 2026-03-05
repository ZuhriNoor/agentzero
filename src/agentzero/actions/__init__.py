"""
Unified Action registry for AgentZero.
All executable capabilities (formerly tools + skills) are registered here.
"""
from typing import Any, Dict, Callable, Optional


class Action:
    """Base class for all agent actions."""
    def __init__(
        self,
        name: str,
        description: str,
        run: Callable,
        permission: Optional[str] = None,
        category: str = "general",
    ):
        self.name = name
        self.description = description
        self.run = run
        self.permission = permission or name
        self.category = category  # "tool", "skill", "integration" — for organization


def load_actions() -> Dict[str, Action]:
    """Loads and returns all registered actions."""
    from .calendar_actions import register as calendar_register
    from .task_actions import register as task_register
    from .habit_actions import register as habit_register
    from .memory_actions import register as memory_register
    from .filesystem_actions import register as filesystem_register
    from .planning_actions import register as planning_register

    registry: Dict[str, Action] = {}
    for registrar in [
        calendar_register,
        task_register,
        habit_register,
        memory_register,
        filesystem_register,
        planning_register,
    ]:
        registry.update(registrar())

    return registry
