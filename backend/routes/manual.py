import os
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

router = APIRouter(prefix="/manual", tags=["manual"])

PDF_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "manuel_utilisation_dynpharma.pdf")


@router.get("/download")
async def download_manual():
    if not os.path.exists(PDF_PATH):
        raise HTTPException(status_code=404, detail="Manuel non disponible")
    return FileResponse(
        PDF_PATH,
        media_type="application/pdf",
        filename="Manuel_Utilisation_DynPharma.pdf",
    )
