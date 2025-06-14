import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from uuid import uuid4
from typing import Dict
import asyncio
from dotenv import load_dotenv

sentry_sdk.init(
    dsn="https://f5ae0e05a8a21b76ea8398cc3457b42a@o4509494426402816.ingest.de.sentry.io/4509494432432208",
    integrations=[FastApiIntegration()],
    send_default_pii=True,
)

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

# Allow CORS for React UI (adjust origins as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Only allow React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared in-memory dictionary to store logs for each job_id
sync_logs: Dict[str, list] = {}


@app.post("/sync")
async def start_sync(background_tasks: BackgroundTasks):
    job_id = str(uuid4())
    sync_logs[job_id] = []
    background_tasks.add_task(sync_youtube_to_spotify, job_id)
    return {"job_id": job_id}


async def sync_youtube_to_spotify(job_id: str):
    # Simulate sync process with log updates
    for i in range(1, 6):
        sync_logs[job_id].append(f"Step {i}/5: Syncing...")
        await asyncio.sleep(1)
    sync_logs[job_id].append("Sync complete!")


@app.get("/sync/{job_id}")
async def stream_logs(request: Request, job_id: str):
    async def event_generator():
        last_index = 0
        while True:
            if await request.is_disconnected():
                break
            logs = sync_logs.get(job_id, [])
            if last_index < len(logs):
                for log in logs[last_index:]:
                    yield f"data: {log}\n\n"
                last_index = len(logs)
            await asyncio.sleep(0.5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
