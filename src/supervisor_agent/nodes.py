from __future__ import annotations

from typing import Any

import json

from supervisor_agent.state import AgentState
from supervisor_agent.config import CONFIG
from supervisor_agent.a2a_client import call_proof, call_researcher, call_validator

from fastmcp import Client

import asyncio

# def _extract_payload(result: Any) -> Any:
#     if hasattr(result, "data") and result.data is not None:
#         return result.data
#     if hasattr(result, "structured_content") and result.structured_content is not None:
#         return result.structured_content
#     return result

def parse_mcp_result(result) -> dict:
    if hasattr(result, "data") and isinstance(result.data, dict):
        return result.data

    if hasattr(result, "structured_content") and isinstance(result.structured_content, dict):
        return result.structured_content

    if hasattr(result, "content") and isinstance(result.content, list) and result.content:
        first = result.content[0]

        if isinstance(first, dict) and "text" in first:
            return json.loads(first["text"])

        if hasattr(first, "text") and isinstance(first.text, str):
            return json.loads(first.text)

    raise ValueError(f"Unexpected MCP result type: {type(result).__name__}")

async def register_run_node(state: AgentState) -> dict[str, Any]:
    async with Client(CONFIG.mongo_store_mcp_url) as client:
        result = await client.call_tool(
            "register_valuation_run",
            {
                "external_object_id": state["external_object_id"],
                "valuation_description": state["valuation_description"],
                "target_count": state["target_count"],
            },
        )

    payload = parse_mcp_result(result)
    return {
        "valuation_id": payload["valuation_id"],
        "status": "run_registered",
        "approved_count": 0,
        "search_round": 0
    }

async def research_and_store_candidates_node(state: AgentState) -> dict[str, Any]:
    research = await call_researcher(
        CONFIG.research_a2a_url,
        {
            "user_query": state["valuation_description"],
            "thread_id": f"research:{state['valuation_id']}",
        },
        user_id=state["user_id"],
        session_id=state["session_id"],
    )

    search_url = research.get("search_url")
    candidate_ids = research.get("candidates_ids") or []

    items = [
        {
            # "item_id": str(item_id),
            "property_id": item_id,
            "search_url": search_url,
            "source": "domria",
        }
        for item_id in candidate_ids
    ]

    async with Client(CONFIG.mongo_store_mcp_url) as client:
        save_candidates_result = await client.call_tool(
            "save_candidates",
            {
                "valuation_id": state["valuation_id"],
                "items": items,
            },
        )
        # print(save_candidates_result)
        increase_search_round_result = await client.call_tool(
            "increment_valuation_search_round",
            {
                "valuation_id": state["valuation_id"],
            },
        )

    search_round = state["search_round"] + 1

    return {
        "search_url": search_url,
        # "candidate_ids": candidate_ids,
        "search_round": search_round,
        "status": "candidates_stored",
    }

async def pull_next_candidate_node(state: AgentState) -> dict[str, Any]:
    async with Client(CONFIG.mongo_store_mcp_url) as client:
        result = await client.call_tool(
            "get_unprocessed_valuation_candidates",
            {
                "valuation_id": state["valuation_id"],
                "limit": 1,
            },
        )

    payload = parse_mcp_result(result)
    candidates = payload.get('result') or []
    next_candidate = candidates[0] if candidates else None

    return {
        "next_candidate": next_candidate,
        "status": "candidate_polled",
    }

# async def pull_candidates_batch_node(state: AgentState) -> dict[str, Any]:
#     async with Client(CONFIG.mongo_store_mcp_url) as client:
#         result = await client.call_tool(
#             "get_unprocessed_valuation_candidates",
#             {
#                 "valuation_id": state["valuation_id"],
#                 "limit": CONFIG.batch_size,
#             },
#         )

#     payload = parse_mcp_result(result)
#     candidates = payload.get('result') or []

