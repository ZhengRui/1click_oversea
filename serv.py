import asyncio
import json
import os
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Query

# Import the Pipeline and Registry classes directly
from lib import PipelineRegistry

app = FastAPI(
    title="1Click Oversea API",
    description="API for extracting product data from Chinese e-commerce sites",
    version="0.1.0",
)


@app.get("/")
def get_root():
    return {"message": "Welcome to 1Click Oversea API. Use /extract endpoint to extract product data."}


@app.get("/extract")
async def extract_product_data(
    url: str = Query(..., description="Product URL to scrape"),
    pipeline_name: str = Query("alibaba_1688", description="Pipeline name to use"),
    translate: bool = Query(False, description="Translate product data"),
    wait_for: int = Query(2, description="Delay before returning HTML (seconds), lower is faster but less reliable"),
):
    try:
        # Get the pipeline from the registry
        pipeline = PipelineRegistry.get(pipeline_name)

        if not pipeline:
            raise HTTPException(
                status_code=404,
                detail=(
                    f"Pipeline '{pipeline_name}' not found. Available pipelines: {PipelineRegistry.list_pipelines()}"
                ),
            )

        # Update the delay_before_return_html in the run_config
        if pipeline.run_config and hasattr(pipeline.run_config, 'delay_before_return_html'):
            pipeline.run_config.delay_before_return_html = wait_for

        # Run the pipeline in headless mode
        result = await pipeline.run(url=url)

        # TODO: If translate feature is needed, implement it here

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An error occurred: {str(e)}")


if __name__ == "__main__":
    # Run the server
    uvicorn.run("serv:app", host="0.0.0.0", port=8000, reload=True)
