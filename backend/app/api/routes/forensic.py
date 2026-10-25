
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.services.ingestion_service import ingest_forensic_csv
from app.services.analysis_service import execute_analysis


router = APIRouter(prefix="/forensic", tags=["Forensic"])


@router.post("/upload")
async def upload_forensic_csv(
    file: UploadFile = File(...),
    token_address: str = Form(...),
) -> dict:
    try:
        # 1. Ingest CSV and persist events
        ingestion_result = await ingest_forensic_csv(
            file=file,
            token_address=token_address,
        )

        # Analyze only wallets represented by this upload, including wallets
        # whose completed forensic history was reused during ingestion.
        wallet_addresses = {
            item["address"] for item in ingestion_result.get("data", [])
        } | set(ingestion_result.get("skipped_addresses", []))

        # 2. Run analysis after ingestion completes, scoped to this upload.
        analysis_result = execute_analysis(
            target_token_mint=token_address,
            wallet_addresses=wallet_addresses,
        )

        # 3. Return both results
        return {
            #"ingestion": ingestion_result,
            "analysis": analysis_result,
        }

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc
