from __future__ import annotations

from fastapi import FastAPI, HTTPException

from valuation_store_api.schemas import RegisterRunRequest, SaveCandidatesRequest, ValidationPatchRequest, ProofPatchRequest, MinioPatchRequest
from valuation_store_api import utils

app = FastAPI(title="Valuation Mongo API")

@app.post("/valuation/register")
async def register_run(request: RegisterRunRequest):
    return await utils.register_run(
        external_object_id=request.external_object_id,
        valuation_description=request.valuation_description,
        target_count=request.target_count,
    )

@app.post("/valuation/{valuation_id}/candidates")
async def save_candidates(request: SaveCandidatesRequest):
    return await utils.save_candidates(
        valuation_id=request.valuation_id,
        items=[item.model_dump() for item in request.items],
    )

@app.get("/valuation/{valuation_id}/candidates/unprocessed")
async def get_unprocessed_candidates(valuation_id: str, limit: int = 1):
    return await utils.get_unprocessed_candidates(valuation_id=valuation_id, limit=limit)

# @app.post("/valuation/{valuation_id}/candidates/{item_id}/processing")
# async def mark_processing(valuation_id: str, item_id: str):
#     return await utils.mark_candidate_processing(valuation_id=valuation_id, item_id=item_id)

@app.patch("/valuation/{valuation_id}/candidates/{item_id}/validation")
async def save_validation(request: ValidationPatchRequest):
    return await utils.save_validation_result(
        valuation_id=request.valuation_id,
        item_id=request.item_id,
        status=request.status,
        reason=request.reason,
        mongo_id=request.mongo_id,
        mongo_path=request.mongo_path,
        is_duplicate=request.is_duplicate,
        property_id=request.property_id,
        url=request.url,
    )

@app.get("/valuation/{valuation_id}/approved/count")
async def get_approved_count(valuation_id: str):
    return {"approved_count": await utils.get_approved_count(valuation_id=valuation_id)}

@app.post("/valuation/{valuation_id}/search-round/increment")
async def increment_search_round(valuation_id: str):
    return await utils.increment_search_round(valuation_id=valuation_id)

@app.get("/valuation/{valuation_id}/approved/unmaterialized")
async def get_approved_without_materialization(valuation_id: str, limit: int = 50):
    return await utils.get_approved_without_materialization(valuation_id=valuation_id, limit=limit)

@app.post("/valuation/{valuation_id}/candidates/{item_id}/materialized")
async def mark_materialized(valuation_id: str, item_id: str):
    return await utils.set_candidates_description(valuation_id=valuation_id, item_id=item_id)

@app.get("/valuation/{valuation_id}/approved/without-proof")
async def get_approved_without_proof(valuation_id: str, limit: int = 50):
    return await utils.get_approved_without_proof(valuation_id=valuation_id, limit=limit)

@app.patch("/valuation/{valuation_id}/candidates/{item_id}/external_proof")
async def save_external_proof(request: ProofPatchRequest):
    return await utils.save_external_proof_result(
        valuation_id=request.valuation_id,
        item_id=request.item_id,
        external_proof_path=request.external_proof_path,
        proof_error=request.proof_error,
    )

@app.get("/valuation/{valuation_id}/proof/without-minio")
async def get_proof_without_minio(valuation_id: str, limit: int = 50):
    return await utils.get_proof_without_minio(valuation_id=valuation_id, limit=limit)

@app.patch("/valuation/{valuation_id}/candidates/{item_id}/minio")
async def save_minio(request: MinioPatchRequest):
    return await utils.save_proof_result(
        valuation_id=request.valuation_id,
        item_id=request.item_id,
        proof_path=request.proof_path,
    )

@app.post("/valuation/{valuation_id}/complete")
async def complete_run(valuation_id: str):
    return await utils.complete_run(valuation_id=valuation_id)

@app.get("/valuation/{valuation_id}/results")
async def get_result_by_run_id(valuation_id: str):
    return await utils.get_valuation_result(valuation_id=valuation_id)

@app.get("/valuation/object/{external_object_id}")
async def get_result_by_external_object_id(external_object_id: str):
    return await utils.get_valuation_result(external_object_id=external_object_id)