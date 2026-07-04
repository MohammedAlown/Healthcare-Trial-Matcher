from fastapi import APIRouter
router = APIRouter(prefix="/documents", tags=["Documents"])

@router.get("/stats")
async def document_stats():
    return {"total_documents": 0, "total_chunks": 0}
