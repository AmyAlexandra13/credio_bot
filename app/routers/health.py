from fastapi import APIRouter
from app.services.health_service import HealthService
from app.models.schemas import HealthResponse

router = APIRouter()

@router.get("/health", response_model=HealthResponse)
async def health_check():
    return HealthService.get_status()
