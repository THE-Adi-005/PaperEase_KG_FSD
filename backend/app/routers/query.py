"""Query endpoints — SSE-streamed reasoning with the KG agent."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import json
import logging

from app.models.schemas import QueryRequest, QueryMode
from app.services.agent import run_agent
from app.services.lazy_completion import get_metrics as get_lazy_metrics

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/query")
async def query_papers(request: QueryRequest):
    """Ask a question about selected papers.
    
    Returns an SSE stream of reasoning steps + final answer.
    
    Event types:
    - thought: Agent's reasoning step
    - action: Agent's chosen action
    - observation: Result from the KG
    - lazy_completion: Targeted re-extraction was triggered
    - answer: Final answer
    - subgraph: KG subgraph used in reasoning
    - error: Error during reasoning
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    if not request.paper_ids:
        raise HTTPException(status_code=400, detail="At least one paper must be selected")

    async def event_stream():
        try:
            async for event in run_agent(
                question=request.question,
                paper_ids=request.paper_ids,
                mode=request.mode,
            ):
                event_type = event.get("event", "data")
                event_data = event.get("data", {})
                yield f"event: {event_type}\ndata: {json.dumps(event_data)}\n\n"
        except Exception as e:
            logger.error(f"Query error: {e}", exc_info=True)
            yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"

        # Send done event
        yield f"event: done\ndata: {json.dumps({})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/compare")
async def compare_papers(request: QueryRequest):
    """Cross-paper comparison query. Same SSE format as /query."""
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    if len(request.paper_ids) < 2:
        raise HTTPException(
            status_code=400,
            detail="At least two papers must be selected for comparison"
        )

    request.mode = QueryMode.COMPARE

    async def event_stream():
        try:
            async for event in run_agent(
                question=request.question,
                paper_ids=request.paper_ids,
                mode=QueryMode.COMPARE,
            ):
                event_type = event.get("event", "data")
                event_data = event.get("data", {})
                yield f"event: {event_type}\ndata: {json.dumps(event_data)}\n\n"
        except Exception as e:
            logger.error(f"Compare error: {e}", exc_info=True)
            yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"

        yield f"event: done\ndata: {json.dumps({})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/metrics/lazy-completion")
async def lazy_completion_metrics():
    """Get lazy completion metrics for evaluation."""
    return get_lazy_metrics()
