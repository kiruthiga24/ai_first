from app.integrations.llama_client import LlamaClient
from app.integrations.bigquery_client import BigQueryClient
from app.utils.sql_diff import generate_diff
import json
import re




class SQLOptimizerService:
    def __init__(self):
        self.llm = LlamaClient()
        self.bq = BigQueryClient()


    def optimize(self, sql: str, table_id: str):
        # 1. Get stats before: prefer table-based stats if table_id provided
        stats_before = None
        rewritten_sql = None
        try:
            table_schema = self.bq.get_bq_table_schema(table_id)
            print("schema", table_schema)
            static_stats = self.bq.static_sql_stats(sql)
            dryrun_stats = self.bq.bigquery_dry_run(sql)
            heuristic = self.bq.heuristic_stats(sql, static_stats, dryrun_stats)

            stats_before = self.llm.analyze_sql(sql, static_stats, dryrun_stats, heuristic, table_schema)
            print(json.dumps(stats_before, indent=4))
        except Exception as e:
            stats_before = {"stats before error": str(e)}

        # 2. Ask LLM to rewrite
        try:
            optimized_sql = self.llm.optimize_sql(sql, table_schema)
            match = re.search(r"```(.*?)```", optimized_sql, re.DOTALL)
            rewritten_sql = match.group(1).strip() if match else None
            print(rewritten_sql)
            
        except Exception as e:
            optimized_sql = sql  # fallback to original
            print("LLM error:", e)

        # 3. Stats after (estimate)
        try:
            static_stats_after = self.bq.static_sql_stats(rewritten_sql)
            dryrun_stats_after = self.bq.bigquery_dry_run(rewritten_sql)
            heuristic_after = self.bq.heuristic_stats(rewritten_sql, static_stats_after, dryrun_stats_after)

            stats_after = self.llm.analyze_sql(rewritten_sql, static_stats_after, dryrun_stats_after, heuristic_after, table_schema)
            print(json.dumps(stats_after, indent=4))
        except Exception as e:
            stats_after = {"error": str(e)}

        # 4. Diff
        diff = generate_diff(sql, rewritten_sql)

        response = {
            "original_sql": sql,
            "optimized_sql": optimized_sql,
            "rewritten_sql": rewritten_sql,
            "diff": diff,
            "stats_before": stats_before,
            "stats_after": stats_after,
        }
        print(json.dumps(response, indent=4))
        return response
