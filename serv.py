import asyncio
import json
import os
import uuid
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# Import the Pipeline and Registry classes directly
from lib import PipelineRegistry
from lib.translate import translate_product_data

app = FastAPI(
    title="1Click Oversea API",
    description="API for extracting product data from Chinese e-commerce sites",
    version="0.1.0",
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory for the demo page
app.mount("/static", StaticFiles(directory="static"), name="static")

# In-memory job store
jobs: Dict[str, Dict[str, Any]] = {}


# Helper to update job progress
def update_job_progress(job_id: str, progress_data: Dict[str, Any]):
    if job_id in jobs:
        jobs[job_id]["progress"] = progress_data
        print(f"Job {job_id} progress update: {progress_data.get('status')}")


# Background job processor
async def process_job(job_id: str, url: str, pipeline_name: str, translate: bool = False):
    try:
        # Get the pipeline
        pipeline = PipelineRegistry.get(pipeline_name)

        if not pipeline:
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = f"Pipeline '{pipeline_name}' not found"
            return

        # Configure pipeline delay
        if pipeline.run_config and hasattr(pipeline.run_config, "delay_before_return_html"):
            pipeline.run_config.delay_before_return_html = 2  # Use a shorter delay for API

        # Update job status
        jobs[job_id]["status"] = "extracting"
        update_job_progress(job_id, {"stage": "extraction", "status": "started", "url": url})

        # Run extraction
        data = await pipeline.run(url=url)

        # Store extracted data
        jobs[job_id]["data"] = data
        jobs[job_id]["status"] = "extracted"
        update_job_progress(job_id, {"stage": "extraction", "status": "completed", "total_items": len(data)})

        # Run translation if requested
        if translate:
            jobs[job_id]["status"] = "translating"
            update_job_progress(job_id, {"stage": "translation", "status": "started"})

            # Translate with progress updates
            translated_data = await translate_product_data(
                data, progress_callback=lambda progress: update_job_progress(job_id, progress)
            )

            # Store translated data
            jobs[job_id]["translated_data"] = translated_data
            jobs[job_id]["status"] = "completed"
            last_progress = jobs[job_id]["progress"]
            update_job_progress(
                job_id,
                {
                    "stage": "all",
                    "status": "completed",
                    "total_items": last_progress["total_items"],
                    "translated": last_progress["translated"],
                    "not_needed": last_progress["not_needed"],
                    "missed": last_progress["missed"],
                },
            )
        else:
            # Mark job as completed if no translation requested
            jobs[job_id]["status"] = "completed"
            update_job_progress(job_id, {"stage": "all", "status": "completed"})

    except Exception as e:
        # Handle any errors
        jobs[job_id]["status"] = "failed"
        jobs[job_id]["error"] = str(e)
        update_job_progress(job_id, {"stage": "error", "status": "failed", "error": str(e)})


@app.get("/demo", response_class=HTMLResponse)
async def get_demo_page():
    with open("static/index.html", "r") as f:
        return f.read()


@app.get("/extract")
async def extract_product_data(
    url: str = Query(..., description="Product URL to scrape"),
    pipeline_name: str = Query("alibaba_1688", description="Pipeline name to use"),
    translate: bool = Query(False, description="Translate product data"),
    wait_for: int = Query(2, description="Delay before returning HTML (seconds), lower is faster but less reliable"),
):
    try:
        # For translation requests, create an async job and return job ID
        if translate:
            job_id = str(uuid.uuid4())
            jobs[job_id] = {
                "status": "queued",
                "url": url,
                "pipeline": pipeline_name,
                "translate": True,
                "created_at": asyncio.get_event_loop().time(),
                "progress": {"status": "queued"},
            }

            # Start background processing
            asyncio.create_task(process_job(job_id, url, pipeline_name, translate=True))

            # Return job ID for status polling
            return {
                "job_id": job_id,
                "status": "queued",
                "message": "Translation job started. Poll /job_status/{job_id} for updates.",
            }

        # For non-translation requests, process synchronously
        pipeline = PipelineRegistry.get(pipeline_name)

        if not pipeline:
            available = ", ".join(PipelineRegistry.list_pipelines())
            raise HTTPException(
                status_code=404, detail=f"Pipeline '{pipeline_name}' not found. Available pipelines: {available}"
            )

        # Update the delay_before_return_html in the run_config
        if pipeline.run_config and hasattr(pipeline.run_config, 'delay_before_return_html'):
            pipeline.run_config.delay_before_return_html = wait_for

        # Run the pipeline in headless mode
        result = await pipeline.run(url=url)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


@app.get("/job_status/{job_id}")
async def get_job_status(job_id: str):
    """Get the status of a processing job"""
    if job_id not in jobs:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    job = jobs[job_id]

    # Basic response with job status
    response = {
        "job_id": job_id,
        "status": job["status"],
        "progress": job.get("progress", {}),
    }

    # Include additional data based on status
    if job["status"] == "failed":
        response["error"] = job.get("error", "Unknown error")

    if job["status"] in ["extracted", "completed"]:
        response["data"] = job.get("data")

    if job["status"] == "completed" and job.get("translate", False):
        response["translated_data"] = job.get("translated_data")

    return response


@app.websocket("/ws/extract")
async def websocket_extract(websocket: WebSocket):
    """WebSocket endpoint for real-time extraction and translation updates"""
    await websocket.accept()

    try:
        # Wait for the initial request data
        request_data = await websocket.receive_json()
        url = request_data.get("url")
        pipeline_name = request_data.get("pipeline", "alibaba_1688")
        translate = request_data.get("translate", False)
        wait_for = request_data.get("wait_for", 2)  # Default to 2 seconds

        if not url:
            await websocket.send_json({"error": "URL is required"})
            await websocket.close()
            return

        # Create a job ID
        job_id = str(uuid.uuid4())

        # Initialize job
        jobs[job_id] = {
            "status": "queued",
            "url": url,
            "pipeline": pipeline_name,
            "translate": translate,
            "created_at": asyncio.get_event_loop().time(),
            "progress": {"status": "queued"},
        }

        # Send initial status
        await websocket.send_json({"job_id": job_id, "status": "queued", "message": "Job started"})

        # Get the pipeline
        pipeline = PipelineRegistry.get(pipeline_name)

        if not pipeline:
            await websocket.send_json(
                {"job_id": job_id, "status": "failed", "error": f"Pipeline '{pipeline_name}' not found"}
            )
            await websocket.close()
            return

        # Configure pipeline
        if pipeline.run_config and hasattr(pipeline.run_config, "delay_before_return_html"):
            pipeline.run_config.delay_before_return_html = wait_for

        # Extraction phase
        try:
            # Update status
            jobs[job_id]["status"] = "extracting"
            await websocket.send_json(
                {"job_id": job_id, "status": "extracting", "progress": {"stage": "extraction", "status": "started"}}
            )

            # Run extraction
            data = await pipeline.run(url=url)

            # Store and send extracted data
            jobs[job_id]["data"] = data
            jobs[job_id]["status"] = "extracted"

            await websocket.send_json(
                {
                    "job_id": job_id,
                    "status": "extracted",
                    "progress": {"stage": "extraction", "status": "completed"},
                    "data": data,
                }
            )

            # Translation phase if requested
            if translate:
                # Update status
                jobs[job_id]["status"] = "translating"
                await websocket.send_json(
                    {
                        "job_id": job_id,
                        "status": "translating",
                        "progress": {"stage": "translation", "status": "started"},
                    }
                )

                # Create an event to signal when the final update is done
                final_update_done = asyncio.Event()

                # Define async progress callback for WebSocket
                async def ws_progress_callback(progress_data):
                    update_job_progress(job_id, progress_data)
                    await websocket.send_json({"job_id": job_id, "status": "translating", "progress": progress_data})

                    # Check if this is the final update
                    if progress_data.get("status") == "completed":
                        final_update_done.set()

                # Translate with progress reporting via WebSocket
                translated_data = await translate_product_data(
                    data, progress_callback=lambda p: asyncio.create_task(ws_progress_callback(p))
                )

                # Store and send translated data
                jobs[job_id]["translated_data"] = translated_data
                jobs[job_id]["status"] = "completed"

                # Wait for the final progress update to be processed
                await final_update_done.wait()

                # Now it's safe to send final data and close connection
                await websocket.send_json(
                    {
                        "job_id": job_id,
                        "status": "completed",
                        "progress": {"stage": "all", "status": "completed"},
                        "data": data,
                        "translated_data": translated_data,
                    }
                )

        except Exception as e:
            # Handle errors
            error_msg = str(e)
            jobs[job_id]["status"] = "failed"
            jobs[job_id]["error"] = error_msg

            await websocket.send_json({"job_id": job_id, "status": "failed", "error": error_msg})

    except WebSocketDisconnect:
        # Handle client disconnect
        print("WebSocket client disconnected")
    except Exception as e:
        # Handle other errors
        try:
            await websocket.send_json({"error": f"An error occurred: {str(e)}"})
        except RuntimeError:
            pass


if __name__ == "__main__":
    # Run the server
    uvicorn.run("serv:app", host="0.0.0.0", port=8000, reload=True)
