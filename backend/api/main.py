from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes.companies import router as companies_router
from api.routes.inference import router as inference_router
from api.routes.jobs import router as jobs_router
from api.routes.lookups import router as lookups_router
from api.routes.dataset import router as dataset_router

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

# companies_router already carries prefix="/companies" internally
app.include_router(companies_router)
app.include_router(inference_router)
app.include_router(jobs_router)
app.include_router(lookups_router)
app.include_router(dataset_router)


@app.get("/health")
async def health():
    return {"status": "ok"}
