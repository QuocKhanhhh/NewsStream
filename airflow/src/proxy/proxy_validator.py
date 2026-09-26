import time
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProxyValidationResult:
    proxy: dict[str, str]
    health: float
    is_valid: bool


class ProxyValidator:
    def __init__(
        self,
        http_client: Any,
        test_url: str,
        checks: int = 3,
        sleep_interval: float = 0.1,
        valid_threshold: float = 0.66,
    ):
        self.http_client = http_client
        self.test_url = test_url
        self.checks = checks
        self.sleep_interval = sleep_interval
        self.valid_threshold = valid_threshold

    def validate(
        self,
        proxy: dict[str, str],
    ) -> ProxyValidationResult:
        success_count = 0

        for _ in range(self.checks):
            try:
                self.http_client.get(
                    self.test_url,
                    proxies=proxy,
                )
                success_count += 1
            except Exception:
                pass

            time.sleep(self.sleep_interval)

        health = success_count / self.checks

        return ProxyValidationResult(
            proxy=proxy,
            health=health,
            is_valid=health >= self.valid_threshold,
        )

    def validate_many(
        self,
        proxies: list[dict[str, str]],
    ) -> list[ProxyValidationResult]:
        results = []

        for proxy in proxies:
            results.append(self.validate(proxy))

        return results