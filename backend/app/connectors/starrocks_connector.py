import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.config import settings


logger = logging.getLogger(__name__)


@dataclass
class StarRocksTable:
    db_name: str
    table_name: str
    fully_qualified_name: str
    table_type: str
    engine: str
    model: str
    sort_keys: List[str] = field(default_factory=list)
    distributed_by: List[str] = field(default_factory=list)
    properties: Dict[str, str] = field(default_factory=dict)
    comment: str = ""
    create_time: Optional[datetime] = None
    update_time: Optional[datetime] = None


@dataclass
class StarRocksMaterializedView:
    db_name: str
    mv_name: str
    fully_qualified_name: str
    base_table_db: str
    base_table_name: str
    base_table_fqn: str
    definition_sql: str
    refresh_type: str
    refresh_interval: int
    is_active: bool
    last_refresh_time: Optional[datetime] = None
    next_refresh_time: Optional[datetime] = None
    partition_info: Dict[str, Any] = field(default_factory=dict)
    comment: str = ""


@dataclass
class StarRocksAuditLog:
    query_id: str
    timestamp: datetime
    user: str
    db: str
    query_type: str
    sql_text: str
    scan_rows: int = 0
    scan_bytes: int = 0
    return_rows: int = 0
    query_time_ms: int = 0
    status: str = ""


