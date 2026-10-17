import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def check_url(url: str, timeout: float = 10.0) -> dict:
    request = Request( url, headers={"User-Agent": "WebCheckReport/0.1"}, method="GET")

    start_time = time.perf_counter()

    try:
        with urlopen(request, timeout=timeout) as response:
            elapsed = time.perf_counter() - start_time

            return {
                "url": url,
                "status_code": response.status,
                "headers": dict(response.headers.items()),
                "elapsed_seconds": round(elapsed, 4),
                "error": None,
            }

    except HTTPError as error:
        elapsed = time.perf_counter() - start_time

        return {
            "url": url,
            "status_code": error.code,
            "headers": dict(error.headers.items()) if error.headers else {},
            "elapsed_seconds": round(elapsed, 4),
            "error": None,
        }

    except (URLError, TimeoutError, OSError) as error:
        elapsed = time.perf_counter() - start_time

        return {
            "url": url,
            "status_code": None,
            "headers": {},
            "elapsed_seconds": round(elapsed, 4),
            "error": str(error),
        }