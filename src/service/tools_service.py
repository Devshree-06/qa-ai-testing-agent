from langchain_core.tools import tool
import requests

@tool
def get_api_status(url:str) -> str:
    """ Check whether the API endpoint is available. """

    try :
        response = requests.get(url,timeout=5)

        return (
            f"API responded successfully. "
            f"Status code : {response.status_code}"
        )
    except requests.RequestException as e:
        return f"API request failed: {str(e)}"

@tool
def test_api(
        method:str,
        url:str,
        body : dict | None = None ) :

    """Send HTTPS request to an API endpoint and return its status and response"""

    try:
        response = requests.request(
            method=method,
            url=url,
            json=body,
            timeout=5
        )

        return {
            "url" : url,
            "status_code" : response.status_code,
            "status" : "UP" if response.ok else "DOWN",
            "response_time_ms" : round(response.elapsed.total_seconds() * 1000,2)
        }
    
    except requests.RequestException as e:

        return {
            "url"  : url,
            "status" : "DOWN",
            "error" : str(e)
        }