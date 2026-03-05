"""Filesystem actions: filesystem read/write/list."""
from . import Action
import os


def filesystem_action(action: str, path: str, **kwargs):
    if action == "list":
        return os.listdir(path)
    elif action == "read":
        with open(path, "r") as f:
            return f.read()
    elif action == "write":
        with open(path, "w") as f:
            f.write(kwargs.get("content", ""))
            return True
    else:
        raise ValueError(f"Unknown filesystem action: {action}")


def register() -> dict:
    return {
        "filesystem": Action(
            name="filesystem",
            description="Access and manipulate local files and directories.",
            run=filesystem_action,
            permission="get_file",
            category="tool",
        ),
    }