#     return {
#         "candidates_batch": candidates,
#         "status": "candidates_batch_polled",
#     }


async def validate_candidate_node(state: AgentState) -> dict[str, Any]:
    candidate = state["next_candidate"]

    validation = await call_validator(
        CONFIG.validator_a2a_url,
        {
            "valuation_property_description": state["valuation_description"],
            "session_id": state["valuation_id"],
            "item_id": candidate["item_id"],
            "search_url": candidate.get("search_url"),
            "property_id": candidate.get("property_id"),
            "url": candidate.get("url"),
        },
        user_id=state["user_id"],
        session_id=state["session_id"],
    )

    async with Client(CONFIG.mongo_store_mcp_url) as client:
        await client.call_tool(
            "save_valuation_candidates_result",
            {
                "valuation_id": state["valuation_id"],
                "item_id": validation["item_id"],
                "status": validation["status"],
                "reason": validation["reason"],
                "mongo_id": validation.get("mongo_id"),
                "mongo_path": validation.get("mongo_path"),
                "is_duplicate": validation.get("is_duplicate", False),
                "property_id": validation.get("property_id"),
                "url": validation.get("url"),
                "payload": validation.get("property_payload")
            },
        )

    print(validation["status"])
    print(validation["reason"])
    # print(validation.get("property_payload"))

    return {
        # "validation_result": validation,
        "status": "candidate_validated",
    }

async def count_approved_node(state: AgentState) -> dict[str, Any]:
    async with Client(CONFIG.mongo_store_mcp_url) as client:
        result = await client.call_tool(
            "get_valuation_approved_count",
            {"valuation_id": state["valuation_id"]},
        )

    payload = parse_mcp_result(result)
    return {
        "approved_count": payload.get("approved_count", 0),
        "status": "count_approved",
    }

def route_after_count_approved(state: AgentState) -> str:
    if state["approved_count"] >= state["target_count"]:
        return "ensure_has_proof" 
    else:
        return "pull_next_candidate"

async def _validate_one_candidate(
    candidate: dict[str, Any],
    state: AgentState,
    semaphore: asyncio.Semaphore,
) -> dict[str, Any]:
    async with semaphore:
        validation = await call_validator(
            CONFIG.validator_a2a_url,
            {
                "valuation_property_description": state["valuation_description"],
                "session_id": state["valuation_id"],
                "item_id": candidate["item_id"],
                "search_url": candidate.get("search_url"),
                "property_id": candidate.get("property_id"),
                "url": candidate.get("url"),
            },
            user_id=state["user_id"],
            session_id=state["session_id"],
        )

        async with Client(CONFIG.mongo_store_mcp_url) as client:
            await client.call_tool(
                "save_valuation_candidates_result",
                {
                    "valuation_id": state["valuation_id"],
                    "item_id": validation["item_id"],
                    "status": validation["status"],
                    "reason": validation["reason"],
                    "mongo_id": validation.get("mongo_id"),
                    "mongo_path": validation.get("mongo_path"),
                    "is_duplicate": validation.get("is_duplicate", False),
                    "property_id": validation.get("property_id"),
                    "url": validation.get("url"),
                },
            )

        return validation

async def validate_candidates_batch_node(state: AgentState) -> dict[str, Any]:
    candidates = state.get("candidates_batch", [])
    if not candidates:
        return {
            "validation_results": [],
            "status": "no_candidates_to_validate",
        }

    semaphore = asyncio.Semaphore(CONFIG.max_concurrency)

    tasks = [
        _validate_one_candidate(candidate, state, semaphore)
        for candidate in candidates
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)

    validation_results: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    for candidate, result in zip(candidates, results):
        if isinstance(result, Exception):
            errors.append(
                {
                    "item_id": candidate["item_id"],
                    "error": f"{type(result).__name__}: {result}",
                }
            )
        else:
            validation_results.append(result)

    return {
        "validation_results": validation_results,
        "validation_errors": errors,
        "status": "candidates_batch_validated",
    }

