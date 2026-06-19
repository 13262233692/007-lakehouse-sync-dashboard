import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

from app.config import settings
from app.connectors import StarRocksConnector
from app.connectors.starrocks_connector import StarRocksMaterializedView
from app.utils.sql_lineage_parser import (
    LineageEdge,
    LineageNode,
    SQLLineageParser,
)


logger = logging.getLogger(__name__)


@dataclass
class LineageDAG:
    nodes: Dict[str, LineageNode] = field(default_factory=dict)
    edges: List[LineageEdge] = field(default_factory=list)
    adjacency: Dict[str, List[str]] = field(default_factory=dict)
    reverse_adjacency: Dict[str, List[str]] = field(default_factory=dict)

    def add_node(self, node: LineageNode) -> None:
        if node.fqn not in self.nodes:
            self.nodes[node.fqn] = node
            self.adjacency[node.fqn] = []
            self.reverse_adjacency[node.fqn] = []

    def add_edge(self, edge: LineageEdge) -> None:
        self.add_node(LineageNode(
            fqn=edge.source_fqn,
            name=edge.source_fqn.split('.')[-1],
            node_type="unknown",
            storage_layer="unknown",
        ))
        self.add_node(LineageNode(
            fqn=edge.target_fqn,
            name=edge.target_fqn.split('.')[-1],
            node_type="unknown",
            storage_layer="unknown",
        ))
        self.edges.append(edge)
        if edge.target_fqn not in self.adjacency[edge.source_fqn]:
            self.adjacency[edge.source_fqn].append(edge.target_fqn)
        if edge.source_fqn not in self.reverse_adjacency[edge.target_fqn]:
            self.reverse_adjacency[edge.target_fqn].append(edge.source_fqn)

    def get_children(self, node_fqn: str) -> List[str]:
        return self.adjacency.get(node_fqn, [])

    def get_parents(self, node_fqn: str) -> List[str]:
        return self.reverse_adjacency.get(node_fqn, [])

    def has_cycle(self) -> bool:
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            for child in self.adjacency.get(node, []):
                if child not in visited:
                    if dfs(child):
                        return True
                elif child in rec_stack:
                    return True
            rec_stack.discard(node)
            return False

        for node in self.nodes:
            if node not in visited:
                if dfs(node):
                    return True
        return False

    def topological_sort(self) -> List[str]:
        in_degree: Dict[str, int] = {n: 0 for n in self.nodes}
        for node, children in self.adjacency.items():
            for child in children:
                in_degree[child] = in_degree.get(child, 0) + 1

        queue = deque([n for n, deg in in_degree.items() if deg == 0])
        result = []
        while queue:
            node = queue.popleft()
            result.append(node)
            for child in self.adjacency.get(node, []):
                in_degree[child] -= 1
                if in_degree[child] == 0:
                    queue.append(child)

        if len(result) != len(self.nodes):
            logger.warning("DAG has cycle, returning partial sort")
        return result

    def get_subgraph(self, node_fqn: str, depth: int = 3) -> "LineageDAG":
        sub = LineageDAG()
        visited: Set[str] = set()

        def bfs_up(start: str, d: int) -> None:
            queue = deque([(start, 0)])
            while queue:
                node, level = queue.popleft()
                if level > d or node in visited:
                    continue
                visited.add(node)
                if node in self.nodes:
                    sub.nodes[node] = self.nodes[node]
                for parent in self.reverse_adjacency.get(node, []):
                    if parent in self.nodes:
                        sub.nodes[parent] = self.nodes[parent]
                    queue.append((parent, level + 1))

        def bfs_down(start: str, d: int) -> None:
            queue = deque([(start, 0)])
            while queue:
                node, level = queue.popleft()
                if level > d or node in visited:
                    continue
                visited.add(node)
                if node in self.nodes:
                    sub.nodes[node] = self.nodes[node]
                for child in self.adjacency.get(node, []):
                    if child in self.nodes:
                        sub.nodes[child] = self.nodes[child]
                    queue.append((child, level + 1))

        bfs_up(node_fqn, depth)
        bfs_down(node_fqn, depth)

        for edge in self.edges:
            if edge.source_fqn in sub.nodes and edge.target_fqn in sub.nodes:
                sub.add_edge(edge)

        return sub

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": [node.to_dict() for node in self.nodes.values()],
            "edges": [edge.to_dict() for edge in self.edges],
            "stats": {
                "total_nodes": len(self.nodes),
                "total_edges": len(self.edges),
                "has_cycle": self.has_cycle(),
            },
        }


