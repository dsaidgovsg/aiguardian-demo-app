#!/usr/bin/env python
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from constants import VERSION

app = FastAPI(docs_url=None, redoc_url=None)

origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


if __name__ == "__main__":
    import multiprocessing
    import uvicorn

    multiprocessing.set_start_method("spawn")

    # Set the number of workers based on available CPUs, capped at 4
    num_workers = min(multiprocessing.cpu_count(), 4)

    uvicorn.run(
        "app.langserve_app:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "8000")),
        reload=(os.environ.get("ENABLE_RELOAD", "false") == "true"),
        reload_includes=["apps/routes.yml"],
        # workers=num_workers,
    )
