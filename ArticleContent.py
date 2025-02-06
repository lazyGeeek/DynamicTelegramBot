from dataclasses import dataclass
from enum import Enum, auto

class ArticleContentType(Enum):
    TEXT = auto()
    IMAGE = auto()
    VIDEO = auto()

@dataclass
class ArticleContent:
    def __init__(
        self,
        type: ArticleContentType = ArticleContentType.TEXT,
        content: str = "",
        caption: str = ""
    ):
        self.type = type
        self.content = content
        self.caption = caption
