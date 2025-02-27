import json
import os

from UserInfo import UserInfo
from NavigationContent import NavigationContent, ButtonType
from ArticleContent import ArticleContent, ArticleContentType
from QuizContent import QuizContent, Question, Answer

class ContentNavigator:
    def __init__(
            self,
            content_file: str
            ) -> None:
        self.content_file = content_file
        self.content = {}
        self.navigation_filter = ""
        self.article_filter = ""
        self.quiz_filter = ""
        self.updateContent()

    def updateContent(self) -> None:
        self.content = {}
        self.navigation_filter = "^("
        self.article_filter = "^("
        self.quiz_filter = "^("

        data = open(self.content_file, "r", encoding="utf8")
        content = json.load(data)["content"]
        data.close()

        self.content = self.getJSONContent(content)
        
        self.navigation_filter += "Back)$"

        if self.article_filter[-1] == '|':
            self.article_filter = self.article_filter[:-1]
        self.article_filter += ")$"
        
        if self.quiz_filter[-1] == '|':
            self.quiz_filter = self.quiz_filter[:-1]
        self.quiz_filter += ")$"

    def getJSONContent(self, values: list) -> dict:
        markup = {}

        for elem in values:
            if elem["type"] == "navigation":
                self.navigation_filter += elem["name"] + "|"
                markup[elem["name"]] = NavigationContent(elem["name"], ButtonType.NAVIGATION, self.getJSONContent(elem["content"]))
            elif elem["type"] == "article":
                self.article_filter += elem["name"] + "|"
                markup[elem["name"]] = NavigationContent(elem["name"], ButtonType.ARTICLE, elem["content"])
            elif elem["type"] == "quiz":
                self.quiz_filter += elem["name"] + "|"
                markup[elem["name"]] = NavigationContent(elem["name"], ButtonType.QUIZ, elem["content"])

        return markup

    def moveTo(self, user_info: UserInfo, move_to: str) -> list:
        current_location = self.content
        
        history_size = len(user_info.history)
        if move_to == "Back" and history_size > 0:
            del user_info.history[history_size - 1:]

        for idx, elem in enumerate(user_info.history):
            if elem in current_location:
                current_location = current_location[elem].content
            else:
                del user_info.history[idx:]

        if move_to in current_location:
            current_location = current_location[move_to].content
            user_info.history.append(move_to)

        content = []

        for value in current_location.values():
            content.append(value)

        return content
    
    def getArticle(self, user_info: UserInfo, article: str) -> list:
        current_location = self.content

        for elem in user_info.history:
            if elem in current_location:
                current_location = current_location[elem].content
            else:
                return []

        if article not in current_location:
            return []

        ret = []
        article_content = current_location[article].content

        for elem in article_content:
            if elem["type"] == "text":
                ret.append(ArticleContent(ArticleContentType.TEXT, elem["content"]))
            elif elem["type"] == "image":
                ret.append(ArticleContent(ArticleContentType.IMAGE, elem["content"], elem["caption"]))
            elif elem["type"] == "video":
                ret.append(ArticleContent(ArticleContentType.VIDEO, elem["content"], elem["caption"]))

        return ret

    def getQuiz(self, user_info: UserInfo, quiz: str) -> QuizContent:
        current_location = self.content

        for elem in user_info.history:
            if elem in current_location:
                current_location = current_location[elem].content
            else:
                return None

        if quiz not in current_location:
            return None

        quiz_content = current_location[quiz]

        ret = QuizContent(quiz_content.label, quiz_content.content["total_score"], [])

        for elem in quiz_content.content["questions"]:
            new_question = Question(elem["name"], elem["hint"], elem["points"], [])
            for answer in elem["answers"]:
                new_question.answers.append(Answer(answer["text"], False if answer["is_correct"] == "false" else True))
            ret.questions.append(new_question)

        return ret

    def addNavigation(self, user_info: UserInfo, new_item: str) -> bool:
        data = open(self.content_file, "r+", encoding="utf8")
        content = json.load(data)

        current_content = content["content"]

        is_exist = False
        for elem in user_info.history:
            is_exist = False
            for value in current_content:
                if value["name"] == elem:
                    is_exist = True
                    current_content = value["content"]
                    break
        
        if not is_exist and len(user_info.history) > 0:
            data.close()
            return False
        
        for elem in current_content:
            if elem["name"] == new_item:
                data.close()
                return False

        new_elem = {}
        new_elem["type"] = "navigation"
        new_elem["name"] = new_item
        new_elem["content"] = []

        current_content.append(new_elem)

        new_json = json.dumps(content, ensure_ascii=False, indent=4)
        data.seek(0)
        data.write(new_json)
        data.truncate()
        data.close()

        self.updateContent()

        return True

    def removeItem(self, user_info: UserInfo, remove_item: str) -> bool:
        data = open(self.content_file, "r+", encoding="utf8")
        content = json.load(data)

        current_content = content["content"]
    
        is_exist = False
        for elem in user_info.history:
            is_exist = False
            for value in current_content:
                if value["name"] == elem:
                    is_exist = True
                    current_content = value["content"]
                    break
        
        if not is_exist and len(user_info.history) > 0:
            data.close()
            return False

        for idx, elem in enumerate(current_content):
            if elem["name"] == remove_item:
                if elem["type"] == "article":
                    for elem2 in elem["content"]:
                        if (elem2["type"] == "image" or elem2["type"] == "video") \
                            and os.path.isfile(elem2["content"]):
                            os.remove(elem2["content"])
                del current_content[idx]
                new_json = json.dumps(content, ensure_ascii=False, indent=4)
                data.seek(0)
                data.write(new_json)
                data.truncate()
                data.close()
                self.updateContent()
                return True
            
        data.close()
        return False

    def addArticle(self, user_info: UserInfo, new_item: str) -> bool:
        data = open(self.content_file, "r+", encoding="utf8")
        content = json.load(data)

        current_content = content["content"]

        is_exist = False
        for elem in user_info.history:
            is_exist = False
            for value in current_content:
                if value["name"] == elem:
                    is_exist = True
                    current_content = value["content"]
                    break
        
        if not is_exist and len(user_info.history) > 0:
            data.close()
            return False

        for elem in current_content:
            if elem["name"] == new_item:
                data.close()
                return False

        new_elem = {}
        new_elem["type"] = "article"
        new_elem["name"] = new_item
        new_elem["content"] = []

        current_content.append(new_elem)

        new_json = json.dumps(content, ensure_ascii=False, indent=4)
        data.seek(0)
        data.write(new_json)
        data.truncate()
        data.close()

        self.updateContent()

        return True

    def appendArticleContent(self, user_info: UserInfo, article: str, new_content: ArticleContent) -> bool:
        data = open(self.content_file, "r+", encoding="utf8")
        content = json.load(data)

        current_content = content["content"]

        is_exist = False
        for elem in user_info.history:
            is_exist = False
            for value in current_content:
                if value["name"] == elem:
                    is_exist = True
                    current_content = value["content"]
                    break
        
        if not is_exist and len(user_info.history) > 0:
            data.close()
            return False

        current_article_content = None

        for elem in current_content:
            if elem["name"] == article:
                current_article_content = elem["content"]

        if current_article_content == None:
            data.close()
            return False

        new_elem = {}
        new_elem["content"] = new_content.content
        
        if new_content.type == ArticleContentType.TEXT:
            new_elem["type"] = "text"
        elif new_content.type == ArticleContentType.IMAGE:
            new_elem["type"] = "image"
            new_elem["caption"] = new_content.caption
        elif new_content.type == ArticleContentType.VIDEO:
            new_elem["type"] = "video"
            new_elem["caption"] = new_content.caption 

        current_article_content.append(new_elem)

        new_json = json.dumps(content, ensure_ascii=False, indent=4)
        data.seek(0)
        data.write(new_json)
        data.truncate()
        data.close()

        self.updateContent()

        return True

    def addQuiz(self, user_info: UserInfo, name: str, content: str) -> bool:
        with open(self.content_file, "r+", encoding="utf8") as data:
            old_content = json.load(data)

            current_content = old_content["content"]

            is_exist = False
            for elem in user_info.history:
                is_exist = False
                for value in current_content:
                    if value["name"] == elem:
                        is_exist = True
                        current_content = value["content"]
                        break
            
            if not is_exist and len(user_info.history) > 0:
                data.close()
                return False
            
            for elem in current_content:
                if elem["name"] == name:
                    data.close()
                    return False

            new_content = json.loads(content)

            if "total_score" not in new_content:
                data.close()
                return False
            
            if "questions" not in new_content:
                data.close()
                return False

            for elem in new_content["questions"]:
                if ("name" not in elem) or ("points" not in elem) or \
                ("hint" not in elem) or ("answers" not in elem):
                    data.close()
                    return False

                for answer in elem["answers"]:
                    if ("text" not in answer) or ("is_correct" not in answer):
                        data.close()
                        return False

            new_quiz = { "type": "quiz", "name": name, "content": new_content }

            current_content.append(new_quiz)

            new_json = json.dumps(old_content, ensure_ascii=False, indent=4)
            data.seek(0)
            data.write(new_json)
            data.truncate()

            data.close()
            self.updateContent()
            return True
        
        return False
