"""BYOC server for Agent Runtime.

Wraps the ADK agent to serve the endpoints that Agent Runtime
routes requests to for custom containers.
"""

import asyncio
import json
import logging
import os
import traceback

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

_agent_engine = None
_init_error = None


def get_agent_engine():
    global _agent_engine, _init_error
    if _agent_engine is not None:
        return _agent_engine
    if _init_error is not None:
        raise _init_error
    try:
        logger.info("Initializing agent engine...")
        from academic_research.agent_runtime_app import agent_runtime
        try:
            agent_runtime.set_up()
            logger.info("Agent engine set_up() completed.")
        except Exception as e:
            logger.warning(f"set_up() failed (non-fatal in BYOC): {e}")
        _agent_engine = agent_runtime
        return _agent_engine
    except Exception as e:
        _init_error = e
        logger.error(f"Failed to initialize agent engine: {e}\n{traceback.format_exc()}")
        raise


@app.get("/")
async def health():
    return {"status": "healthy"}


@app.get("/is_busy")
async def is_busy():
    return {"is_busy": False}


@app.post("/api/reasoning_engine")
async def reasoning_engine(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})

    class_method = body.get("class_method", "")
    input_data = body.get("input", {})

    try:
        engine = get_agent_engine()
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Agent init failed: {str(e)}"})

    method = getattr(engine, class_method, None)
    if method is None:
        available = [m for m in dir(engine) if not m.startswith("_") and callable(getattr(engine, m, None))]
        return JSONResponse(status_code=400, content={"error": f"Method '{class_method}' not found. Available: {available}"})

    try:
        if asyncio.iscoroutinefunction(method):
            result = await method(**input_data)
        else:
            result = method(**input_data)

        if result is None:
            return JSONResponse(content={"result": None})
        if isinstance(result, (dict, list)):
            return JSONResponse(content=result)
        return JSONResponse(content={"result": str(result)})
    except Exception as e:
        logger.error(f"Error calling {class_method}: {e}\n{traceback.format_exc()}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/stream_reasoning_engine")
async def stream_reasoning_engine(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})

    class_method = body.get("class_method", "")
    input_data = body.get("input", {})

    try:
        engine = get_agent_engine()
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Agent init failed: {str(e)}"})

    method = getattr(engine, class_method, None)
    if method is None:
        return JSONResponse(status_code=400, content={"error": f"Method '{class_method}' not found."})

    async def event_stream():
        try:
            if asyncio.iscoroutinefunction(method):
                async for chunk in method(**input_data):
                    data = chunk if isinstance(chunk, dict) else {"chunk": str(chunk)}
                    yield json.dumps(data) + "\n"
            else:
                for chunk in method(**input_data):
                    data = chunk if isinstance(chunk, dict) else {"chunk": str(chunk)}
                    yield json.dumps(data) + "\n"
        except Exception as e:
            yield json.dumps({"error": str(e)}) + "\n"

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", "8080"))
    logger.info(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
