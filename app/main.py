from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from app.handlers.vk_callback import router as vk_router
from app.services.excel_export import EXPORT_DIR


app = FastAPI(title="Kitchen VK Bot", version="0.1.0")
app.include_router(vk_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.get("/exports/{filename}")
async def download_export(filename: str) -> FileResponse:
    if "/" in filename or "\\" in filename:
        raise HTTPException(status_code=404, detail="File not found")
    path = EXPORT_DIR / filename
    if not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        path,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
