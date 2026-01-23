"""
Graph Builder for AURA Knowledge Graph
Constructs graph from research session data
"""

from typing import Dict, Any, List, Set, Tuple
import json
import re
from collections import defaultdict
import asyncio


class GraphBuilder:
    """
    Builds knowledge graph from research analysis results
    """

    def __init__(self):
        self.nodes = []
        self.edges = []
        self.node_index = {}  # For quick lookup

    async def build_from_session(self, session_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build complete knowledge graph from research session

        Args:
            session_data: Complete research session results

        Returns:
            Graph data with nodes and edges
        """
        # Extract all analyses
        analyses = self._extract_analyses(session_data)

        if not analyses:
            return {"nodes": [], "edges": [], "error": "No analyses found"}

        # Build different node types
        await self._build_paper_nodes(analyses)
        await self._build_concept_nodes(analyses)
        await self._build_author_nodes(analyses)
        await self._build_method_nodes(analyses)

        # Build edges (relationships)
        await self._build_edges(analyses)

        return {
            "nodes": self.nodes,
            "edges": self.edges,
            "stats": self._get_graph_stats()
        }

    def _extract_analyses(self, session_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract all paper analyses from session data"""
        analyses = []

        # Get subordinate results
        subordinate_results = session_data.get("subordinate_results", [])

        for result in subordinate_results:
            if result.get("status") == "completed":
                result_data = result.get("result", {})
                result_analyses = result_data.get("analyses", [])
                analyses.extend(result_analyses)

        return analyses

    async def _build_paper_nodes(self, analyses: List[Dict[str, Any]]):
        """Create nodes for each research paper"""
        for idx, analysis in enumerate(analyses):
            # Extract citation info
            citations = analysis.get("citations", [{}])
            citation = citations[0] if citations else {}

            metadata = analysis.get("metadata", {})

            node = {
                "id": f"paper_{idx}",
                "type": "paper",
                "label": citation.get("title", f"Paper {idx+1}"),
                "group": "paper",
                "summary": analysis.get("summary", ""),
                "authors": citation.get("authors", "Unknown"),
                "year": citation.get("year", "N/A"),
                "source": citation.get("source", ""),
                "metrics": {
                    "relevance_score": metadata.get("relevance_score", 5),
                    "citations": 0,  # Will be updated if citation data available
                    "influence": 0.5  # Default, will be computed
                },
                "metadata": {
                    "domain": metadata.get("research_domain", "Unknown"),
                    "technical_depth": metadata.get("technical_depth", "applied"),
                    "key_points": analysis.get("key_points", [])[:3]  # Top 3 points
                }
            }

            self.nodes.append(node)
            self.node_index[node["id"]] = len(self.nodes) - 1

    async def _build_concept_nodes(self, analyses: List[Dict[str, Any]]):
        """Create nodes for key concepts/topics"""
        concept_frequency = defaultdict(int)
        concept_papers = defaultdict(set)

        # Extract concepts from all papers
        for idx, analysis in enumerate(analyses):
            metadata = analysis.get("metadata", {})
            core_ideas = metadata.get("core_ideas", [])

            for idea in core_ideas:
                # Clean and normalize concept
                concept = self._normalize_concept(idea)
                if concept and len(concept) > 3:  # Filter out very short concepts
                    concept_frequency[concept] += 1
                    concept_papers[concept].add(f"paper_{idx}")

        # Create nodes for concepts that appear in multiple papers or are significant
        for concept, frequency in concept_frequency.items():
            if frequency >= 1:  # Include all concepts for now
                node = {
                    "id": f"concept_{len([n for n in self.nodes if n['type'] == 'concept'])}",
                    "type": "concept",
                    "label": concept,
                    "group": "concept",
                    "metrics": {
                        "frequency": frequency,
                        "centrality": frequency / len(analyses),  # Normalized frequency
                        "papers": list(concept_papers[concept])
                    }
                }
                self.nodes.append(node)
                self.node_index[node["id"]] = len(self.nodes) - 1

    async def _build_author_nodes(self, analyses: List[Dict[str, Any]]):
        """Create nodes for authors"""
        author_info = defaultdict(lambda: {"papers": [], "domains": set()})

        for idx, analysis in enumerate(analyses):
            citations = analysis.get("citations", [{}])
            citation = citations[0] if citations else {}
            authors_str = citation.get("authors", "Unknown")

            if authors_str and authors_str != "Unknown" and "not provided" not in authors_str.lower():
                # Extract individual authors (simple split for now)
                authors = self._extract_author_names(authors_str)

                metadata = analysis.get("metadata", {})
                domain = metadata.get("research_domain", "Unknown")

                for author in authors:
                    author_info[author]["papers"].append(f"paper_{idx}")
                    if domain != "Unknown":
                        author_info[author]["domains"].add(domain)

        # Create author nodes
        for author, info in author_info.items():
            if len(info["papers"]) > 0:  # Only authors with papers
                node = {
                    "id": f"author_{len([n for n in self.nodes if n['type'] == 'author'])}",
                    "type": "author",
                    "label": author,
                    "group": "author",
                    "metrics": {
                        "paper_count": len(info["papers"]),
                        "domains": list(info["domains"]),
                        "papers": info["papers"]
                    }
                }
                self.nodes.append(node)
                self.node_index[node["id"]] = len(self.nodes) - 1

    async def _build_method_nodes(self, analyses: List[Dict[str, Any]]):
        """Create nodes for research methods/techniques"""
        method_frequency = defaultdict(int)
        method_papers = defaultdict(set)

        for idx, analysis in enumerate(analyses):
            metadata = analysis.get("metadata", {})
            methodology = metadata.get("methodology", "")

            # Extract methods from methodology description
            methods = self._extract_methods(methodology)

            for method in methods:
                method_frequency[method] += 1
                method_papers[method].add(f"paper_{idx}")

        # Create nodes for methods that appear multiple times
        for method, frequency in method_frequency.items():
            if frequency >= 1 and len(method) > 3:
                node = {
                    "id": f"method_{len([n for n in self.nodes if n['type'] == 'method'])}",
                    "type": "method",
                    "label": method,
                    "group": "method",
                    "metrics": {
                        "frequency": frequency,
                        "usage_rate": frequency / len(analyses),
                        "papers": list(method_papers[method])
                    }
                }
                self.nodes.append(node)
                self.node_index[node["id"]] = len(self.nodes) - 1

    async def _build_edges(self, analyses: List[Dict[str, Any]]):
        """Build relationships between nodes"""
        # Paper to concept edges
        for idx, analysis in enumerate(analyses):
            paper_id = f"paper_{idx}"
            metadata = analysis.get("metadata", {})
            core_ideas = metadata.get("core_ideas", [])

            # Link papers to concepts
            for idea in core_ideas:
                concept = self._normalize_concept(idea)
                concept_node = self._find_node_by_label(concept, "concept")
                if concept_node:
                    self.edges.append({
                        "source": paper_id,
                        "target": concept_node["id"],
                        "type": "discusses",
                        "weight": 0.8
                    })

        # Paper to author edges
        for idx, analysis in enumerate(analyses):
            paper_id = f"paper_{idx}"
            citations = analysis.get("citations", [{}])
            citation = citations[0] if citations else {}
            authors_str = citation.get("authors", "Unknown")

            if authors_str and authors_str != "Unknown":
                authors = self._extract_author_names(authors_str)
                for author in authors:
                    author_node = self._find_node_by_label(author, "author")
                    if author_node:
                        self.edges.append({
                            "source": author_node["id"],
                            "target": paper_id,
                            "type": "authored",
                            "weight": 1.0
                        })

        # Paper to method edges
        for idx, analysis in enumerate(analyses):
            paper_id = f"paper_{idx}"
            metadata = analysis.get("metadata", {})
            methodology = metadata.get("methodology", "")

            methods = self._extract_methods(methodology)
            for method in methods:
                method_node = self._find_node_by_label(method, "method")
                if method_node:
                    self.edges.append({
                        "source": paper_id,
                        "target": method_node["id"],
                        "type": "uses_method",
                        "weight": 0.7
                    })

        # Concept co-occurrence edges (concepts appearing in same papers)
        concept_nodes = [n for n in self.nodes if n["type"] == "concept"]
        for i, concept1 in enumerate(concept_nodes):
            papers1 = set(concept1["metrics"]["papers"])
            for concept2 in concept_nodes[i+1:]:
                papers2 = set(concept2["metrics"]["papers"])
                overlap = papers1.intersection(papers2)

                if len(overlap) >= 1:  # Concepts appear together
                    self.edges.append({
                        "source": concept1["id"],
                        "target": concept2["id"],
                        "type": "related_to",
                        "weight": len(overlap) / max(len(papers1), len(papers2))
                    })

    def _normalize_concept(self, concept: str) -> str:
        """Normalize concept text"""
        if not concept:
            return ""
        # Remove common prefixes
        concept = re.sub(r'^(the|a|an)\s+', '', concept.lower())
        # Clean up
        concept = concept.strip()
        return concept

    def _extract_author_names(self, authors_str: str) -> List[str]:
        """Extract individual author names"""
        # Handle "et al." format
        if "et al" in authors_str.lower():
            # Extract first author
            first_author = re.sub(r'\s+et\s+al\.?.*', '', authors_str).strip()
            return [first_author] if first_author else []

        # Split by common separators
        authors = re.split(r'[,;]|\sand\s', authors_str)
        return [a.strip() for a in authors if a.strip()]

    def _extract_methods(self, methodology: str) -> List[str]:
        """Extract research methods from methodology description"""
        if not methodology or len(methodology) < 20:
            return []

        # Common research methods keywords
        method_keywords = [
            "machine learning", "deep learning", "neural network", "regression",
            "classification", "clustering", "survey", "experiment", "case study",
            "meta-analysis", "systematic review", "qualitative", "quantitative",
            "mixed methods", "simulation", "modeling", "statistical analysis",
            "data mining", "natural language processing", "computer vision",
            "reinforcement learning", "supervised learning", "unsupervised learning",
            "cross-sectional", "longitudinal", "randomized control", "rct",
            "ethnography", "grounded theory", "content analysis", "thematic analysis"
        ]

        methods = []
        methodology_lower = methodology.lower()

        for keyword in method_keywords:
            if keyword in methodology_lower:
                methods.append(keyword.title())

        return list(set(methods))  # Remove duplicates

    def _find_node_by_label(self, label: str, node_type: str = None) -> Dict[str, Any]:
        """Find node by label and optionally type"""
        for node in self.nodes:
            if node["label"].lower() == label.lower():
                if node_type is None or node["type"] == node_type:
                    return node
        return None

    def _get_graph_stats(self) -> Dict[str, Any]:
        """Calculate graph statistics"""
        node_types = defaultdict(int)
        edge_types = defaultdict(int)

        for node in self.nodes:
            node_types[node["type"]] += 1

        for edge in self.edges:
            edge_types[edge["type"]] += 1

        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "node_types": dict(node_types),
            "edge_types": dict(edge_types)
        }
