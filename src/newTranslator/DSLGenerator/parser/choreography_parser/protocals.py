from typing import List, Optional, Tuple, Any, Protocol

class ElementProtocol(Protocol):
    def deferred_init(self) -> None:
        pass
    id: str

class GraphProtocol(Protocol):
    def get_element_with_id(self, id: str) -> ElementProtocol:
        pass