# async def materialize_approved_objects_node(state: AgentState) -> dict[str, Any]:
#     async with Client(CONFIG.mongo_store_mcp_url) as client:
#         result = await client.call_tool(
#             "get_approved_without_materialization",
#             {
#                 "valuation_id": state["valuation_id"],
#                 "limit": 100,
#             },
#         )

#     payload = parse_mcp_result(result) or []
    
#     items = payload or []

    # async with Client(CONFIG.mongo_store_mcp_url) as client:
    #     for item in items:
    #         await client.call_tool(
    #             "mark_candidate_materialized",
    #             {
    #                 "valuation_id": state["valuation_id"],
    #                 "item_id": item["item_id"],
    #             },
    #         )

#         count_result = await client.call_tool(
#             "get_valuation_approved_count",
#             {"valuation_run_id": state["valuation_run_id"]},
#         )

#     count_payload = _extract_payload(count_result)

#     return {
#         "approved_count": count_payload.get("approved_count", 0),
#         "approved_without_materialization": items,
#         "status": "approved_materialized",
#     }


async def ensure_has_proof_node(state: AgentState) -> dict[str, Any]:
    async with Client(CONFIG.mongo_store_mcp_url) as client:
        result = await client.call_tool(
            "get_approved_without_proof",
            {
                "valuation_id": state["valuation_id"],
                "limit": 100,
            },
        )

    payload = parse_mcp_result(result)
    items = payload["result"] or []

    for item in items:
        proof = await call_proof(CONFIG.proof_a2a_url, {"url":item["url"],},)
        async with Client(CONFIG.mongo_store_mcp_url) as client:
            await client.call_tool(
                "save_candidate_external_proof_result",
                {
                    "valuation_id": state["valuation_id"],
                    "item_id": item["item_id"],
                    "external_proof_path": proof.get("path"),
                    "proof_error": proof.get("error"),
                },
                user_id=state["user_id"],
                session_id=state["session_id"],
            )

    return {
        "status": "proof_linked",
    }

async def copy_proof_node(state: AgentState) -> dict[str, Any]:
    async with Client(CONFIG.mongo_store_mcp_url) as client:
        result = await client.call_tool(
            "get_proof_without_minio",
            {
                "valuation_id": state["valuation_id"],
                "limit": 100,
            },
        )

    payload = parse_mcp_result(result)
    items = payload["result"] or []

    for item in items:
        async with Client(CONFIG.object_move_mcp_url) as minio_client:
            copy_result = await minio_client.call_tool(
                "move_object_from_temporary_to_permanent_store",
                {
                    "source_path": item["external_proof_path"],
                    "target_bucket": CONFIG.minio_bucket,
                },
            )

        async with Client(CONFIG.mongo_store_mcp_url) as mongo_client:
            copy_payload = parse_mcp_result(copy_result)
            await mongo_client.call_tool(
                "save_candidate_proof_result",
                {
                    "valuation_id": state["valuation_id"],
                    "item_id": item["item_id"],
                    "proof_path": copy_payload.get("path"),
                },
            )

    return {
        # "proof_without_minio": items,
        "status": "proof_moved",
    }

async def finalize_run_node(state: AgentState) -> dict[str, Any]:
    async with Client(CONFIG.mongo_store_mcp_url) as client:
        await client.call_tool(
            "complete_valuation_run",
            {
                "valuation_id": state["valuation_id"],
            },
        )

        result = await client.call_tool(
            "get_valuation_result",
            {
                "valuation_id": state["valuation_id"],
            },
        )

    payload = parse_mcp_result(result)

    return {
        "final": payload,
        "status": "completed",
    }

def route_after_pull_next_candidate(state: AgentState) -> str:
    if state.get("next_candidate"):
        return "validate_candidate"
    if state["search_round"] > 8:
        return "ensure_has_proof"
    return "research_and_store_candidates"