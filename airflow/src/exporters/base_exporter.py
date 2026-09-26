from abc import ABC, abstractmethod
from typing import Any

class BaseExporter(ABC):
    @abstractmethod
    def export(self, records: list[Any]) -> int:
        raise NotImplementedError("Subclasses must implement the export method.")


BaseParser = BaseExporter
