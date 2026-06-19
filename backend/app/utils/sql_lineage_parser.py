import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from app.connectors.starrocks_connector import StarRocksMaterializedView


logger = logging.getLogger(__name__)


@dataclass
class LineageEdge:
    source_fqn: str
    target_fqn: str
    edge_type: str = "dependency"
    transformation: str = ""
    refresh_delay_seconds: int = 0
    last_refresh_time: Optional[Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source_fqn,
            "target": self.target_fqn,
            "type": self.edge_type,
            "transformation": self.transformation,
            "refresh_delay_seconds": self.refresh_delay_seconds,
            "last_refresh_time": (
                self.last_refresh_time.isoformat()
                if self.last_refresh_time and hasattr(self.last_refresh_time, "isoformat")
                else None
            ),
        }


@dataclass
class LineageNode:
    fqn: str
    name: str
    node_type: str
    storage_layer: str
    database_name: str = ""
    table_name: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.fqn,
            "name": self.name,
            "type": self.node_type,
            "storage_layer": self.storage_layer,
            "database_name": self.database_name,
            "table_name": self.table_name,
            "properties": self.properties,
        }


class SQLLineageParser:
    def __init__(self) -> None:
        self._hive_table_pattern = re.compile(
            r'(?:FROM|JOIN|INTO|TABLE)\s+([`"\[]?[\w]+\.?[`"\]]?[\w]+[`"\]]?)',
            re.IGNORECASE
        )
        self._external_catalog_pattern = re.compile(
            r'(?:FROM|JOIN)\s+([`"\[]?(?:oss|hive|hudi|iceberg)[_\w]*\.`?[\w]+\`?\.`?[\w]+\`?)',
            re.IGNORECASE
        )
        self._qualified_table_pattern = re.compile(
            r'([`"]?[\w]+`?\s*\.\s*`?[\w]+`?(?:\s*\.\s*`?[\w]+`?)?)',
            re.IGNORECASE
        )
        self._cte_pattern = re.compile(
            r'WITH\s+([\w]+)\s+AS\s*\(',
            re.IGNORECASE
        )
        logger.info("SQLLineageParser initialized")

    def _clean_sql(self, sql: str) -> str:
        sql = re.sub(r'--.*?$', '', sql, flags=re.MULTILINE)
        sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
        sql = sql.replace('\n', ' ').replace('\t', ' ')
        sql = re.sub(r'\s+', ' ', sql).strip()
        return sql

    def _extract_ctes(self, sql: str) -> Set[str]:
        ctes = set()
        for match in self._cte_pattern.finditer(sql):
            ctes.add(match.group(1).lower())
        return ctes

    def _normalize_table_name(self, table_ref: str) -> str:
        table_ref = table_ref.strip().strip('`').strip('"').strip('[')
        table_ref = re.sub(r'\s+', '', table_ref)
        return table_ref.lower()

    def _classify_source(self, table_ref: str) -> Tuple[str, str, str]:
        normalized = self._normalize_table_name(table_ref)
        parts = normalized.split('.')

        if len(parts) == 3:
            catalog, db, tbl = parts
            if 'oss' in catalog:
                return (f"oss.{db}.{tbl}", "oss", tbl)
            elif 'hive' in catalog:
                return (f"hive.{db}.{tbl}", "hive", tbl)
            elif 'starrocks' in catalog or 'sr' in catalog:
                return (f"starrocks.{db}.{tbl}", "starrocks", tbl)
            else:
                return (f"starrocks.{db}.{tbl}", "starrocks", tbl)
        elif len(parts) == 2:
            db, tbl = parts
            return (f"starrocks.{db}.{tbl}", "starrocks", tbl)
        elif len(parts) == 1:
            return (f"starrocks.default.{parts[0]}", "starrocks", parts[0])
        else:
            return (normalized, "unknown", parts[-1] if parts else normalized)

    def extract_source_tables(self, sql: str) -> List[Dict[str, str]]:
        cleaned_sql = self._clean_sql(sql)
        ctes = self._extract_ctes(cleaned_sql)

        sources = []
        seen = set()

        for match in self._external_catalog_pattern.finditer(cleaned_sql):
            table_ref = match.group(1)
            fqn, storage_layer, name = self._classify_source(table_ref)
            if fqn not in seen and name.lower() not in ctes:
                seen.add(fqn)
                sources.append({
                    "fqn": fqn,
                    "name": name,
                    "storage_layer": storage_layer,
                    "raw_ref": table_ref,
                })

        if not sources:
            for match in self._hive_table_pattern.finditer(cleaned_sql):
                table_ref = match.group(1)
                if any(kw in table_ref.lower() for kw in ['select', 'where', 'and', 'from', 'join']):
                    continue
                fqn, storage_layer, name = self._classify_source(table_ref)
                if fqn not in seen and name.lower() not in ctes:
                    seen.add(fqn)
                    sources.append({
                        "fqn": fqn,
                        "name": name,
                        "storage_layer": storage_layer,
                        "raw_ref": table_ref,
                    })

        logger.info("Extracted %d source tables from SQL", len(sources))
        return sources

    def parse_mv_lineage(
        self,
        mv: StarRocksMaterializedView,
        additional_sources: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[LineageNode, List[LineageNode], List[LineageEdge]]:
        target_node = LineageNode(
            fqn=mv.fully_qualified_name,
            name=mv.mv_name,
            node_type="materialized_view",
            storage_layer="starrocks",
            database_name=mv.db_name,
            table_name=mv.mv_name,
            properties={
                "refresh_type": mv.refresh_type,
                "refresh_interval": mv.refresh_interval,
                "is_active": mv.is_active,
                "last_refresh_time": (
                    mv.last_refresh_time.isoformat()
                    if mv.last_refresh_time
                    else None
                ),
                "comment": mv.comment,
            },
        )

        source_nodes: List[LineageNode] = []
        edges: List[LineageEdge] = []

        base_fqn = mv.base_table_fqn
        if base_fqn:
            parts = base_fqn.split('.')
            base_name = parts[-1]
            base_storage_layer = parts[0] if parts and parts[0] in ("oss", "hive", "tablestore", "starrocks") else "starrocks"
            base_db = parts[1] if len(parts) >= 3 else mv.base_table_db
            source_node = LineageNode(
                fqn=base_fqn,
                name=base_name,
                node_type="table",
                storage_layer=base_storage_layer,
                database_name=base_db,
                table_name=mv.base_table_name,
                properties={},
            )
            source_nodes.append(source_node)

            from datetime import datetime
            delay = 0
            if mv.last_refresh_time:
                delay = int((datetime.utcnow() - mv.last_refresh_time).total_seconds())
            elif mv.refresh_interval:
                delay = mv.refresh_interval

            edge = LineageEdge(
                source_fqn=base_fqn,
                target_fqn=mv.fully_qualified_name,
                edge_type="mv_dependency",
                transformation=mv.definition_sql[:200] if mv.definition_sql else "",
                refresh_delay_seconds=delay,
                last_refresh_time=mv.last_refresh_time,
            )
            edges.append(edge)

        if mv.definition_sql:
            external_sources = self.extract_source_tables(mv.definition_sql)
            for src in external_sources:
                src_fqn = src["fqn"]
                existing = next((n for n in source_nodes if n.fqn == src_fqn), None)
                if not existing:
                    ext_node = LineageNode(
                        fqn=src_fqn,
                        name=src["name"],
                        node_type="external_table",
                        storage_layer=src["storage_layer"],
                        database_name=src_fqn.split('.')[1] if len(src_fqn.split('.')) > 1 else "",
                        table_name=src["name"],
                        properties={"raw_reference": src["raw_ref"]},
                    )
                    source_nodes.append(ext_node)

                    edge_exists = any(
                        e.source_fqn == src_fqn and e.target_fqn == mv.fully_qualified_name
                        for e in edges
                    )
                    if not edge_exists:
                        from datetime import datetime
                        delay = 0
                        if mv.last_refresh_time:
                            delay = int((datetime.utcnow() - mv.last_refresh_time).total_seconds())
                        edge = LineageEdge(
                            source_fqn=src_fqn,
                            target_fqn=mv.fully_qualified_name,
                            edge_type="external_dependency",
                            transformation=f"Source: {src['raw_ref']}",
                            refresh_delay_seconds=delay,
                            last_refresh_time=mv.last_refresh_time,
                        )
                        edges.append(edge)

        if additional_sources:
            for src in additional_sources:
                src_fqn = src.get("fqn", "")
                if src_fqn and not any(n.fqn == src_fqn for n in source_nodes):
                    node = LineageNode(
                        fqn=src_fqn,
                        name=src.get("name", src_fqn.split('.')[-1]),
                        node_type="table",
                        storage_layer=src.get("storage_layer", "unknown"),
                        properties=src.get("properties", {}),
                    )
                    source_nodes.append(node)

                    from datetime import datetime
                    edge = LineageEdge(
                        source_fqn=src_fqn,
                        target_fqn=mv.fully_qualified_name,
                        edge_type="additional_dependency",
                        refresh_delay_seconds=0,
                        last_refresh_time=mv.last_refresh_time,
                    )
                    edges.append(edge)

        return target_node, source_nodes, edges
