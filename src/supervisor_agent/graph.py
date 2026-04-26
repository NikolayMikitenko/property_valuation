from __future__ import annotations

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from supervisor_agent.state import AgentState, InputState, OutputState

from supervisor_agent.nodes import (
    register_run_node, 
    research_and_store_candidates_node, 
    count_approved_node,
    route_after_count_approved,
    pull_next_candidate_node,
    # pull_candidates_batch_node, 
    route_after_pull_next_candidate, 
    validate_candidate_node,
    # validate_candidates_batch_node,
    ensure_has_proof_node,
    copy_proof_node,
    finalize_run_node
)

def build_graph():
    graph = StateGraph(AgentState, input_schema=InputState, output_schema=OutputState)

    graph.add_node("register_run", register_run_node)
    graph.add_node("research_and_store_candidates", research_and_store_candidates_node)
    graph.add_node("count_approved", count_approved_node)
    # graph.add_node("pull_candidates_batch", pull_candidates_batch_node)
    graph.add_node("pull_next_candidate", pull_next_candidate_node)
    # graph.add_node("validate_candidates_batch", validate_candidates_batch_node)
    graph.add_node("validate_candidate", validate_candidate_node)
    # graph.add_node("materialize_approved_objects", materialize_approved_objects_node)
    graph.add_node("ensure_has_proof", ensure_has_proof_node)
    graph.add_node("copy_proof", copy_proof_node)
    graph.add_node("finalize_run", finalize_run_node) 

    graph.add_edge(START, "register_run")
    graph.add_edge("register_run", "research_and_store_candidates")
    # graph.add_edge("research_and_store_candidates", "pull_candidates_batch")
    # graph.add_edge("research_and_store_candidates", "pull_next_candidate")
    graph.add_edge("research_and_store_candidates", "count_approved")
    graph.add_conditional_edges(
        "count_approved",
        route_after_count_approved,
        {
            "pull_next_candidate": "pull_next_candidate",
            "ensure_has_proof": "ensure_has_proof",
        }
    )

    graph.add_conditional_edges(
        "pull_next_candidate",
        route_after_pull_next_candidate,
        {
            "validate_candidate": "validate_candidate",
            "research_and_store_candidates": "research_and_store_candidates",
            "ensure_has_proof": "ensure_has_proof",
        },
    )    
    graph.add_edge("validate_candidate", "count_approved")

    graph.add_edge("ensure_has_proof", "copy_proof")
    graph.add_edge("copy_proof", "finalize_run")
    graph.add_edge("finalize_run", END) 

    return graph.compile(checkpointer=InMemorySaver())