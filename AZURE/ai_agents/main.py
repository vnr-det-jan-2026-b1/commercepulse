from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
import os
from dotenv import load_dotenv

# Ensure environment variables (.env) are loaded
load_dotenv()

from app.agents.graph import engine
from app.agents.state import SystemState

app = FastAPI(
    title="CommercePulse AI Agents API",
    description="REST API for triggering the multi-agent LangGraph workflows."
)

class SimulationRequest(BaseModel):
    seller_id: str
    time_window_start: str
    time_window_end: str
    snapshot_data: Dict[str, Any]

@app.post("/api/v1/simulate")
async def run_simulation(request: SimulationRequest):
    """
    Executes the 5-Agent LangGraph scenario based on standard JSON input.
    """
    if not os.getenv("GROQ_API_KEY"):
        raise HTTPException(status_code=500, detail="GROQ_API_KEY is not set.")
        
    initial_state: SystemState = {
        "seller_id": request.seller_id,
        "time_window_start": request.time_window_start,
        "time_window_end": request.time_window_end,
        "snapshot_data": request.snapshot_data,
        "revenue_insights": None,
        "ops_insights": None,
        "market_insights": None,
        "final_executive_plan": None
    }
    
    try:
        final_state = engine.invoke(initial_state)
        
        # Extract the Pydantic plan object output from the Synthesizer
        plan = final_state.get("final_executive_plan")
        if plan:
            return {
                "status": "success", 
                "seller_id": request.seller_id,
                "executive_plan": plan.model_dump()
            }
        else:
            return {"status": "partial", "message": "Graph completed but no executive plan was generated."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/simulate/stream")
async def run_simulation_stream(request: SimulationRequest):
    """
    Executes the 5-Agent LangGraph scenario and streams the output from the Synthesizer.
    """
    from fastapi.responses import StreamingResponse
    import json
    
    if not os.getenv("GROQ_API_KEY"):
        raise HTTPException(status_code=500, detail="GROQ_API_KEY is not set.")
        
    initial_state: SystemState = {
        "seller_id": request.seller_id,
        "time_window_start": request.time_window_start,
        "time_window_end": request.time_window_end,
        "snapshot_data": request.snapshot_data,
        "revenue_insights": None,
        "ops_insights": None,
        "market_insights": None,
        "final_executive_plan": None
    }
    
    async def generate():
        # Using astreams to get streaming events from langgraph
        try:
            async for event in engine.astream_events(initial_state, version="v2"):
                # We specifically want to stream the chat model tokens from the synthesizer node
                if event["event"] == "on_chat_model_stream":
                    # Check if this event came from our synthesizer node
                    tags = event.get("tags", [])
                    if "synthesizer" in tags or event["name"] == "ChatGroq":
                        chunk = event["data"]["chunk"]
                        if chunk.content:
                            yield f"data: {json.dumps({'content': chunk.content})}\n\n"
                            
            # Send a final 'done' event
            yield f"data: {json.dumps({'status': 'done'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            
    return StreamingResponse(generate(), media_type="text/event-stream")

class WhatIfRequest(BaseModel):
    seller_id: str
    scenario: str

@app.post("/api/v1/simulate/whatif")
async def run_whatif_stream(request: WhatIfRequest):
    """
    Executes a custom 'What-If' hypothetical scenario and streams the output from the Synthesizer.
    This bypasses standard automated snapshot triggers.
    """
    from fastapi.responses import StreamingResponse
    from datetime import date as _date, timedelta
    import json
    
    if not os.getenv("GROQ_API_KEY"):
        raise HTTPException(status_code=500, detail="GROQ_API_KEY is not set.")
        
    today = _date.today()
    # Create the state with the custom scenario injected into snapshot data
    initial_state: SystemState = {
        "seller_id": request.seller_id,
        "time_window_start": str(today - timedelta(days=7)),
        "time_window_end": str(today),
        "snapshot_data": {"user_hypothetical_scenario": request.scenario},
        "revenue_insights": None,
        "ops_insights": None,
        "market_insights": None,
        "marketing_insights": None,
        "final_executive_plan": None
    }
    
    async def generate():
        try:
            async for event in engine.astream_events(initial_state, version="v2"):
                if event["event"] == "on_chat_model_stream":
                    tags = event.get("tags", [])
                    if "synthesizer" in tags or event["name"] == "ChatGroq":
                        chunk = event["data"]["chunk"]
                        if chunk.content:
                            yield f"data: {json.dumps({'content': chunk.content})}\n\n"
            yield f"data: {json.dumps({'status': 'done'})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            
    return StreamingResponse(generate(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    # Can run this file directly via `python main.py`
    uvicorn.run(app, host="0.0.0.0", port=8001)
