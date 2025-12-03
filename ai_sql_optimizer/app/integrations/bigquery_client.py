import os, re
from google.cloud import bigquery
from app.core.config import get_settings
import json

class BigQueryClient:
    def __init__(self):
        settings = get_settings()
        project = settings.GCP_PROJECT
        if project:
            print(project)
            self.client = bigquery.Client(project=project)
        else:
            self.client = None

    def get_bq_table_schema(self, table_id: str):
        try:
            table_ref = f"{get_settings().GCP_PROJECT}.{get_settings().GCP_DATASET}.{table_id}"
            print("table", table_ref)
            table = self.client.get_table(table_ref)

            schema_info = []

            for field in table.schema:
                schema_info.append({
                    "name": field.name,
                    "type": field.field_type,
                    "mode": field.mode,     # NULLABLE, REQUIRED, REPEATED
                    "description": field.description
                })

            return schema_info
        except Exception as e:
            return e
    
     # --------------------------------------------------------
    # STEP 1 — Static SQL Parsing (select*, joins, predicates)
    # --------------------------------------------------------

    def static_sql_stats(self, sql: str):
        return {
            "select_star": bool(re.search(r"select\s+\*", sql, re.IGNORECASE)),
            "num_joins": len(re.findall(r"\bjoin\b", sql, re.IGNORECASE)),
            "window_functions": re.findall(
                r"(row_number|rank|dense_rank|lag|lead)\s*\(",
                sql,
                re.IGNORECASE
            ),
            "non_sargable_predicates": re.findall(
                r"(DATE\([^)]*\)|CAST\([^)]* AS DATE\))",
                sql,
                re.IGNORECASE
            ),
            "partition_filters_used": bool(
                re.search(r"(WHERE|AND)\s+.*event_date", sql, re.IGNORECASE)
            )
        }

    # --------------------------------------------------------
    # STEP 2 — BigQuery Dry Run
    # --------------------------------------------------------
    def bigquery_dry_run(self, sql: str):
        job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
        job = self.client.query(sql, job_config=job_config)

        return {
            "bytes_scanned": job.total_bytes_processed,
            "bytes_billed": job.total_bytes_billed,
            "slot_ms": job.slot_millis,
            "tables_accessed": len(job.referenced_tables or []),
            "rows_scanned": job.total_rows if hasattr(job, "total_rows") else None
        }

    # --------------------------------------------------------
    # STEP 3 — Estimated Stats / Heuristics
    # --------------------------------------------------------
    def heuristic_stats(self, sql: str, static_stats, dryrun_stats):
        est_shuffle = (
            dryrun_stats["bytes_scanned"] * 0.12   # assume 12% shuffle risk
            if static_stats["num_joins"] > 1
            else dryrun_stats["bytes_scanned"] * 0.02
        )

        return {
            "join_type": "shuffle" if static_stats["num_joins"] > 1 else "broadcast",
            "shuffle_bytes": int(est_shuffle),
            "partition_pruning": static_stats["partition_filters_used"],
            "cluster_pruning": static_stats["partition_filters_used"],
            "join_build_size": "large" if est_shuffle > 1e9 else "small"
        }


