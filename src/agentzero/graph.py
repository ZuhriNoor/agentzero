"""
LangGraph setup for AgentZero: defines the core graph, nodes, and transitions.
Every node transition checks state.error and routes to error_handler if set.
"""

from langgraph.graph import StateGraph, START, END
from agentzero.agent_state import AgentState
from agentzero.intent_router import intent_router
from agentzero.policy_enforcer import policy_enforcer
from agentzero.context_builder import context_builder
from agentzero.planner import planner
from agentzero.executor import executor
from agentzero.evaluator import evaluator
from agentzero.memory_writer import memory_writer
from agentzero.response_composer import response_composer
from agentzero.error_handler import error_handler


def _error_or(next_node: str):
    """Returns a routing function: go to error_handler if error, else next_node."""
    def route(state: AgentState):
        if state.error:
            return "error_handler"
        return next_node
    return route


def _error_or_context_route(state: AgentState):
    """Route after context_builder: error_handler > executor (chat) > planner."""
    if state.error:
        return "error_handler"
    if state.intent == "chat":
        return "executor"
    return "planner"


def build_agentzero_graph():
    graph = StateGraph(AgentState)
    graph.add_node("intent_router", intent_router)
    graph.add_node("policy_enforcer", policy_enforcer)
    graph.add_node("context_builder", context_builder)
    graph.add_node("planner", planner)
    graph.add_node("executor", executor)
    graph.add_node("evaluator", evaluator)
    graph.add_node("memory_writer", memory_writer)
    graph.add_node("response_composer", response_composer)
    graph.add_node("error_handler", error_handler)

    # Entry point
    graph.add_edge(START, "intent_router")

    # Every transition checks for errors before proceeding
    graph.add_conditional_edges("intent_router", _error_or("policy_enforcer"), {
        "policy_enforcer": "policy_enforcer",
        "error_handler": "error_handler",
    })

    graph.add_conditional_edges("policy_enforcer", _error_or("context_builder"), {
        "context_builder": "context_builder",
        "error_handler": "error_handler",
    })

    graph.add_conditional_edges("context_builder", _error_or_context_route, {
        "executor": "executor",
        "planner": "planner",
        "error_handler": "error_handler",
    })

    graph.add_conditional_edges("planner", _error_or("executor"), {
        "executor": "executor",
        "error_handler": "error_handler",
    })

    graph.add_conditional_edges("executor", _error_or("evaluator"), {
        "evaluator": "evaluator",
        "error_handler": "error_handler",
    })
    
    def route_evaluator(state: AgentState):
        if state.error:
            return "error_handler"
        if state.step == "evaluator (retry loop)":
            return "planner"
        return "memory_writer"

    graph.add_conditional_edges("evaluator", route_evaluator, {
        "planner": "planner",
        "memory_writer": "memory_writer",
        "error_handler": "error_handler",
    })

    graph.add_conditional_edges("memory_writer", _error_or("response_composer"), {
        "response_composer": "response_composer",
        "error_handler": "error_handler",
    })

    graph.add_edge("response_composer", END)
    graph.add_edge("error_handler", END)

    return graph
