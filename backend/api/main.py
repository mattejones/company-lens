from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes.companies import router as companies_router

app = FastAPI(
    title="Company Lens",
    description="Enrich Companies House data with verified domain information.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(companies_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
