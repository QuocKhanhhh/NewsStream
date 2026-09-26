from typing import Any

from bs4 import BeautifulSoup


class ProxyScraper:
    def __init__(
        self,
        source_url: str,
        http_client: Any,
    ):
        self.source_url = source_url
        self.http_client = http_client

    def fetch(self, limit: int = 100) -> list[dict[str, str]]:
        content = self.http_client.get(self.source_url)

        return self._parse_proxy_table(
            content=content,
            limit=limit,
        )

    def _parse_proxy_table(
        self,
        content: bytes,
        limit: int,
    ) -> list[dict[str, str]]:
        soup = BeautifulSoup(content, "lxml")

        table = soup.find("table", class_="table")

        if table is None:
            table = soup.find("table")

        if table is None:
            raise ValueError(
                "Không tìm thấy bảng proxy"
            )

        body = table.find("tbody")

        if body is None:
            return []

        proxies = []

        for row in body.find_all("tr"):
            columns = [
                column.get_text(strip=True)
                for column in row.find_all("td")
            ]

            if len(columns) < 7:
                continue

            proxy = self._build_proxy(columns)

            if proxy:
                proxies.append(proxy)

            if len(proxies) >= limit:
                break

        return proxies

    @staticmethod
    def _build_proxy(
        columns: list[str],
    ) -> dict[str, str] | None:
        ip_address = columns[0]
        port = columns[1]
        https_supported = columns[6].lower() == "yes"

        if not ip_address or not port:
            return None

        protocol = "https" if https_supported else "http"
        proxy_url = f"{protocol}://{ip_address}:{port}"

        return {
            "http": proxy_url,
            "https": proxy_url,
        }