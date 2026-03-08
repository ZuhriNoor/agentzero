"""
LangGraph setup for AgentZero: defines the core graph, nodes, and transitions.
Every node transition checks state.error and routes to error_handler if set.
"""

from langgraph.graph import StateGraph, START, END
from agentzero.agent_state import AgentState
from agentzero.supervisor import supervisor_node
from agentzero.policy_enforcer import policy_enforcer
from agentzero.context_builder import context_builder
from agentzero.agents import calendar_agent_node, task_agent_node, knowledge_agent_node
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
    graph.add_node("supervisor", supervisor_node)
    graph.add_node("policy_enforcer", policy_enforcer)
    graph.add_node("context_builder", context_builder)
    
    # Sub-Agents
    graph.add_node("calendar_agent", calendar_agent_node)
    graph.add_node("task_agent", task_agent_node)
    graph.add_node("knowledge_agent", knowledge_agent_node)
    
    graph.add_node("executor", executor)
    graph.add_node("evaluator", evaluator)
    graph.add_node("memory_writer", memory_writer)
    graph.add_node("response_composer", response_composer)
    graph.add_node("error_handler", error_handler)

    # Entry point
    graph.add_edge(START, "supervisor")

    graph.add_conditional_edges("supervisor", _error_or("policy_enforcer"), {
        "policy_enforcer": "policy_enforcer",
        "error_handler": "error_handler",
    })

    graph.add_conditional_edges("policy_enforcer", _error_or("context_builder"), {
        "context_builder": "context_builder",
        "error_handler": "error_handler",
    })

    def route_to_agent(state: AgentState):
        if state.error: return "error_handler"
        domain = state.intent or "chat"
        if domain == "calendar": return "calendar_agent"
        if domain == "task": return "task_agent"
        if domain == "knowledge": return "knowledge_agent"
        return "executor" # If chat, skip agents directly to executor

    graph.add_conditional_edges("context_builder", route_to_agent, {
        "calendar_agent": "calendar_agent",
        "task_agent": "task_agent",
        "knowledge_agent": "knowledge_agent",
        "executor": "executor",
        "error_handler": "error_handler",
    })

    # All sub-agents converge back to the executor
    for agent_node in ["calendar_agent", "task_agent", "knowledge_agent"]:
        graph.add_conditional_edges(agent_node, _error_or("executor"), {
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
            # On retry, send back to the correct sub-agent!
            domain = state.intent or "chat"
            return f"{domain}_agent" if domain in ["calendar", "task", "knowledge"] else "executor"
        return "memory_writer"

    graph.add_conditional_edges("evaluator", route_evaluator, {
        "calendar_agent": "calendar_agent",
        "task_agent": "task_agent",
        "knowledge_agent": "knowledge_agent",
        "executor": "executor",
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
