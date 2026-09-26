import json
import logging
from dataclasses import asdict, dataclass

logger = logging.getLogger(__name__)


@dataclass
class FeedMetrics:
    source: str
    items_read: int = 0
    items_valid: int = 0
    items_rejected: int = 0
    messages_published: int = 0
    duration_ms: float = 0.0
    http_status: int | None = None
    error: str | None = None

    def as_dict(self) -> dict:
        return asdict(self)

    def log(self) -> dict:
        payload = self.as_dict()
        logger.info("feed_metrics=%s", json.dumps(payload, ensure_ascii=False, sort_keys=True))
        return payload
