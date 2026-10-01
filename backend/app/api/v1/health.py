from typing import Dict
from fastapi import APIRouter
from app.schemas.common import ApiResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=ApiResponse[Dict[str, str]])
async def health_check():
    """
    Service health check endpoint to verify backend connectivity.
    """
    return ApiResponse.success_response(
        data={
            "status": "healthy",
            "service": "walkthrough-backend",
        }
    )
