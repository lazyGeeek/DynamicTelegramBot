from dataclasses import dataclass
from enum import Enum, auto
from typing import Any

class ButtonType(Enum):
    NAVIGATION = auto()
    ARTICLE = auto()
    TEST = auto()

@dataclass
class NavigationContent:
    def __init__(
        self,
        label: str,
        type: ButtonType = ButtonType.NAVIGATION,
        content: Any = {}
    ):
        self.label = label
        self.type = type
        self.content = content
