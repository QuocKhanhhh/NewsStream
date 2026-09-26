import time
from email.utils import parsedate_to_datetime
from typing import Optional, Dict
import requests


class HTTPClientError(RuntimeError):
    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        retry_after: float | None = None,
        proxy_error: bool = False,
    ):
        self.status_code = status_code
        self.retry_after = retry_after
        self.proxy_error = proxy_error
        super().__init__(message)

class HTTPSClient:
    def __init__(
        self,
        timeout: int = 30,
        user_agent: Optional[str] = None,
        max_retries: int = 0,
        backoff_factor: float = 1.0,
    ):
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent or "NewsScraper/1.0"})

    def get(self, url: str, proxies: Optional[Dict[str, str]] = None) -> bytes:
        for attempt in range(self.max_retries + 1):
            try:
                response = self.session.get(url, proxies=proxies, timeout=self.timeout)
                if response.status_code == 429 or response.status_code >= 500:
                    retry_after = self._retry_after(response)
                    if attempt < self.max_retries:
                        time.sleep(
                            retry_after
                            if retry_after is not None
                            else self.backoff_factor * (2 ** attempt)
                        )
                        continue
                    raise HTTPClientError(
                        f"HTTP request failed with status {response.status_code}",
                        status_code=response.status_code,
                        retry_after=retry_after,
                        proxy_error=response.status_code in {403, 407},
                    )
                # Convert every non-success HTTP response to the same typed
                # error.  This lets callers distinguish permanent 4xx errors
                # from retryable 429/5xx responses without depending on
                # requests.exceptions.HTTPError.
                if not 200 <= response.status_code < 300:
                    raise HTTPClientError(
                        f"HTTP request failed with status {response.status_code}",
                        status_code=response.status_code,
                        retry_after=self._retry_after(response),
                        proxy_error=response.status_code in {403, 407},
                    )
                response.raise_for_status()
                return response.content
            except (requests.Timeout, requests.ConnectionError) as error:
                if attempt < self.max_retries:
                    time.sleep(self.backoff_factor * (2 ** attempt))
                    continue
                raise HTTPClientError(
                    "HTTP request failed after retries",
                    proxy_error=True,
                ) from error
        raise HTTPClientError("HTTP request failed")

    @staticmethod
    def _retry_after(response: requests.Response) -> float | None:
        value = response.headers.get("Retry-After")
        if not value:
            return None
        try:
            return max(0.0, float(value))
        except ValueError:
            try:
                date = parsedate_to_datetime(value)
                return max(0.0, date.timestamp() - time.time())
            except (TypeError, ValueError, OverflowError):
                return None

    def close(self):
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
            
    
