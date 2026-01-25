"""
Knowledge Graph API Routes
Integrated with SQL Server database
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import json
import os
from ..graph.graph_builder import GraphBuilder
from ..graph.graph_analyzer import GraphAnalyzer
from ..utils.config import ANALYSIS_DIR
from ..services.db_service import get_db_service

router = APIRouter(prefix="/graph", tags=["graph"])

# In-memory cache for generated graphs (for performance)
graph_cache = {}


class PathRequest(BaseModel):
    """Request model for path finding"""
    source_id: str
    target_id: str


@router.post("/build/{session_id}")
async def build_graph(session_id: str, user_id: Optional[int] = None):
    """
    Build knowledge graph from research session

    Args:
        session_id: Research session ID
        user_id: Optional user ID for audit

    Returns:
        Graph data with nodes and edges
    """
    db_service = get_db_service()

    try:
        # Try to load session data from database first
        session = db_service.get_session_details(session_id)

        if session:
            # Get analyses from database
            analyses = db_service.get_session_analyses(session_id)
            essay = db_service.get_session_essay(session_id)

            print(f"[Graph] Loaded {len(analyses)} analyses from database for session {session_id}")

            session_data = {
                'query': session['query'],
                'analyses': analyses if analyses else [],
                'essay': essay.get('full_content') if essay else None
            }
        else:
            # Fallback to file-based data
            session_file = os.path.join(ANALYSIS_DIR, f"research_{session_id}.json")

            if not os.path.exists(session_file):
                raise HTTPException(status_code=404, detail="Research session not found")

            with open(session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)

        # Build graph
        builder = GraphBuilder()
        graph_data = await builder.build_from_session(session_data)

        # Save to database (non-fatal)
        try:
            db_service.save_graph(session_id, graph_data, user_id)
        except Exception as e:
            print(f"[Graph] Warning: Failed to save graph to DB: {e}")

        # Cache the graph
        graph_cache[session_id] = graph_data

        return {
            "success": True,
            "session_id": session_id,
            "graph": graph_data,
            "message": "Knowledge graph built and saved successfully",
            "stats": {
                "nodes": len(graph_data.get('nodes', [])),
                "edges": len(graph_data.get('edges', []))
            }
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
    db_service = get_db_service()

    try:
        # Check cache first
        if session_id in graph_cache:
            return {
                "success": True,
                "session_id": session_id,
                "graph": graph_cache[session_id],
                "source": "cache"
            }

        # Check database for existing graph
        try:
            db_graph = db_service.get_session_graph(session_id)
            if db_graph:
                graph_cache[session_id] = db_graph
                return {
                    "success": True,
                    "session_id": session_id,
                    "graph": db_graph,
                    "source": "database"
                }
        except Exception as e:
            print(f"[Graph] DB graph lookup failed: {e}")

        # Try to build from file or database
        session_data = None
        session_file = os.path.join(ANALYSIS_DIR, f"research_{session_id}.json")

        if os.path.exists(session_file):
            with open(session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
        else:
            # Try database
            try:
                session = db_service.get_session_details(session_id)
                if session:
                    analyses = db_service.get_session_analyses(session_id)
                    essay = db_service.get_session_essay(session_id)
                    session_data = {
                        'query': session['query'],
                        'analyses': analyses if analyses else [],
                        'essay': essay.get('full_content') if essay else None
                    }
            except Exception as e:
                print(f"[Graph] DB session lookup failed: {e}")

        if not session_data:
            raise HTTPException(status_code=404, detail="Research session not found")

        # Build graph
        builder = GraphBuilder()
        graph_data = await builder.build_from_session(session_data)

        # Save to cache (DB save is non-fatal)
        graph_cache[session_id] = graph_data
        try:
            db_service.save_graph(session_id, graph_data)
        except Exception as e:
            print(f"[Graph] Warning: Failed to save graph to DB: {e}")

        return {
            "success": True,
            "session_id": session_id,
            "graph": graph_data,
            "source": "built"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[Graph] Error: {e}")
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
    db_service = get_db_service()

    try:
        # Get graph data
        graph_data = await _get_or_build_graph(session_id, db_service)

        # Analyze graph
        analyzer = GraphAnalyzer(graph_data)
        analysis_results = analyzer.analyze()

        # Update centrality in database if available
        if analysis_results.get('centrality'):
            db_service.update_graph_centrality(session_id, analysis_results['centrality'])

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
    db_service = get_db_service()

    try:
        # Get graph data
        graph_data = await _get_or_build_graph(session_id, db_service)

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
    db_service = get_db_service()

    try:
        # Get graph data
        graph_data = await _get_or_build_graph(session_id, db_service)

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
    db_service = get_db_service()

    try:
        # Try to get from database first
        db_session_id = db_service.get_session_id(session_id)
        if db_session_id:
            central_nodes = db_service.graph.get_central_nodes(db_session_id, limit=top_k)
            if central_nodes:
                return {
                    "success": True,
                    "session_id": session_id,
                    "central_nodes": central_nodes,
                    "source": "database"
                }

        # Fallback to computed analysis
        graph_data = await _get_or_build_graph(session_id, db_service)

        analyzer = GraphAnalyzer(graph_data)
        central_nodes = analyzer.find_central_nodes(top_k=top_k)

        return {
            "success": True,
            "session_id": session_id,
            "central_nodes": central_nodes,
            "source": "computed"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Central node analysis failed: {str(e)}")


@router.get("/stats/{session_id}")
async def get_graph_stats(session_id: str):
    """
    Get graph statistics

    Args:
        session_id: Research session ID

    Returns:
        Graph statistics
    """
    db_service = get_db_service()

    try:
        db_session_id = db_service.get_session_id(session_id)
        if db_session_id:
            stats = db_service.graph.get_graph_stats(db_session_id)
            return {
                "success": True,
                "session_id": session_id,
                "stats": stats
            }

        raise HTTPException(status_code=404, detail="Graph not found for this session")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {str(e)}")


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


async def _get_or_build_graph(session_id: str, db_service) -> Dict[str, Any]:
    """Helper to get or build graph data"""

    # Check cache first
    if session_id in graph_cache:
        return graph_cache[session_id]

    # Check database for existing graph
    db_graph = db_service.get_session_graph(session_id)
    if db_graph:
        graph_cache[session_id] = db_graph
        return db_graph

    # Try to build from file first
    session_file = os.path.join(ANALYSIS_DIR, f"research_{session_id}.json")
    session_data = None

    if os.path.exists(session_file):
        with open(session_file, 'r', encoding='utf-8') as f:
            session_data = json.load(f)
    else:
        # Fallback: Build from database data
        session = db_service.get_session_details(session_id)
        if session:
            analyses = db_service.get_session_analyses(session_id)
            essay = db_service.get_session_essay(session_id)
            session_data = {
                'query': session['query'],
                'analyses': analyses if analyses else [],
                'essay': essay.get('full_content') if essay else None
            }

    if not session_data:
        raise HTTPException(status_code=404, detail="Research session not found")

    builder = GraphBuilder()
    graph_data = await builder.build_from_session(session_data)

    # Save and cache (non-fatal DB save)
    try:
        db_service.save_graph(session_id, graph_data)
    except Exception as e:
        print(f"[Graph] Warning: Failed to save graph to DB: {e}")

    graph_cache[session_id] = graph_data

    return graph_data
