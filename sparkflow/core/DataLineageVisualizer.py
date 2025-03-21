import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from typing import Dict, Tuple, List


class DataLineageVisualizer:
    def __init__(self):
        pass

    def _process_dict(self, data_lineage: Dict[str, List[Tuple[str, List[str]]]]):
        def normalize_name(name):
            return name.replace(".sql", "")

        normalized_lineage = {}
        for file, connections in data_lineage.items():
            norm_file = normalize_name(file)
            normalized_connections = []
            for conn_type, deps in connections:
                norm_deps = [normalize_name(dep) for dep in deps]
                normalized_connections.append((conn_type, norm_deps))
            normalized_lineage[norm_file] = normalized_connections

        sql_files = list(normalized_lineage.keys())
        all_deps = []
        for connections in normalized_lineage.values():
            for conn_type, deps in connections:
                all_deps.extend(deps)
        all_nodes = set(sql_files + all_deps)

        node_types = {}
        for node in all_nodes:
            if node in sql_files:
                node_types[node] = "sql"
            else:
                node_types[node] = "source"

        return node_types, normalized_lineage

    def visualize(self, data_lineage: Dict[str, List[Tuple[str, List[str]]]]):
        G = nx.DiGraph()

        node_types, normalized_lineage = self._process_dict(data_lineage)

        for node, node_type in node_types.items():
            if node_type == "sql":
                G.add_node(node, color="lightblue", type="sql")
            else:
                G.add_node(node, color="lightgreen", type="source")

        for sql_file, connections in normalized_lineage.items():
            for connection_type, nodes in connections:
                for node in nodes:
                    if connection_type == "references":
                        G.add_edge(node, sql_file, color="red", type="references")
                    elif connection_type == "sources":
                        G.add_edge(node, sql_file, color="blue", type="sources")

        plt.figure(figsize=(12, 8))

        if nx.is_directed_acyclic_graph(G):
            generations = list(nx.topological_generations(G))
            max_layer = len(generations) - 1
            max_nodes = max(len(layer) for layer in generations)
            pos = {}
            for i, layer in enumerate(generations):
                m = len(layer)
                start_x = (max_nodes - m) / 2
                for j, node in enumerate(sorted(layer)):
                    pos[node] = (start_x + j, max_layer - i)
        else:
            print("Graph is not a DAG, using spring layout.")
            pos = nx.spring_layout(G, k=1.0, seed=42)

        sql_nodes = [node for node in G.nodes() if G.nodes[node]["type"] == "sql"]
        source_nodes = [node for node in G.nodes() if G.nodes[node]["type"] == "source"]
        nx.draw_networkx_nodes(
            G,
            pos,
            nodelist=sql_nodes,
            node_size=2000,
            node_color="lightblue",
            node_shape="o",
            alpha=0.8,
        )
        nx.draw_networkx_nodes(
            G,
            pos,
            nodelist=source_nodes,
            node_size=2000,
            node_color="lightgreen",
            node_shape="s",
            alpha=0.8,
        )

        ref_edges = [
            (u, v) for u, v, d in G.edges(data=True) if d["type"] == "references"
        ]
        src_edges = [(u, v) for u, v, d in G.edges(data=True) if d["type"] == "sources"]
        nx.draw_networkx_edges(
            G,
            pos,
            edgelist=ref_edges,
            width=2,
            alpha=0.7,
            edge_color="red",
            arrows=True,
            arrowsize=20,
        )
        nx.draw_networkx_edges(
            G,
            pos,
            edgelist=src_edges,
            width=2,
            alpha=0.7,
            edge_color="blue",
            arrows=True,
            arrowsize=20,
        )

        nx.draw_networkx_labels(G, pos, font_size=10, font_weight="bold")

        sql_patch = mpatches.Patch(color="lightblue", label="SQL Files")
        source_patch = mpatches.Patch(color="lightgreen", label="Source/Dependency")
        ref_patch = mpatches.Patch(color="red", label="References (incoming)")
        src_patch = mpatches.Patch(color="blue", label="Sources (data flow)")
        plt.legend(handles=[sql_patch, source_patch, ref_patch, src_patch], loc="best")

        plt.title("Data Lineage Graph Visualization", fontsize=15)
        plt.axis("off")
        plt.tight_layout()
        plt.show()
