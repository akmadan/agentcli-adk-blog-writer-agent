"""BYOC server for Agent Runtime.

Wraps AgentEngineApp to serve the /api/reasoning_engine endpoints
that Agent Runtime expects from custom containers.
"""

import asyncio
import json
import logging
import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

_agent_engine = None


def get_agent_engine():
    global _agent_engine
    if _agent_engine is None:
        from academic_research.agent_runtime_app import agent_runtime
        agent_runtime.set_up()
        _agent_engine = agent_runtime
    return _agent_engine


@app.get("/")
async def health():
    return {"status": "healthy"}


@app.get("/is_busy")
async def is_busy():
    return {"is_busy": False}


@app.post("/api/reasoning_engine")
async def reasoning_engine(request: Request):
    body = await request.json()
    class_method = body.get("class_method", "")
    input_data = body.get("input", {})

    engine = get_agent_engine()
    method = getattr(engine, class_method, None)
    if method is None:
        return JSONResponse(
            status_code=400,
            content={"error": f"Method {class_method} not found. Available: {[m for m in dir(engine) if not m.startswith('_')]}"},
        )

    if asyncio.iscoroutinefunction(method):
        result = await method(**input_data)
    else:
        result = method(**input_data)

    return JSONResponse(content=result if isinstance(result, (dict, list)) else {"result": str(result)})


@app.post("/api/stream_reasoning_engine")
async def stream_reasoning_engine(request: Request):
    body = await request.json()
    class_method = body.get("class_method", "")
    input_data = body.get("input", {})

    engine = get_agent_engine()
    method = getattr(engine, class_method, None)
    if method is None:
        return JSONResponse(
            status_code=400,
            content={"error": f"Method {class_method} not found."},
        )

    async def event_stream():
        if asyncio.iscoroutinefunction(method):
            async for chunk in method(**input_data):
                yield json.dumps(chunk if isinstance(chunk, dict) else {"chunk": str(chunk)}) + "\n"
        else:
            for chunk in method(**input_data):
                yield json.dumps(chunk if isinstance(chunk, dict) else {"chunk": str(chunk)}) + "\n"

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
