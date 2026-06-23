"""BYOC server for Agent Runtime.

Implements /api/reasoning_engine and /api/stream_reasoning_engine
endpoints that Agent Runtime's sidecar routes requests to.
"""

import asyncio
import json
import logging
import os
import traceback

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response, StreamingResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

_engine = None
_init_done = False


def _get_engine():
    global _engine, _init_done
    if _init_done:
        return _engine
    _init_done = True
    try:
        logger.info("Initializing AgentEngineApp...")
        from academic_research.agent_runtime_app import agent_runtime
        try:
            agent_runtime.set_up()
            logger.info("set_up() succeeded")
        except Exception as e:
            logger.warning(f"set_up() failed (continuing): {e}")
        _engine = agent_runtime
    except Exception as e:
        logger.error(f"Failed to import agent: {e}\n{traceback.format_exc()}")
        _engine = None
    return _engine


@app.get("/")
async def root():
    return Response(content="OK", media_type="text/plain")


@app.get("/is_busy")
async def is_busy():
    return JSONResponse(content={"is_busy": False})


@app.post("/api/reasoning_engine")
async def reasoning_engine(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

    class_method = body.get("class_method", "")
    input_data = body.get("input", {})
    logger.info(f"reasoning_engine: class_method={class_method}")

    engine = _get_engine()
    if engine is None:
        return JSONResponse(status_code=500, content={"error": "Agent engine failed to initialize"})

    method = getattr(engine, class_method, None)
    if method is None:
        available = [m for m in dir(engine) if not m.startswith("_") and callable(getattr(engine, m, None))]
        return JSONResponse(status_code=400, content={"error": f"Method '{class_method}' not found. Available: {available}"})

    try:
        if asyncio.iscoroutinefunction(method):
            result = await method(**input_data)
        else:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, lambda: method(**input_data))

        if result is None:
            return Response(content=json.dumps(None), media_type="application/json")
        if isinstance(result, (dict, list, str, int, float, bool)):
            return Response(content=json.dumps(result), media_type="application/json")
        try:
            return Response(content=json.dumps(result.__dict__), media_type="application/json")
        except (TypeError, AttributeError):
            return Response(content=json.dumps(str(result)), media_type="application/json")
    except Exception as e:
        logger.error(f"Error in {class_method}: {e}\n{traceback.format_exc()}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/stream_reasoning_engine")
async def stream_reasoning_engine(request: Request):
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON body"})

    class_method = body.get("class_method", "")
    input_data = body.get("input", {})
    logger.info(f"stream_reasoning_engine: class_method={class_method}")

    engine = _get_engine()
    if engine is None:
        return JSONResponse(status_code=500, content={"error": "Agent engine failed to initialize"})

    method = getattr(engine, class_method, None)
    if method is None:
        return JSONResponse(status_code=400, content={"error": f"Method '{class_method}' not found."})

    async def generate():
        try:
            if asyncio.iscoroutinefunction(method):
                result = method(**input_data)
                if hasattr(result, "__aiter__"):
                    async for chunk in result:
                        if isinstance(chunk, dict):
                            yield json.dumps(chunk) + "\n"
                        else:
                            try:
                                yield json.dumps(chunk.__dict__) + "\n"
                            except (TypeError, AttributeError):
                                yield json.dumps({"data": str(chunk)}) + "\n"
                else:
                    r = await result
                    yield json.dumps(r if isinstance(r, dict) else {"data": str(r)}) + "\n"
            else:
                for chunk in method(**input_data):
                    if isinstance(chunk, dict):
                        yield json.dumps(chunk) + "\n"
                    else:
                        try:
                            yield json.dumps(chunk.__dict__) + "\n"
                        except (TypeError, AttributeError):
                            yield json.dumps({"data": str(chunk)}) + "\n"
        except Exception as e:
            logger.error(f"Stream error in {class_method}: {e}\n{traceback.format_exc()}")
            yield json.dumps({"error": str(e)}) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    logger.info(f"Starting BYOC server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
