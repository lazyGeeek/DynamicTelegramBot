from dataclasses import dataclass

@dataclass
class UserInfo:
    def __init__(
        self,
        first_name: str,
        user_id: int = -1,
        chat_id: int = -1
    ):
        self.first_name = first_name
        self.user_id = user_id
        self.chat_id = chat_id
        self.is_admin = True
        self.history = []
        self.last_article = ""
