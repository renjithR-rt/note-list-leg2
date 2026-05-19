from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.modules.backend.router import router

app = FastAPI(title="Note List API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:8094"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
