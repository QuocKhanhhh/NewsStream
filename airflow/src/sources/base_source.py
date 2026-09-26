from abc import ABC, abstractmethod

class BaseSource(ABC):
    @abstractmethod
    def fetch(self) -> bytes:
        raise NotImplementedError
    