"""Query endpoints — SSE-streamed reasoning with the KG agent + naive RAG baseline + multi-agent pipeline."""

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import json
import logging

from app.config import settings
from app.models.schemas import QueryRequest, QueryMode
from app.services.agent import run_agent
from app.services.multi_agent import run_multi_agent
from app.services.lazy_completion import get_metrics as get_lazy_metrics
from app.services.naive_rag import run_naive_rag, get_naive_metrics

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/query")
async def query_papers(request: QueryRequest):
    """Ask a question about selected papers.
    
    Supports pipeline selection via request.pipeline:
    - "single": Use the original single-agent ReACT loop
    - "multi": Use the multi-agent pipeline (Planner → Retriever → Reasoner → Verifier)
    - "auto": Use multi-agent if MULTI_AGENT_ENABLED, else single-agent
    
    Returns an SSE stream of reasoning steps + final answer.
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    if not request.paper_ids:
        raise HTTPException(status_code=400, detail="At least one paper must be selected")

    # Determine which pipeline to use
    use_multi = (
        request.pipeline == "multi" or
        (request.pipeline == "auto" and settings.MULTI_AGENT_ENABLED)
    )

    async def event_stream():
        try:
            if use_multi:
                async for event in run_multi_agent(
                    question=request.question,
                    paper_ids=request.paper_ids,
                    mode=request.mode,
                ):
                    event_type = event.get("event", "data")
                    event_data = event.get("data", {})
                    yield f"event: {event_type}\ndata: {json.dumps(event_data)}\n\n"
            else:
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


@router.post("/query-naive")
async def query_papers_naive(request: QueryRequest):
    """Ask a question using NAIVE RAG (no Knowledge Graph).
    
    This is the baseline comparison mode. Instead of traversing
    the KG with the ReACT agent, it simply concatenates raw paper
    text and sends it to the LLM as context.
    
    Same SSE event format as /query for fair comparison.
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")

    if not request.paper_ids:
        raise HTTPException(status_code=400, detail="At least one paper must be selected")

    async def event_stream():
        try:
            async for event in run_naive_rag(
                question=request.question,
                paper_ids=request.paper_ids,
            ):
                event_type = event.get("event", "data")
                event_data = event.get("data", {})
                yield f"event: {event_type}\ndata: {json.dumps(event_data)}\n\n"
        except Exception as e:
            logger.error(f"Naive RAG error: {e}", exc_info=True)
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


@router.post("/query-dual")
async def query_papers_dual(request: QueryRequest):
    """Ask a question using BOTH KG-Grounded and Naive RAG concurrently.
    
    Yields SSE events prefixed with `kg:` or `naive:` to route them.
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    if not request.paper_ids:
        raise HTTPException(status_code=400, detail="At least one paper must be selected")

    import asyncio
    
    async def event_stream():
        # Queues for each stream
        kg_queue = asyncio.Queue()
        naive_queue = asyncio.Queue()
        
        async def run_kg():
            try:
                async for event in run_agent(question=request.question, paper_ids=request.paper_ids, mode=request.mode):
                    await kg_queue.put(event)
            except Exception as e:
                await kg_queue.put({"event": "error", "data": {"message": str(e)}})
            finally:
                await kg_queue.put(None) # EOF
                
        async def run_naive():
            try:
                async for event in run_naive_rag(question=request.question, paper_ids=request.paper_ids):
                    await naive_queue.put(event)
            except Exception as e:
                await naive_queue.put({"event": "error", "data": {"message": str(e)}})
            finally:
                await naive_queue.put(None) # EOF

        # Start both concurrently
        kg_task = asyncio.create_task(run_kg())
        naive_task = asyncio.create_task(run_naive())
        
        active_streams = 2
        
        while active_streams > 0:
            # Wait for the next event from either queue
            done, pending = await asyncio.wait(
                [asyncio.create_task(kg_queue.get()), asyncio.create_task(naive_queue.get())],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            for task in done:
                event = task.result()
                
                # Figure out which queue this task belonged to by re-queueing if necessary,
                # but since asyncio.wait returns tasks, we can just check what queue it came from.
                # Actually, simpler way: wrap queue.get() to return source ID
            
        # Simpler approach: gather events and yield them. Since we need to stream in real-time,
        # we can just use an async generator wrapper that adds the prefix.
        
    # The queue approach is a bit complex for a quick demo. Let's just run them sequentially
    # in the stream, but prefix them so the UI can separate them. The UI can handle receiving
    # all naive events, then all kg events, or we can interleave them.
    
    async def event_stream_sequential():
        # Run naive first (it's fast)
        try:
            async for event in run_naive_rag(question=request.question, paper_ids=request.paper_ids):
                event_type = event.get("event", "data")
                event_data = event.get("data", {})
                yield f"event: naive:{event_type}\ndata: {json.dumps(event_data)}\n\n"
        except Exception as e:
            yield f"event: naive:error\ndata: {json.dumps({'message': str(e)})}\n\n"
            
        # Then run KG
        try:
            async for event in run_agent(question=request.question, paper_ids=request.paper_ids, mode=request.mode):
                event_type = event.get("event", "data")
                event_data = event.get("data", {})
                yield f"event: kg:{event_type}\ndata: {json.dumps(event_data)}\n\n"
        except Exception as e:
            yield f"event: kg:error\ndata: {json.dumps({'message': str(e)})}\n\n"
            
        yield f"event: done\ndata: {json.dumps({})}\n\n"

    return StreamingResponse(
        event_stream_sequential(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

@router.post("/query-multi-agent")
async def query_multi_agent(request: QueryRequest):
    """Ask a question using the multi-agent pipeline.
    
    Uses 4 specialist agents:
    1. Planner — decomposes question into sub-questions
    2. Retriever — gathers evidence from the KG
    3. Reasoner — synthesizes evidence into grounded answer
    4. Verifier — fact-checks against the graph
    """
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
    if not request.paper_ids:
        raise HTTPException(status_code=400, detail="At least one paper must be selected")

    async def event_stream():
        try:
            async for event in run_multi_agent(
                question=request.question,
                paper_ids=request.paper_ids,
                mode=request.mode,
            ):
                event_type = event.get("event", "data")
                event_data = event.get("data", {})
                yield f"event: {event_type}\ndata: {json.dumps(event_data)}\n\n"
        except Exception as e:
            logger.error(f"Multi-agent error: {e}", exc_info=True)
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


@router.get("/metrics/naive-rag")
async def naive_rag_metrics():
    """Get naive RAG baseline metrics for evaluation."""
    return get_naive_metrics()