class StarRocksConnector:
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
    ) -> None:
        self.host = host or settings.STARROCKS_FE_HOST
        self.port = port or settings.STARROCKS_QUERY_PORT
        self.user = user or settings.STARROCKS_USER
        self.password = password or settings.STARROCKS_PASSWORD
        self.database = database or settings.STARROCKS_DATABASE
        self._connection = None
        self._connected = False
        logger.info(
            "StarRocksConnector initialized for %s:%d (db=%s)",
            self.host, self.port, self.database
        )

    def _connect(self) -> None:
        if self._connected:
            return
        try:
            import mysql.connector

            self._connection = mysql.connector.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database,
                connection_timeout=30,
            )
            self._connected = True
            logger.info("Connected to StarRocks FE at %s:%d", self.host, self.port)
        except ImportError:
            logger.warning(
                "StarRocks MySQL client not available. Install mysql-connector-python."
            )
            self._connected = False
        except Exception as e:
            logger.error("Failed to connect to StarRocks: %s", str(e))
            self._connected = False

    def _close(self) -> None:
        if self._connection and self._connected:
            try:
                self._connection.close()
            except Exception as e:
                logger.warning("Error closing StarRocks connection: %s", str(e))
            finally:
                self._connected = False
                self._connection = None

    def __enter__(self) -> "StarRocksConnector":
        self._connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._close()

    def _execute_query(self, sql: str) -> List[Dict[str, Any]]:
        if not self._connected:
            self._connect()
        if not self._connection:
            logger.warning("StarRocks not connected, returning empty result for: %s", sql[:50])
            return []
        try:
            cursor = self._connection.cursor(dictionary=True)
            cursor.execute(sql)
            results = cursor.fetchall()
            cursor.close()
            return [dict(row) for row in results]
        except Exception as e:
            logger.error("StarRocks query failed: %s", str(e))
            return []

    def list_databases(self) -> List[str]:
        logger.info("Listing StarRocks databases")
        rows = self._execute_query("SHOW DATABASES")
        return [row.get("Database", "") for row in rows]

    def list_tables(self, db_name: str) -> List[str]:
        logger.info("Listing tables in database: %s", db_name)
        rows = self._execute_query(f"SHOW TABLES FROM `{db_name}`")
        key = f"Tables_in_{db_name}"
        return [row.get(key, "") for row in rows if row.get(key)]

    def list_materialized_views(self, db_name: str, table_name: Optional[str] = None) -> List[StarRocksMaterializedView]:
        logger.info("Listing materialized views in %s (table=%s)", db_name, table_name)
        sql = f"SHOW MATERIALIZED VIEWS FROM `{db_name}`"
        if table_name:
            sql += f" WHERE TableName = '{table_name}'"
        rows = self._execute_query(sql)
        result = []
        for row in rows:
            try:
                mv = StarRocksMaterializedView(
                    db_name=db_name,
                    mv_name=row.get("MaterializedViewName", ""),
                    fully_qualified_name=f"starrocks.{db_name}.{row.get('MaterializedViewName', '')}",
                    base_table_db=row.get("DBName", db_name),
                    base_table_name=row.get("TableName", ""),
                    base_table_fqn=f"starrocks.{row.get('DBName', db_name)}.{row.get('TableName', '')}",
                    definition_sql=row.get("Definition", ""),
                    refresh_type=row.get("RefreshType", ""),
                    refresh_interval=int(row.get("RefreshInterval", 0) or 0),
                    is_active=row.get("State", "ACTIVE") == "ACTIVE",
                    last_refresh_time=row.get("LastRefreshTime"),
                    next_refresh_time=row.get("NextRefreshTime"),
                    comment=row.get("Comment", ""),
                )
                result.append(mv)
            except Exception as e:
                logger.error("Error parsing MV row: %s", str(e))
        logger.info("Found %d materialized views in %s", len(result), db_name)
        return result

    def get_mv_definition(self, db_name: str, mv_name: str) -> Optional[str]:
        logger.info("Getting MV definition: %s.%s", db_name, mv_name)
        rows = self._execute_query(f"SHOW CREATE MATERIALIZED VIEW `{db_name}`.`{mv_name}`")
        if rows:
            return rows[0].get("Materialized View Create Statement", "")
        return None

    def get_audit_logs(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000,
    ) -> List[StarRocksAuditLog]:
        if start_time is None:
            start_time = datetime.utcnow() - timedelta(days=7)
        if end_time is None:
            end_time = datetime.utcnow()

        logger.info(
            "Fetching StarRocks audit logs: %s ~ %s (limit=%d)",
            start_time, end_time, limit
        )

        sql = f"""
            SELECT 
                QUERY_ID as query_id,
                TIMESTAMP as timestamp,
                USER as user,
                DB as db,
                QUERY_TYPE as query_type,
                SQL_TEXT as sql_text,
                SCAN_ROWS as scan_rows,
                SCAN_BYTES as scan_bytes,
                RETURN_ROWS as return_rows,
                QUERY_TIME as query_time_ms,
                STATE as status
            FROM INFORMATION_SCHEMA.statement_audit
            WHERE TIMESTAMP >= '{start_time.strftime('%Y-%m-%d %H:%M:%S')}'
              AND TIMESTAMP <= '{end_time.strftime('%Y-%m-%d %H:%M:%S')}'
            ORDER BY TIMESTAMP DESC
            LIMIT {limit}
        """
        rows = self._execute_query(sql)
        result = []
        for row in rows:
            try:
                audit = StarRocksAuditLog(
                    query_id=row.get("query_id", ""),
                    timestamp=row.get("timestamp"),
                    user=row.get("user", ""),
                    db=row.get("db", ""),
                    query_type=row.get("query_type", ""),
                    sql_text=row.get("sql_text", ""),
                    scan_rows=int(row.get("scan_rows", 0) or 0),
                    scan_bytes=int(row.get("scan_bytes", 0) or 0),
                    return_rows=int(row.get("return_rows", 0) or 0),
                    query_time_ms=int(row.get("query_time_ms", 0) or 0),
                    status=row.get("status", ""),
                )
                result.append(audit)
            except Exception as e:
                logger.error("Error parsing audit log row: %s", str(e))
        logger.info("Fetched %d audit log entries", len(result))
        return result

    def get_table_ddl(self, db_name: str, table_name: str) -> Optional[str]:
        logger.info("Getting DDL for table: %s.%s", db_name, table_name)
        rows = self._execute_query(f"SHOW CREATE TABLE `{db_name}`.`{table_name}`")
        if rows:
            return rows[0].get("Create Table", "")
        return None

    def get_mv_refresh_status(self, db_name: str, mv_name: str) -> Dict[str, Any]:
        logger.info("Getting MV refresh status: %s.%s", db_name, mv_name)
        rows = self._execute_query(
            f"SELECT * FROM INFORMATION_SCHEMA.materialized_views_refresh_jobs "
            f"WHERE TABLE_SCHEMA = '{db_name}' AND MATERIALIZED_VIEW_NAME = '{mv_name}'"
        )
        if rows:
            return dict(rows[0])
        return {}
