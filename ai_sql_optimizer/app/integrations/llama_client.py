import os
import re
from typing import Any, Dict, List
import requests
import json
from app.core.config import get_settings


class LlamaClient:
    def __init__(self):
        settings = get_settings()
        self.host = os.getenv("OLLAMA_HOST", settings.OLLAMA_HOST).rstrip("/")
        self.model = os.getenv("LLM_MODEL", settings.LLM_MODEL)
        self.timeout = int(os.getenv("LLM_TIMEOUT", "120"))

    def optimize_sql(self, sql: str, table_schema: List[Dict[str, Any]]) -> str:

        prompt = f"""
        You are an expert SQL performance optimizer for Google BigQuery.
        Your job is to ALWAYS improve the SQL using the provided TABLE SCHEMA for correctness.

        =====================
        TABLE SCHEMA (Parsed)
        =====================
        {table_schema}

        RULES:
        1. NEVER invent or guess columns. Only use the columns listed in the schema.
        2. Remove SELECT * and explicitly list only required columns.
        3. Push filters early when safe.
        4. Optimize JOIN order and filter placement.
        5. Prefer WHERE for filtering.
        6. Use QUALIFY ONLY when:
        - The query contains a window function (ROW_NUMBER, RANK, LAG, LEAD, OVER(), etc.)
        - NEVER introduce QUALIFY if no window function exists.
        - NEVER create artificial window functions just to add QUALIFY.
        7. Avoid unnecessary ORDER BY unless required.
        8. For BigQuery indexing:
        - Recommend *partitioning* for DATE/TIMESTAMP columns frequently filtered.
        - Recommend *clustering* for high-cardinality columns used in JOIN, WHERE, GROUP BY, ORDER BY.
        - DO NOT mention traditional B-Tree/Index structures.
        9. Output must ALWAYS use BigQuery-valid SQL.
        10. ALWAYS return the following two sections only:

        ### Optimized SQL:
        <rewritten-query>

        ### Explanation:
        - List every improvement made.
        - Provide BigQuery partitioning & clustering recommendations.

        =====================
        Original SQL:
        {sql}
        """


        # ------------ TRY NEW API FIRST ------------
        try:
            print(prompt)
            new_api_url = f"{self.host}/v1/chat/completions"
            print(new_api_url)
            print(self.model)
            print(self.timeout)
            response = requests.post(
                new_api_url,
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ]
                },
                timeout=self.timeout
            )

            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()

        except Exception:
            # Ignore and fallback to legacy API
            pass

        # ------------ FALLBACK: OLD OLLAMA API ------------
        legacy_url = f"{self.host}/api/generate"
        payload = {"model": self.model, "prompt": prompt, "stream": False}
        response = requests.post(legacy_url, json=payload, timeout=self.timeout)

        if response.status_code != 200:
            raise Exception(
                f"LLM error ({response.status_code}): {response.text}"
            )

        data = response.json()
        return data.get("response", "").strip()
    

    # --------------------------------------------------------
    # LLaMA Review
    # --------------------------------------------------------
    def llama_review(self, sql: str, text_stats: dict, dry_run_stats: dict, estimated_stats: dict, table_schema: List[Dict[str, Any]]):
        prompt_payload = {
        "sql": sql,
        "text_analysis": text_stats,
        "dry_run_stats": dry_run_stats,
        "estimated_stats": estimated_stats
    }

        prompt = f"""
        You are an expert BigQuery performance engineer.

        You will analyze a SQL query using:
        - Provided BigQuery DRY RUN statistics
        - Static SQL analysis
        - The exact TABLE SCHEMA supplied below

        =====================
        TABLE SCHEMA
        =====================
        {table_schema}

        STRICT RULES:
        1. Never guess or invent columns. Only use the schema above.
        2. All conclusions must be consistent with BigQuery behavior.
        3. Base recommendations only on:
        - Query structure
        - DRY RUN bytes processed
        - Joins, filters, window usage
        - Partition & clustering opportunities
        4. Do NOT rewrite the SQL. This is a review, not optimization.
        5. Output MUST be valid JSON. No markdown, no commentary.
        6. JSON fields required:
        - recommendations: list of strings
        - risk_flags: list of strings
        - sql_quality_score: integer 0–100
        - complexity: one of: "low", "medium", "high", "very_high"

        Your entire response MUST be ONLY JSON. No text before or after.

        =====================
        INPUT DATA
        =====================
        {json.dumps(prompt_payload, indent=2)}
        """

        try:
            print(prompt)
            url = f"{self.host}/v1/chat/completions"
            print(url)
            print(self.model)
            print(self.timeout)
            r = requests.post(
                url,
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}]
                },
                timeout=self.timeout
            )
            if r.status_code == 200:
                return r.json()["choices"][0]["message"]["content"]
        except:
            pass

        # fallback to legacy Ollama API
        legacy_url = f"{self.host}/api/generate"
        r = requests.post(
            legacy_url,
            json={"model": self.model, "prompt": prompt, "stream": False},
            timeout=self.timeout
        )
        return r.json().get("response", "")

    # --------------------------------------------------------
    # MASTER FUNCTION — Final combined report
    # --------------------------------------------------------
    def analyze_sql(self, sql: str,  static_stats: str, dryrun_stats: str, heuristic: str, table_schema: List[Dict[str, Any]]):
        llama_json = self.llama_review(sql, static_stats, dryrun_stats, heuristic, table_schema)

        return {
            "query_text_stats": static_stats,
            "scan_stats": dryrun_stats,
            "plan_stats": heuristic,
            "llm_review": llama_json
        }

