from langchain_core.tools import tool
import requests

@tool
def run_test_api(
        url:str,
        method:str,
        expected_status:int,
        body: dict | None=None,
        headers: dict | None=None
):
    """Execute the API test and compare the actual HTTP status with the expected status """

    try:
        response = requests.request(
            url=url,
            method=method,
            json=body,
            headers=headers,
            timeout=10
        )

        passed = response.status_code == expected_status

        return {
            "passed" : passed,
            "url" : url,
            "method" : method,
            "expected_status" : expected_status,
            "actual_status" : response.status_code,
            "response_timeout_ms" : round(response.elapsed.total_seconds() * 1000,2)
        }
    except requests.RequestException as e:
        return {
            "passed": False,
            "method" : method,
            "url" : url,
            "error" : str(e) 
        }