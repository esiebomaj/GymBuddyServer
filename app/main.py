from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import auth, health, settings, visits, waitlist


@asynccontextmanager
async def lifespan(app: FastAPI):
    get_settings()  # validate env vars on startup
    yield


app = FastAPI(title="GymBuddy API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(settings.router)
app.include_router(visits.router)
app.include_router(waitlist.router)