# DVS backend entry point

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import earthquakes, fires, gdacs

app = FastAPI(title="DVS API", description="Disaster Visualization System — Asia")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(earthquakes.router)
app.include_router(fires.router)
app.include_router(gdacs.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}