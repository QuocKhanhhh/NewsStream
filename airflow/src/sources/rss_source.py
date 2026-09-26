from typing import Optional
from src.clients.https_client import HTTPSClient
from src.clients.https_client import HTTPClientError
from src.sources.base_source import BaseSource
from dataclasses import dataclass

class RSSSource(BaseSource):
    def __init__(
        self,
        url: str,
        http_client: HTTPSClient,
        source_name: Optional[str] = None,
        proxy: dict | None = None,
        proxy_pool=None,
        max_proxy_attempts: int = 3,
    ):
        self.url = url
        self.http_client = http_client
        self.source_name = source_name or url
        self.proxy = proxy
        self.proxy_pool = proxy_pool
        self.max_proxy_attempts = max_proxy_attempts
        
    def fetch(self) -> bytes:
        if self.proxy_pool is None:
            return self.http_client.get(self.url, proxies=self.proxy)

        last_error = None
        for _ in range(self.max_proxy_attempts):
            proxy = self.proxy_pool.acquire()
            if proxy is None:
                break
            try:
                content = self.http_client.get(self.url, proxies=proxy)
                self.proxy_pool.release(proxy)
                return content
            except HTTPClientError as error:
                last_error = error
                if error.proxy_error:
                    self.proxy_pool.remove(proxy)
                else:
                    self.proxy_pool.release(proxy)
                    raise
            except Exception as error:
                last_error = error
                self.proxy_pool.remove(proxy)

        if last_error is not None:
            raise last_error
        raise RuntimeError(f"No proxy available for RSS source: {self.source_name}")
    
    
@dataclass(frozen=True)
class RSSFeeds:
    name: str
    url: str
    language: str
