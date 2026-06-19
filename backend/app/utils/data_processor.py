import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, unquote


logger = logging.getLogger(__name__)


def normalize_storage_path(path: Optional[str]) -> str:
    if not path:
        return ""
    path = unquote(path.strip())
    parsed = urlparse(path)
    if parsed.scheme and parsed.netloc:
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path.rstrip('/')}"
    else:
        normalized = re.sub(r"/+", "/", path).rstrip("/")
    logger.debug("Normalized path '%s' -> '%s'", path, normalized)
    return normalized


def calculate_size_stats(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not records:
        return {
            "total_size_bytes": 0,
            "total_records": 0,
            "total_files": 0,
            "avg_record_size_bytes": 0,
            "min_size_bytes": 0,
            "max_size_bytes": 0,
        }
    sizes = []
    total_records = 0
    total_files = 0
    for rec in records:
        size = rec.get("size_bytes") or rec.get("total_size_bytes") or 0
        sizes.append(size)
        total_records += rec.get("record_count", 0) or 0
        total_files += rec.get("file_count", 0) or 0
    total_size = sum(sizes)
    avg_size = total_size // len(sizes) if sizes else 0
    result = {
        "total_size_bytes": total_size,
        "total_records": total_records,
        "total_files": total_files,
        "avg_record_size_bytes": avg_size,
        "min_size_bytes": min(sizes) if sizes else 0,
        "max_size_bytes": max(sizes) if sizes else 0,
    }
    logger.debug("Calculated size stats: %s", result)
    return result


def merge_metadata(
    hive_data: Optional[List[Dict[str, Any]]] = None,
    oss_data: Optional[List[Dict[str, Any]]] = None,
    ots_data: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    merged: Dict[str, Dict[str, Any]] = {}
    hive_data = hive_data or []
    oss_data = oss_data or []
    ots_data = ots_data or []

    for item in hive_data:
        key = _build_merge_key(item)
        if key not in merged:
            merged[key] = {}
        merged[key].update({
            "source_type": "hive",
            "hive_metadata": item,
            "name": item.get("name") or item.get("table_name") or "",
            "schema_name": item.get("schema_name") or item.get("db_name"),
            "table_name": item.get("table_name"),
            "storage_path": normalize_storage_path(item.get("location") or item.get("storage_path")),
            "columns": item.get("columns", []),
            "partition_keys": item.get("partition_keys", []),
            "partitions": item.get("partitions", []),
        })
        _copy_stats(item, merged[key])
        logger.debug("Merged hive data for key: %s", key)

    for item in oss_data:
        key = _build_merge_key(item)
        if key not in merged:
            merged[key] = {
                "source_type": "oss",
                "name": item.get("name") or item.get("prefix") or "",
                "storage_path": normalize_storage_path(item.get("prefix") or item.get("storage_path")),
            }
        else:
            merged[key]["source_type"] = _combine_source_types(merged[key].get("source_type", ""), "oss")
        merged[key]["oss_metadata"] = item
        _copy_stats(item, merged[key])
        logger.debug("Merged oss data for key: %s", key)

    for item in ots_data:
        key = _build_merge_key(item)
        if key not in merged:
            merged[key] = {
                "source_type": "tablestore",
                "name": item.get("name") or item.get("table_name") or "",
                "table_name": item.get("table_name"),
                "columns": item.get("columns", []),
            }
        else:
            merged[key]["source_type"] = _combine_source_types(merged[key].get("source_type", ""), "tablestore")
        merged[key]["ots_metadata"] = item
        _copy_stats(item, merged[key])
        logger.debug("Merged ots data for key: %s", key)

    result = list(merged.values())
    logger.info("Merged metadata: %d records from hive(%d) + oss(%d) + ots(%d)",
                len(result), len(hive_data), len(oss_data), len(ots_data))
    return result


def bytes_to_human(size_bytes: Optional[int]) -> str:
    if size_bytes is None:
        return "0 B"
    if size_bytes < 0:
        size_bytes = 0
    units = ["B", "KB", "MB", "GB", "TB", "PB"]
    size = float(size_bytes)
    unit_index = 0
    while size >= 1024.0 and unit_index < len(units) - 1:
        size /= 1024.0
        unit_index += 1
    result = f"{size:.2f} {units[unit_index]}"
    logger.debug("Converted %d bytes to %s", size_bytes, result)
    return result


def _build_merge_key(item: Dict[str, Any]) -> str:
    path = normalize_storage_path(
        item.get("storage_path")
        or item.get("location")
        or item.get("prefix")
        or ""
    )
    if path:
        return f"path:{path}"
    schema = item.get("schema_name") or item.get("db_name") or ""
    table = item.get("table_name") or item.get("name") or ""
    if schema and table:
        return f"table:{schema}.{table}"
    if table:
        return f"table:{table}"
    name = item.get("name", "")
    return f"name:{name}"


def _copy_stats(source: Dict[str, Any], target: Dict[str, Any]) -> None:
    for key in ["record_count", "total_size_bytes", "file_count"]:
        val = source.get(key)
        if val is not None:
            target[key] = val


def _combine_source_types(existing: str, new_type: str) -> str:
    if not existing:
        return new_type
    if new_type in existing:
        return existing
    return f"{existing}+{new_type}"