class LineageService:
    def __init__(self) -> None:
        self.parser = SQLLineageParser()
        self._cached_dag: Optional[LineageDAG] = None
        self._cache_time: Optional[datetime] = None
        logger.info("LineageService initialized")

    def _is_cache_valid(self) -> bool:
        if not self._cached_dag or not self._cache_time:
            return False
        cache_age = (datetime.utcnow() - self._cache_time).total_seconds()
        return cache_age < settings.LINEAGE_CACHE_TTL_SECONDS

    def _generate_mock_data(self) -> LineageDAG:
        logger.info("Generating mock lineage data for StarRocks acceleration network")
        dag = LineageDAG()

        mock_data = [
            {
                "mv_fqn": "starrocks.dws.dws_user_behavior_1d",
                "mv_name": "dws_user_behavior_1d",
                "db": "dws",
                "refresh_type": "ASYNC",
                "refresh_interval": 3600,
                "is_active": True,
                "last_refresh_time": datetime.utcnow() - timedelta(minutes=25),
                "definition": """
                    CREATE MATERIALIZED VIEW dws_user_behavior_1d
                    REFRESH ASYNC START(now()) EVERY(INTERVAL 1 HOUR)
                    AS SELECT user_id, dt, count(*) as pv, count(distinct session_id) as uv
                    FROM oss.ods.ods_user_behavior_log
                    GROUP BY user_id, dt
                """,
                "sources": [
                    {"fqn": "oss.ods.ods_user_behavior_log", "name": "ods_user_behavior_log", "storage_layer": "oss"},
                ],
            },
            {
                "mv_fqn": "starrocks.dws.dws_order_summary_1d",
                "mv_name": "dws_order_summary_1d",
                "db": "dws",
                "refresh_type": "ASYNC",
                "refresh_interval": 1800,
                "is_active": True,
                "last_refresh_time": datetime.utcnow() - timedelta(minutes=12),
                "definition": """
                    CREATE MATERIALIZED VIEW dws_order_summary_1d
                    REFRESH ASYNC EVERY(INTERVAL 30 MINUTE)
                    AS SELECT dt, region, sum(amount) as gmv, count(order_id) as order_cnt
                    FROM hive.dw.orders
                    JOIN hive.dw.dim_products ON orders.product_id = dim_products.id
                    GROUP BY dt, region
                """,
                "sources": [
                    {"fqn": "hive.dw.orders", "name": "orders", "storage_layer": "hive"},
                    {"fqn": "hive.dw.dim_products", "name": "dim_products", "storage_layer": "hive"},
                ],
            },
            {
                "mv_fqn": "starrocks.dws.dws_payment_flow_1h",
                "mv_name": "dws_payment_flow_1h",
                "db": "dws",
                "refresh_type": "ASYNC",
                "refresh_interval": 600,
                "is_active": True,
                "last_refresh_time": datetime.utcnow() - timedelta(minutes=8),
                "definition": """
                    CREATE MATERIALIZED VIEW dws_payment_flow_1h
                    REFRESH ASYNC EVERY(INTERVAL 10 MINUTE)
                    AS SELECT date_trunc('hour', dt) as hour, pay_type, sum(amount) as pay_amount
                    FROM oss.ods.payment_flow
                    GROUP BY date_trunc('hour', dt), pay_type
                """,
                "sources": [
                    {"fqn": "oss.ods.payment_flow", "name": "payment_flow", "storage_layer": "oss"},
                ],
            },
            {
                "mv_fqn": "starrocks.ads.ads_realtime_dashboard",
                "mv_name": "ads_realtime_dashboard",
                "db": "ads",
                "refresh_type": "ASYNC",
                "refresh_interval": 300,
                "is_active": True,
                "last_refresh_time": datetime.utcnow() - timedelta(minutes=3),
                "definition": """
                    CREATE MATERIALIZED VIEW ads_realtime_dashboard
                    REFRESH ASYNC EVERY(INTERVAL 5 MINUTE)
                    AS SELECT o.dt, o.region, o.gmv, o.order_cnt, u.pv, u.uv, p.pay_amount
                    FROM starrocks.dws.dws_order_summary_1d o
                    LEFT JOIN starrocks.dws.dws_user_behavior_1d u ON o.dt = u.dt
                    LEFT JOIN starrocks.dws.dws_payment_flow_1h p ON o.dt = substring(p.hour, 1, 10)
                """,
                "sources": [
                    {"fqn": "starrocks.dws.dws_order_summary_1d", "name": "dws_order_summary_1d", "storage_layer": "starrocks"},
                    {"fqn": "starrocks.dws.dws_user_behavior_1d", "name": "dws_user_behavior_1d", "storage_layer": "starrocks"},
                    {"fqn": "starrocks.dws.dws_payment_flow_1h", "name": "dws_payment_flow_1h", "storage_layer": "starrocks"},
                ],
            },
            {
                "mv_fqn": "starrocks.ads.ads_user_profile_agg",
                "mv_name": "ads_user_profile_agg",
                "db": "ads",
                "refresh_type": "MANUAL",
                "refresh_interval": 86400,
                "is_active": True,
                "last_refresh_time": datetime.utcnow() - timedelta(hours=5),
                "definition": """
                    CREATE MATERIALIZED VIEW ads_user_profile_agg
                    REFRESH MANUAL
                    AS SELECT user_id, count(distinct dt) as active_days, sum(pv) as total_pv
                    FROM starrocks.dws.dws_user_behavior_1d
                    GROUP BY user_id
                """,
                "sources": [
                    {"fqn": "starrocks.dws.dws_user_behavior_1d", "name": "dws_user_behavior_1d", "storage_layer": "starrocks"},
                ],
            },
        ]

        for item in mock_data:
            mv = StarRocksMaterializedView(
                db_name=item["db"],
                mv_name=item["mv_name"],
                fully_qualified_name=item["mv_fqn"],
                base_table_db=item["sources"][0]["fqn"].split('.')[1] if item["sources"] else "",
                base_table_name=item["sources"][0]["name"] if item["sources"] else "",
                base_table_fqn=item["sources"][0]["fqn"] if item["sources"] else "",
                definition_sql=item["definition"],
                refresh_type=item["refresh_type"],
                refresh_interval=item["refresh_interval"],
                is_active=item["is_active"],
                last_refresh_time=item["last_refresh_time"],
            )
            target_node, source_nodes, edges = self.parser.parse_mv_lineage(mv, item["sources"])
            dag.add_node(target_node)
            for src in source_nodes:
                dag.add_node(src)
            for edge in edges:
                dag.add_edge(edge)

        return dag

    def build_lineage_dag(self, force_refresh: bool = False) -> LineageDAG:
        if not force_refresh and self._is_cache_valid():
            logger.info("Using cached lineage DAG")
            return self._cached_dag

        try:
            dag = LineageDAG()

            with StarRocksConnector() as sr:
                databases = sr.list_databases()
                for db in databases:
                    try:
                        mvs = sr.list_materialized_views(db)
                        for mv in mvs:
                            try:
                                if not mv.definition_sql:
                                    mv.definition_sql = sr.get_mv_definition(db, mv.mv_name) or ""
                                target_node, source_nodes, edges = self.parser.parse_mv_lineage(mv)
                                dag.add_node(target_node)
                                for src in source_nodes:
                                    dag.add_node(src)
                                for edge in edges:
                                    dag.add_edge(edge)
                            except Exception as e:
                                logger.error("Error processing MV %s.%s: %s", db, mv.mv_name, str(e))
                    except Exception as e:
                        logger.error("Error processing database %s: %s", db, str(e))

            if len(dag.nodes) == 0:
                logger.warning("No lineage data from StarRocks, using mock data")
                dag = self._generate_mock_data()

        except Exception as e:
            logger.error("Error building lineage DAG from StarRocks: %s, using mock data", str(e))
            dag = self._generate_mock_data()

        self._cached_dag = dag
        self._cache_time = datetime.utcnow()
        logger.info(
            "Lineage DAG built: %d nodes, %d edges",
            len(dag.nodes), len(dag.edges)
        )
        return dag

    def calculate_refresh_delays(self, dag: LineageDAG) -> Dict[str, Dict[str, Any]]:
        delays = {}
        now = datetime.utcnow()
        for edge in dag.edges:
            target_node = dag.nodes.get(edge.target_fqn)
            if not target_node:
                continue
            props = target_node.properties
            last_refresh = props.get("last_refresh_time")
            refresh_interval = props.get("refresh_interval", 0)
            if last_refresh:
                try:
                    if isinstance(last_refresh, str):
                        last_refresh_dt = datetime.fromisoformat(last_refresh)
                    else:
                        last_refresh_dt = last_refresh
                    actual_delay = int((now - last_refresh_dt).total_seconds())
                except (ValueError, TypeError):
                    actual_delay = 0
            else:
                actual_delay = refresh_interval if refresh_interval else 0

            status = "normal"
            if refresh_interval and actual_delay > refresh_interval * 2:
                status = "delayed"
            elif refresh_interval and actual_delay > refresh_interval:
                status = "warning"

            edge_key = f"{edge.source_fqn}->{edge.target_fqn}"
            delays[edge_key] = {
                "source": edge.source_fqn,
                "target": edge.target_fqn,
                "refresh_delay_seconds": actual_delay,
                "refresh_interval": refresh_interval,
                "status": status,
                "last_refresh_time": last_refresh,
            }
        return delays

    def get_force_graph_data(self, force_refresh: bool = False) -> Dict[str, Any]:
        dag = self.build_lineage_dag(force_refresh=force_refresh)
        delays = self.calculate_refresh_delays(dag)

        nodes = []
        for fqn, node in dag.nodes.items():
            categories = {
                "oss": 0,
                "hive": 1,
                "starrocks": 2,
                "tablestore": 3,
            }
            cat = categories.get(node.storage_layer, 4)
            node_dict = node.to_dict()
            node_dict["category"] = cat
            node_dict["symbolSize"] = 80 if node.node_type == "materialized_view" else 50
            node_dict["label"] = node.name
            nodes.append(node_dict)

        edges = []
        for edge in dag.edges:
            edge_key = f"{edge.source_fqn}->{edge.target_fqn}"
            delay_info = delays.get(edge_key, {})
            edge_dict = edge.to_dict()
            edge_dict["lineStyle"] = self._get_edge_style(delay_info.get("status", "normal"))
            edge_dict["label"] = {
                "show": True,
                "formatter": self._format_delay_label(
                    delay_info.get("refresh_delay_seconds", 0),
                    delay_info.get("status", "normal")
                ),
                "fontSize": 10,
            }
            edges.append(edge_dict)

        categories = [
            {"name": "OSS"},
            {"name": "Hive"},
            {"name": "StarRocks"},
            {"name": "TableStore"},
            {"name": "Unknown"},
        ]

        stats = {
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "by_storage_layer": self._count_by_storage_layer(nodes),
            "delayed_edges": sum(1 for e in edges if e.get("label", {}).get("status") == "delayed"),
            "warning_edges": sum(1 for e in edges if e.get("label", {}).get("status") == "warning"),
            "normal_edges": sum(1 for e in edges if e.get("label", {}).get("status") == "normal"),
        }

        return {
            "nodes": nodes,
            "links": edges,
            "categories": categories,
            "stats": stats,
            "delays": delays,
            "topology": dag.to_dict()["stats"],
        }

    @staticmethod
    def _get_edge_style(status: str) -> Dict[str, Any]:
        styles = {
            "normal": {"color": "#00d4ff", "width": 2, "curveness": 0.2, "type": "solid"},
            "warning": {"color": "#ffb300", "width": 3, "curveness": 0.25, "type": "dashed"},
            "delayed": {"color": "#ff4757", "width": 4, "curveness": 0.3, "type": "bold"},
        }
        return styles.get(status, styles["normal"])

    @staticmethod
    def _format_delay_label(seconds: int, status: str) -> str:
        if seconds < 60:
            time_str = f"{seconds}s"
        elif seconds < 3600:
            time_str = f"{seconds // 60}m{seconds % 60}s"
        elif seconds < 86400:
            time_str = f"{seconds // 3600}h{(seconds % 3600) // 60}m"
        else:
            time_str = f"{seconds // 86400}d{(seconds % 86400) // 3600}h"

        status_icons = {"normal": "✓", "warning": "⚠", "delayed": "✗"}
        return f"{status_icons.get(status, '')} {time_str}"

    @staticmethod
    def _count_by_storage_layer(nodes: List[Dict[str, Any]]) -> Dict[str, int]:
        counts = {}
        for node in nodes:
            layer = node.get("storage_layer", "unknown")
            counts[layer] = counts.get(layer, 0) + 1
        return counts
