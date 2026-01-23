"""
Graph Analyzer for AURA Knowledge Graph
Computes metrics, communities, and insights
"""

from typing import Dict, Any, List, Set, Tuple
from collections import defaultdict, deque
import math


class GraphAnalyzer:
    """
    Analyzes knowledge graph and computes metrics
    """

    def __init__(self, graph_data: Dict[str, Any]):
        self.nodes = graph_data.get("nodes", [])
        self.edges = graph_data.get("edges", [])
        self.adjacency = self._build_adjacency()

    def analyze(self) -> Dict[str, Any]:
        """
        Perform complete graph analysis

        Returns:
            Analysis results with metrics and insights
        """
        return {
            "node_metrics": self.compute_node_metrics(),
            "communities": self.detect_communities(),
            "central_nodes": self.find_central_nodes(),
            "insights": self.generate_insights()
        }

    def _build_adjacency(self) -> Dict[str, List[Dict[str, Any]]]:
        """Build adjacency list from edges"""
        adjacency = defaultdict(list)

        for edge in self.edges:
            source = edge["source"]
            target = edge["target"]
            weight = edge.get("weight", 1.0)

            adjacency[source].append({
                "node": target,
                "weight": weight,
                "type": edge.get("type", "unknown")
            })

            # For undirected relationships
            if edge.get("type") in ["related_to", "co_authored"]:
                adjacency[target].append({
                    "node": source,
                    "weight": weight,
                    "type": edge.get("type", "unknown")
                })

        return adjacency

    def compute_node_metrics(self) -> Dict[str, Dict[str, Any]]:
        """
        Compute metrics for each node

        Returns:
            Dict mapping node_id to metrics
        """
        metrics = {}

        # Compute degree centrality
        degree_centrality = self._compute_degree_centrality()

        # Compute PageRank
        pagerank = self._compute_pagerank()

        # Compute betweenness centrality (simplified)
        betweenness = self._compute_betweenness_centrality()

        # Combine metrics
        for node in self.nodes:
            node_id = node["id"]
            metrics[node_id] = {
                "degree_centrality": degree_centrality.get(node_id, 0),
                "pagerank": pagerank.get(node_id, 0),
                "betweenness_centrality": betweenness.get(node_id, 0),
                "influence_score": self._compute_influence_score(
                    degree_centrality.get(node_id, 0),
                    pagerank.get(node_id, 0),
                    betweenness.get(node_id, 0)
                )
            }

        return metrics

    def _compute_degree_centrality(self) -> Dict[str, float]:
        """Compute degree centrality for all nodes"""
        degree = defaultdict(int)

        for edge in self.edges:
            degree[edge["source"]] += 1
            degree[edge["target"]] += 1

        # Normalize
        max_degree = max(degree.values()) if degree else 1
        return {node_id: deg / max_degree for node_id, deg in degree.items()}

    def _compute_pagerank(self, damping=0.85, max_iter=100, tol=1e-6) -> Dict[str, float]:
        """
        Compute PageRank for all nodes

        Args:
            damping: Damping factor (default 0.85)
            max_iter: Maximum iterations
            tol: Convergence tolerance

        Returns:
            PageRank scores
        """
        # Initialize PageRank
        num_nodes = len(self.nodes)
        if num_nodes == 0:
            return {}

        pagerank = {node["id"]: 1.0 / num_nodes for node in self.nodes}

        # Build outgoing links
        outgoing = defaultdict(list)
        for edge in self.edges:
            outgoing[edge["source"]].append(edge["target"])

        # Iterate
        for iteration in range(max_iter):
            new_pagerank = {}
            max_diff = 0

            for node in self.nodes:
                node_id = node["id"]

                # Calculate incoming PageRank
                rank_sum = 0
                for other_node in self.nodes:
                    other_id = other_node["id"]
                    if node_id in outgoing[other_id]:
                        num_outgoing = len(outgoing[other_id])
                        if num_outgoing > 0:
                            rank_sum += pagerank[other_id] / num_outgoing

                # Update PageRank
                new_rank = (1 - damping) / num_nodes + damping * rank_sum
                new_pagerank[node_id] = new_rank

                # Track convergence
                max_diff = max(max_diff, abs(new_rank - pagerank[node_id]))

            pagerank = new_pagerank

            # Check convergence
            if max_diff < tol:
                break

        return pagerank

    def _compute_betweenness_centrality(self) -> Dict[str, float]:
        """
        Compute betweenness centrality (simplified version)

        Returns:
            Betweenness scores
        """
        betweenness = {node["id"]: 0.0 for node in self.nodes}

        # For each pair of nodes, find shortest paths
        for source_node in self.nodes:
            source_id = source_node["id"]

            # BFS to find shortest paths
            distances, paths = self._bfs_shortest_paths(source_id)

            # Update betweenness for intermediate nodes
            for target_node in self.nodes:
                target_id = target_node["id"]

                if source_id != target_id and target_id in paths:
                    path = paths[target_id]
                    # Count nodes in path (excluding source and target)
                    for intermediate in path[1:-1]:
                        betweenness[intermediate] += 1

        # Normalize
        max_betweenness = max(betweenness.values()) if any(betweenness.values()) else 1
        return {node_id: score / max_betweenness for node_id, score in betweenness.items()}

    def _bfs_shortest_paths(self, source: str) -> Tuple[Dict[str, int], Dict[str, List[str]]]:
        """
        BFS to find shortest paths from source

        Returns:
            Tuple of (distances, paths)
        """
        distances = {source: 0}
        paths = {source: [source]}
        queue = deque([source])

        while queue:
            current = queue.popleft()
            current_distance = distances[current]

            for neighbor_info in self.adjacency[current]:
                neighbor = neighbor_info["node"]

                if neighbor not in distances:
                    distances[neighbor] = current_distance + 1
                    paths[neighbor] = paths[current] + [neighbor]
                    queue.append(neighbor)

        return distances, paths

    def _compute_influence_score(self, degree: float, pagerank: float, betweenness: float) -> float:
        """
        Compute overall influence score

        Args:
            degree: Degree centrality
            pagerank: PageRank score
            betweenness: Betweenness centrality

        Returns:
            Weighted influence score
        """
        # Weighted combination
        return 0.3 * degree + 0.5 * pagerank + 0.2 * betweenness

    def detect_communities(self) -> List[Dict[str, Any]]:
        """
        Detect communities using label propagation

        Returns:
            List of communities with members
        """
        # Initialize: each node is its own community
        labels = {node["id"]: node["id"] for node in self.nodes}

        # Iterate until convergence
        max_iterations = 100
        for iteration in range(max_iterations):
            changed = False

            # Random order to avoid bias
            node_order = [node["id"] for node in self.nodes]

            for node_id in node_order:
                # Find most common label among neighbors
                neighbor_labels = []

                for neighbor_info in self.adjacency[node_id]:
                    neighbor = neighbor_info["node"]
                    weight = neighbor_info["weight"]
                    # Add label multiple times based on weight
                    neighbor_labels.extend([labels[neighbor]] * int(weight * 10))

                if neighbor_labels:
                    # Most common label
                    label_counts = defaultdict(int)
                    for label in neighbor_labels:
                        label_counts[label] += 1

                    most_common_label = max(label_counts.items(), key=lambda x: x[1])[0]

                    if labels[node_id] != most_common_label:
                        labels[node_id] = most_common_label
                        changed = True

            if not changed:
                break

        # Group nodes by community
        communities_dict = defaultdict(list)
        for node_id, label in labels.items():
            communities_dict[label].append(node_id)

        # Format communities
        communities = []
        for idx, (label, members) in enumerate(communities_dict.items()):
            if len(members) > 1:  # Only include communities with multiple members
                # Determine community theme based on node types
                community_nodes = [n for n in self.nodes if n["id"] in members]
                theme = self._determine_community_theme(community_nodes)

                communities.append({
                    "id": f"community_{idx}",
                    "size": len(members),
                    "members": members,
                    "theme": theme
                })

        return sorted(communities, key=lambda c: c["size"], reverse=True)

    def _determine_community_theme(self, nodes: List[Dict[str, Any]]) -> str:
        """Determine theme/topic of a community"""
        # Count node types
        type_counts = defaultdict(int)
        labels = []

        for node in nodes:
            type_counts[node["type"]] += 1
            if node["type"] in ["concept", "method"]:
                labels.append(node["label"])

        # Generate theme description
        if labels:
            return f"Cluster: {', '.join(labels[:3])}"
        else:
            return f"Research cluster ({type_counts['paper']} papers)"

    def find_central_nodes(self, top_k: int = 10) -> Dict[str, List[Dict[str, Any]]]:
        """
        Find most central/influential nodes

        Args:
            top_k: Number of top nodes to return

        Returns:
            Top nodes by different metrics
        """
        metrics = self.compute_node_metrics()

        # Sort by different metrics
        by_pagerank = sorted(
            metrics.items(),
            key=lambda x: x[1]["pagerank"],
            reverse=True
        )[:top_k]

        by_degree = sorted(
            metrics.items(),
            key=lambda x: x[1]["degree_centrality"],
            reverse=True
        )[:top_k]

        by_betweenness = sorted(
            metrics.items(),
            key=lambda x: x[1]["betweenness_centrality"],
            reverse=True
        )[:top_k]

        # Get node details
        node_map = {node["id"]: node for node in self.nodes}

        def format_node(node_id, metric_value):
            node = node_map.get(node_id, {})
            return {
                "id": node_id,
                "label": node.get("label", "Unknown"),
                "type": node.get("type", "unknown"),
                "score": metric_value
            }

        return {
            "most_influential": [
                format_node(node_id, m["pagerank"]) for node_id, m in by_pagerank
            ],
            "most_connected": [
                format_node(node_id, m["degree_centrality"]) for node_id, m in by_degree
            ],
            "key_bridges": [
                format_node(node_id, m["betweenness_centrality"]) for node_id, m in by_betweenness
            ]
        }

    def generate_insights(self) -> List[str]:
        """
        Generate human-readable insights from graph analysis

        Returns:
            List of insight statements
        """
        insights = []

        # Graph structure insights
        num_papers = len([n for n in self.nodes if n["type"] == "paper"])
        num_concepts = len([n for n in self.nodes if n["type"] == "concept"])
        num_authors = len([n for n in self.nodes if n["type"] == "author"])
        num_methods = len([n for n in self.nodes if n["type"] == "method"])

        insights.append(
            f"The research landscape contains {num_papers} papers, "
            f"{num_concepts} key concepts, {num_methods} research methods, "
            f"and {num_authors} identified authors."
        )

        # Community insights
        communities = self.detect_communities()
        if communities:
            largest_community = communities[0]
            insights.append(
                f"Found {len(communities)} research clusters. "
                f"The largest cluster contains {largest_community['size']} related nodes "
                f"focused on: {largest_community['theme']}."
            )

        # Central nodes
        central = self.find_central_nodes(top_k=3)
        if central["most_influential"]:
            top_node = central["most_influential"][0]
            insights.append(
                f"Most influential node: '{top_node['label']}' "
                f"({top_node['type']}) with influence score {top_node['score']:.3f}."
            )

        # Network density
        max_edges = len(self.nodes) * (len(self.nodes) - 1) / 2
        density = len(self.edges) / max_edges if max_edges > 0 else 0
        insights.append(
            f"Network density is {density:.2%}, indicating "
            f"{'a highly interconnected' if density > 0.3 else 'a moderately connected' if density > 0.1 else 'a sparse'} "
            f"research field."
        )

        return insights

    def find_shortest_path(self, source_id: str, target_id: str) -> Dict[str, Any]:
        """
        Find shortest path between two nodes

        Args:
            source_id: Source node ID
            target_id: Target node ID

        Returns:
            Path information
        """
        distances, paths = self._bfs_shortest_paths(source_id)

        if target_id in paths:
            path = paths[target_id]
            return {
                "exists": True,
                "path": path,
                "length": len(path) - 1,
                "nodes": [
                    next((n for n in self.nodes if n["id"] == node_id), {"label": node_id})
                    for node_id in path
                ]
            }
        else:
            return {
                "exists": False,
                "message": "No path found between these nodes"
            }
