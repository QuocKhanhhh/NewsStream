from abc import ABC, abstractmethod
from typing import Any


class BaseParser(ABC):
    @abstractmethod
    def parse(self, content: bytes) -> list[Any]:
        """
        Abstract method to parse the given content.

        Args:
            content (bytes): The content to be parsed.

        Returns:
            Any: The parsed result.
        """
        raise NotImplementedError("Subclasses must implement the parse method.")
    