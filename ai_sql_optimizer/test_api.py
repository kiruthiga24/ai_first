import requests

API_URL = "http://127.0.0.1:8000/api/v1/optimize"

payload = {
    "sql": """
        SELECT *
        FROM `test.employees`
        WHERE salary > 50000
        ORDER BY salary DESC
    """,
    "table": "employees"
}

try:
    response = requests.post(API_URL, json=payload)
    print("Status Code:", response.status_code)

    if response.status_code == 200:
        print("\n--- Optimized SQL ---")
        print(response.json().get("optimized_sql"))

        print("\n--- Explanation ---")
        print(response.json().get("explanation"))
    else:
        print("\nError Response:")
        print(response.text)

except Exception as e:
    print("Error occurred:", e)
