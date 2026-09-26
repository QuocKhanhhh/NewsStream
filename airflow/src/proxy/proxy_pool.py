from typing import Any


class ProxyPool:
    def __init__(
        self,
        redis_client: Any,
        redis_key: str = "proxies",
        max_size: int = 10,
    ):
        self.redis_client = redis_client
        self.redis_key = redis_key
        self.max_size = max_size

    def replace(
        self,
        proxies: list,
    ) -> None:
        unique = []
        seen = set()
        normalized = []
        for item in proxies:
            # Accept plain proxy dictionaries and ProxyValidationResult objects.
            proxy = getattr(item, "proxy", item)
            health = float(getattr(item, "health", 0.0))
            normalized.append((health, proxy))

        for _, proxy in sorted(normalized, key=lambda item: item[0], reverse=True):
            identity = (proxy.get("http", ""), proxy.get("https", ""))
            if identity not in seen:
                seen.add(identity)
                unique.append(proxy)

        self.redis_client.replace_list(
            key=self.redis_key,
            values=unique[: self.max_size],
        )

    def acquire(self) -> dict[str, str] | None:
        """Atomically take the next proxy for one worker/task."""
        if hasattr(self.redis_client, "pop_first"):
            return self.redis_client.pop_first(key=self.redis_key)
        return self.get()

    def release(self, proxy: dict[str, str]) -> None:
        """Return a healthy proxy to the end of the rotation."""
        if hasattr(self.redis_client, "push_last"):
            self.redis_client.push_last(key=self.redis_key, value=proxy)

    def remove(self, proxy: dict[str, str]) -> None:
        """Remove the specific failing proxy."""
        if hasattr(self.redis_client, "remove_value"):
            self.redis_client.remove_value(key=self.redis_key, value=proxy)

    def get(self) -> dict[str, str] | None:
        return self.redis_client.get_first(
            key=self.redis_key,
        )

    def remove_current(self):
        return self.redis_client.remove_first(
            key=self.redis_key,
        )

    def is_empty(self) -> bool:
        return self.get() is None
