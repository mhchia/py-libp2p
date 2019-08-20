from abc import ABC, abstractmethod


class IRawConnection(ABC):
    """
    A Raw Connection provides a Reader and a Writer
    """

    initiator: bool

    @abstractmethod
    async def write(self, data: bytes) -> None:
        pass

    @abstractmethod
    async def read(self, n: int = -1) -> bytes:
        pass

    @abstractmethod
    def close(self) -> None:
        pass

    @abstractmethod
    def next_stream_id(self) -> int:
        pass
