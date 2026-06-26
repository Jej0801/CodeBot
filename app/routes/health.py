from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from app.database import check_db_connection
import time

router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Basic health check endpoint.

    Returns 200 OK if the service is running.
    Used by load balancers for basic service availability.
    """
    return {"status": "healthy", "service": "CodeBot API"}


@router.get("/health/ready")
async def readiness_check():
    """
    Readiness check endpoint.

    Verifies that the service is ready to accept traffic by:
    - Checking database connectivity
    - Verifying critical dependencies

    This is used by Kubernetes readiness probes.

    Returns:
    - 200 OK if service is ready
    - 503 Service Unavailable if not ready
    """
    start_time = time.time()
    db_healthy = await check_db_connection()
    response_time = time.time() - start_time

    if db_healthy:
        return {
            "status": "ready",
            "checks": {
                "database": "healthy",
            },
            "response_time_ms": round(response_time * 1000, 2),
        }
    else:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "checks": {
                    "database": "unhealthy",
                },
                "response_time_ms": round(response_time * 1000, 2),
            },
        )


@router.get("/health/live")
async def liveness_check():
    """
    Liveness check endpoint.

    Verifies that the service process is alive and not deadlocked.
    This is used by Kubernetes liveness probes.

    If this fails, Kubernetes will restart the pod.

    Returns:
    - 200 OK if service is alive
    """
    return {"status": "alive", "service": "CodeBot API"}