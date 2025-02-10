class Answer:
    def __init__(
            self,
            label: str = "",
            is_correct: bool = False
    ):
        self.label = label
        self.is_correct = is_correct

class Question:
    def __init__(
            self,
            label: str = "",
            hint: str = "",
            points: float = 0.0,
            answers: list = []
    ):
        self.label = label
        self.hint = hint
        self.points = points
        self.answers = answers

class QuizContent:
    def __init__(
            self,
            label: str = "",
            total_score: float = 0.0,
            questions: list = []
    ):
        self.label = label
        self.total_score = total_score
        self.questions = questions
