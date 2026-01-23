"""
Knowledge Graph API Routes
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import json
import os
from ..graph.graph_builder import GraphBuilder
from ..graph.graph_analyzer import GraphAnalyzer
from ..utils.config import ANALYSIS_DIR

router = APIRouter(prefix="/graph", tags=["graph"])

# In-memory cache for generated graphs
graph_cache = {}


class PathRequest(BaseModel):
    """Request model for path finding"""
    source_id: str
    target_id: str


@router.post("/build/{session_id}")
async def build_graph(session_id: str):
    """
    Build knowledge graph from research session

    Args:
        session_id: Research session ID

    Returns:
        Graph data with nodes and edges
    """
    try:
        # Load session data
        session_file = os.path.join(ANALYSIS_DIR, f"research_{session_id}.json")

        if not os.path.exists(session_file):
            raise HTTPException(status_code=404, detail="Research session not found")

        with open(session_file, 'r', encoding='utf-8') as f:
            session_data = json.load(f)

        # Build graph
        builder = GraphBuilder()
        graph_data = await builder.build_from_session(session_data)

        if "error" in graph_data:
            raise HTTPException(status_code=400, detail=graph_data["error"])

        # Cache the graph
        graph_cache[session_id] = graph_data

        return {
            "success": True,
            "session_id": session_id,
            "graph": graph_data,
            "message": "Knowledge graph built successfully"
        }

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Session file not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph building failed: {str(e)}")


@router.get("/data/{session_id}")
async def get_graph_data(session_id: str):
    """
    Retrieve graph data for a session

    Args:
        session_id: Research session ID

    Returns:
        Graph data
    """
    try:
        # Check cache first
        if session_id in graph_cache:
            return {
                "success": True,
                "session_id": session_id,
                "graph": graph_cache[session_id],
                "cached": True
            }

        # Try to build if not cached
        session_file = os.path.join(ANALYSIS_DIR, f"research_{session_id}.json")

        if not os.path.exists(session_file):
            raise HTTPException(status_code=404, detail="Research session not found")

        with open(session_file, 'r', encoding='utf-8') as f:
            session_data = json.load(f)

        # Build graph
        builder = GraphBuilder()
        graph_data = await builder.build_from_session(session_data)

        # Cache it
        graph_cache[session_id] = graph_data

        return {
            "success": True,
            "session_id": session_id,
            "graph": graph_data,
            "cached": False
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve graph: {str(e)}")


@router.get("/analyze/{session_id}")
async def analyze_graph(session_id: str):
    """
    Analyze graph and compute metrics

    Args:
        session_id: Research session ID

    Returns:
        Analysis results with metrics and insights
    """
    try:
        # Get graph data
        if session_id not in graph_cache:
            # Build graph first
            session_file = os.path.join(ANALYSIS_DIR, f"research_{session_id}.json")

            if not os.path.exists(session_file):
                raise HTTPException(status_code=404, detail="Research session not found")

            with open(session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)

            builder = GraphBuilder()
            graph_data = await builder.build_from_session(session_data)
            graph_cache[session_id] = graph_data
        else:
            graph_data = graph_cache[session_id]

        # Analyze graph
        analyzer = GraphAnalyzer(graph_data)
        analysis_results = analyzer.analyze()

        return {
            "success": True,
            "session_id": session_id,
            "analysis": analysis_results
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph analysis failed: {str(e)}")


@router.post("/find-path/{session_id}")
async def find_path(session_id: str, path_request: PathRequest):
    """
    Find shortest path between two nodes

    Args:
        session_id: Research session ID
        path_request: Source and target node IDs

    Returns:
        Path information
    """
    try:
        # Get graph data
        if session_id not in graph_cache:
            raise HTTPException(
                status_code=404,
                detail="Graph not found. Please build graph first."
            )

        graph_data = graph_cache[session_id]

        # Find path
        analyzer = GraphAnalyzer(graph_data)
        path_info = analyzer.find_shortest_path(
            path_request.source_id,
            path_request.target_id
        )

        return {
            "success": True,
            "session_id": session_id,
            "path": path_info
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Path finding failed: {str(e)}")


@router.get("/clusters/{session_id}")
async def get_clusters(session_id: str):
    """
    Get community clusters from graph

    Args:
        session_id: Research session ID

    Returns:
        Community detection results
    """
    try:
        # Get graph data
        if session_id not in graph_cache:
            # Build graph first
            session_file = os.path.join(ANALYSIS_DIR, f"research_{session_id}.json")

            if not os.path.exists(session_file):
                raise HTTPException(status_code=404, detail="Research session not found")

            with open(session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)

            builder = GraphBuilder()
            graph_data = await builder.build_from_session(session_data)
            graph_cache[session_id] = graph_data
        else:
            graph_data = graph_cache[session_id]

        # Detect communities
        analyzer = GraphAnalyzer(graph_data)
        communities = analyzer.detect_communities()

        return {
            "success": True,
            "session_id": session_id,
            "communities": communities,
            "total_clusters": len(communities)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cluster detection failed: {str(e)}")


@router.get("/central-nodes/{session_id}")
async def get_central_nodes(session_id: str, top_k: int = 10):
    """
    Get most central/influential nodes

    Args:
        session_id: Research session ID
        top_k: Number of top nodes to return

    Returns:
        Central nodes by different metrics
    """
    try:
        # Get graph data
        if session_id not in graph_cache:
            # Build graph first
            session_file = os.path.join(ANALYSIS_DIR, f"research_{session_id}.json")

            if not os.path.exists(session_file):
                raise HTTPException(status_code=404, detail="Research session not found")

            with open(session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)

            builder = GraphBuilder()
            graph_data = await builder.build_from_session(session_data)
            graph_cache[session_id] = graph_data
        else:
            graph_data = graph_cache[session_id]

        # Find central nodes
        analyzer = GraphAnalyzer(graph_data)
        central_nodes = analyzer.find_central_nodes(top_k=top_k)

        return {
            "success": True,
            "session_id": session_id,
            "central_nodes": central_nodes
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Central node analysis failed: {str(e)}")


@router.delete("/cache/{session_id}")
async def clear_graph_cache(session_id: str):
    """
    Clear cached graph data for a session

    Args:
        session_id: Research session ID

    Returns:
        Success message
    """
    if session_id in graph_cache:
        del graph_cache[session_id]
        return {
            "success": True,
            "message": f"Graph cache cleared for session {session_id}"
        }
    else:
        return {
            "success": True,
            "message": "No cached graph found for this session"
        }
