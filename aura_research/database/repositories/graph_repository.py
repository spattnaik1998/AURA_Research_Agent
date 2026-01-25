"""
Graph Repository
Database operations for GraphNodes and GraphEdges tables
"""

from typing import Optional, List, Dict, Any, Tuple
from .base_repository import BaseRepository


class GraphRepository(BaseRepository):
    """Repository for knowledge graph operations."""

    @property
    def table_name(self) -> str:
        return "GraphNodes"

    @property
    def primary_key(self) -> str:
        return "node_id"

    # ==================== Node Methods ====================

    def create_node(
        self,
        session_id: int,
        node_type: str,
        node_key: str,
        label: str,
        properties: Optional[Dict] = None
    ) -> int:
        """Create a new graph node."""
        query = """
            INSERT INTO GraphNodes
            (session_id, node_type, node_key, label, properties)
            VALUES (?, ?, ?, ?, ?)
        """
        return self.db.insert_and_get_id(
            query,
            (session_id, node_type, node_key, label, self.to_json(properties))
        )

    def create_nodes_bulk(
        self,
        session_id: int,
        nodes: List[Dict]
    ) -> int:
        """Bulk insert nodes for a session."""
        query = """
            INSERT INTO GraphNodes
            (session_id, node_type, node_key, label, properties)
            VALUES (?, ?, ?, ?, ?)
        """
        params_list = [
            (
                session_id,
                n.get('type'),
                n.get('key') or n.get('id'),
                n.get('label'),
                self.to_json(n.get('properties'))
            )
            for n in nodes
        ]
        return self.db.execute_many(query, params_list)

    def get_node_by_key(
        self,
        session_id: int,
        node_type: str,
        node_key: str
    ) -> Optional[Dict[str, Any]]:
        """Get node by session, type, and key."""
        query = """
            SELECT * FROM GraphNodes
            WHERE session_id = ? AND node_type = ? AND node_key = ?
        """
        result = self.db.fetch_one(query, (session_id, node_type, node_key))
        if result and result.get('properties'):
            result['properties'] = self.from_json(result['properties'])
        return result

    def get_nodes_by_session(self, session_id: int) -> List[Dict[str, Any]]:
        """Get all nodes for a session."""
        query = "SELECT * FROM GraphNodes WHERE session_id = ?"
        results = self.db.fetch_all(query, (session_id,))
        for r in results:
            if r.get('properties'):
                r['properties'] = self.from_json(r['properties'])
        return results

    def get_nodes_by_type(
        self,
        session_id: int,
        node_type: str
    ) -> List[Dict[str, Any]]:
        """Get nodes by type within a session."""
        query = """
            SELECT * FROM GraphNodes
            WHERE session_id = ? AND node_type = ?
        """
        results = self.db.fetch_all(query, (session_id, node_type))
        for r in results:
            if r.get('properties'):
                r['properties'] = self.from_json(r['properties'])
        return results

    def update_node_centrality(
        self,
        node_id: int,
        degree: Optional[float] = None,
        pagerank: Optional[float] = None,
        betweenness: Optional[float] = None
    ) -> bool:
        """Update centrality metrics for a node."""
        query = """
            UPDATE GraphNodes
            SET centrality_degree = ?,
                centrality_pagerank = ?,
                centrality_betweenness = ?
            WHERE node_id = ?
        """
        rows_affected = self.db.execute(
            query,
            (degree, pagerank, betweenness, node_id)
        )
        return rows_affected > 0

    def update_node_community(self, node_id: int, community_id: int) -> bool:
        """Update community assignment for a node."""
        query = "UPDATE GraphNodes SET community_id = ? WHERE node_id = ?"
        rows_affected = self.db.execute(query, (community_id, node_id))
        return rows_affected > 0

    def get_central_nodes(
        self,
        session_id: int,
        metric: str = 'pagerank',
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get top central nodes by specified metric."""
        column_map = {
            'pagerank': 'centrality_pagerank',
            'degree': 'centrality_degree',
            'betweenness': 'centrality_betweenness'
        }
        column = column_map.get(metric, 'centrality_pagerank')

        query = f"""
            SELECT * FROM GraphNodes
            WHERE session_id = ? AND {column} IS NOT NULL
            ORDER BY {column} DESC
            OFFSET 0 ROWS FETCH NEXT ? ROWS ONLY
        """
        results = self.db.fetch_all(query, (session_id, limit))
        for r in results:
            if r.get('properties'):
                r['properties'] = self.from_json(r['properties'])
        return results

    def get_nodes_by_community(
        self,
        session_id: int,
        community_id: int
    ) -> List[Dict[str, Any]]:
        """Get all nodes in a community."""
        query = """
            SELECT * FROM GraphNodes
            WHERE session_id = ? AND community_id = ?
        """
        results = self.db.fetch_all(query, (session_id, community_id))
        for r in results:
            if r.get('properties'):
                r['properties'] = self.from_json(r['properties'])
        return results

    # ==================== Edge Methods ====================

    def create_edge(
        self,
        session_id: int,
        source_node_id: int,
        target_node_id: int,
        edge_type: str,
        weight: float = 1.0,
        properties: Optional[Dict] = None
    ) -> int:
        """Create a new graph edge."""
        query = """
            INSERT INTO GraphEdges
            (session_id, source_node_id, target_node_id, edge_type, weight, properties)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        return self.db.insert_and_get_id(
            query,
            (session_id, source_node_id, target_node_id, edge_type, weight, self.to_json(properties))
        )

    def create_edges_bulk(
        self,
        session_id: int,
        edges: List[Dict]
    ) -> int:
        """Bulk insert edges for a session."""
        query = """
            INSERT INTO GraphEdges
            (session_id, source_node_id, target_node_id, edge_type, weight, properties)
            VALUES (?, ?, ?, ?, ?, ?)
        """
        params_list = [
            (
                session_id,
                e.get('source_id'),
                e.get('target_id'),
                e.get('type'),
                e.get('weight', 1.0),
                self.to_json(e.get('properties'))
            )
            for e in edges
        ]
        return self.db.execute_many(query, params_list)

    def get_edges_by_session(self, session_id: int) -> List[Dict[str, Any]]:
        """Get all edges for a session."""
        query = """
            SELECT e.*,
                   sn.label as source_label, sn.node_type as source_type,
                   tn.label as target_label, tn.node_type as target_type
            FROM GraphEdges e
            JOIN GraphNodes sn ON e.source_node_id = sn.node_id
            JOIN GraphNodes tn ON e.target_node_id = tn.node_id
            WHERE e.session_id = ?
        """
        results = self.db.fetch_all(query, (session_id,))
        for r in results:
            if r.get('properties'):
                r['properties'] = self.from_json(r['properties'])
        return results

    def get_node_edges(
        self,
        node_id: int
    ) -> List[Dict[str, Any]]:
        """Get all edges connected to a node."""
        query = """
            SELECT e.*,
                   sn.label as source_label,
                   tn.label as target_label
            FROM GraphEdges e
            JOIN GraphNodes sn ON e.source_node_id = sn.node_id
            JOIN GraphNodes tn ON e.target_node_id = tn.node_id
            WHERE e.source_node_id = ? OR e.target_node_id = ?
        """
        return self.db.fetch_all(query, (node_id, node_id))

    def get_edges_by_type(
        self,
        session_id: int,
        edge_type: str
    ) -> List[Dict[str, Any]]:
        """Get edges by type within a session."""
        query = """
            SELECT * FROM GraphEdges
            WHERE session_id = ? AND edge_type = ?
        """
        return self.db.fetch_all(query, (session_id, edge_type))

    # ==================== Graph Data Methods ====================

    def get_full_graph(self, session_id: int) -> Dict[str, Any]:
        """Get complete graph data for visualization."""
        nodes = self.get_nodes_by_session(session_id)
        edges = self.get_edges_by_session(session_id)

        return {
            'nodes': [
                {
                    'id': n['node_id'],
                    'key': n['node_key'],
                    'type': n['node_type'],
                    'label': n['label'],
                    'properties': n.get('properties', {}),
                    'centrality': {
                        'degree': n.get('centrality_degree'),
                        'pagerank': n.get('centrality_pagerank'),
                        'betweenness': n.get('centrality_betweenness')
                    },
                    'community': n.get('community_id')
                }
                for n in nodes
            ],
            'edges': [
                {
                    'id': e['edge_id'],
                    'source': e['source_node_id'],
                    'target': e['target_node_id'],
                    'type': e['edge_type'],
                    'weight': float(e['weight']) if e.get('weight') else 1.0,
                    'source_label': e.get('source_label'),
                    'target_label': e.get('target_label')
                }
                for e in edges
            ]
        }

    def get_graph_stats(self, session_id: int) -> Dict[str, Any]:
        """Get graph statistics."""
        node_query = """
            SELECT
                COUNT(*) as total_nodes,
                COUNT(DISTINCT node_type) as node_types,
                COUNT(DISTINCT community_id) as communities
            FROM GraphNodes
            WHERE session_id = ?
        """
        edge_query = """
            SELECT
                COUNT(*) as total_edges,
                COUNT(DISTINCT edge_type) as edge_types,
                AVG(weight) as avg_weight
            FROM GraphEdges
            WHERE session_id = ?
        """

        node_stats = self.db.fetch_one(node_query, (session_id,))
        edge_stats = self.db.fetch_one(edge_query, (session_id,))

        return {
            'nodes': node_stats,
            'edges': edge_stats
        }

    def delete_graph_by_session(self, session_id: int) -> Tuple[int, int]:
        """Delete all graph data for a session."""
        edges_deleted = self.db.execute(
            "DELETE FROM GraphEdges WHERE session_id = ?",
            (session_id,)
        )
        nodes_deleted = self.db.execute(
            "DELETE FROM GraphNodes WHERE session_id = ?",
            (session_id,)
        )
        return nodes_deleted, edges_deleted

    def graph_exists(self, session_id: int) -> bool:
        """Check if graph data exists for a session."""
        query = "SELECT 1 FROM GraphNodes WHERE session_id = ?"
        result = self.db.fetch_one(query, (session_id,))
        return result is not None
