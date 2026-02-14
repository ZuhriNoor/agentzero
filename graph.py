"""
LangGraph setup for AgentZero: defines the core graph, nodes, and transitions.
"""

from langgraph.graph import StateGraph, START, END
from agent_state import AgentState
from intent_router import intent_router
from policy_enforcer import policy_enforcer
from context_builder import context_builder
from planner import planner
from executor import executor
from memory_writer import memory_writer
from response_composer import response_composer
from error_handler import error_handler

def build_agentzero_graph():
    graph = StateGraph(AgentState)
    graph.add_node("intent_router", intent_router)
    graph.add_node("policy_enforcer", policy_enforcer)
    graph.add_node("context_builder", context_builder)
    graph.add_node("planner", planner)
    graph.add_node("executor", executor)
    graph.add_node("memory_writer", memory_writer)
    graph.add_node("response_composer", response_composer)
    graph.add_node("error_handler", error_handler)

    # Entry point
    graph.add_edge(START, "intent_router")

    # Transitions (explicit, deterministic)
    graph.add_edge("intent_router", "policy_enforcer")
    graph.add_edge("policy_enforcer", "context_builder")
    graph.add_edge("policy_enforcer", "context_builder")
    
    def route_context_builder(state: AgentState):
        if state.intent == "chat":
            return "executor"
        return "planner"

    graph.add_conditional_edges(
        "context_builder",
        route_context_builder,
        {
            "executor": "executor",
            "planner": "planner"
        }
    )

    graph.add_edge("planner", "executor")
    graph.add_edge("executor", "memory_writer")
    graph.add_edge("memory_writer", "response_composer")
    graph.add_edge("response_composer", END)  # End

    # Error/fallback: handled inside node logic, not via conditional transitions
    graph.add_edge("error_handler", END)  # End on error

    return graph
