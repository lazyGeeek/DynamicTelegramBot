import logging
import copy
import os.path

from enum import Enum, auto
from random import shuffle

from telegram import Update, ReplyKeyboardRemove, KeyboardButton, ReplyKeyboardMarkup#, Poll
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters
)

from ContentNavigator import ContentNavigator, ArticleContent, ArticleContentType
from UserInfo import UserInfo

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

class BotActions(Enum):
    MENU = auto()
    ADD_ITEM = auto()
    ADD_NAVIGATION = auto()
    ADD_ARTICLE = auto()
    ADD_ARTICLE_NAME = auto()
    SELECT_ARTICLE_CONTENT_TYPE = auto()
    ADD_ARTICLE_CONTENT = auto()
    SAVE_ARTICLE_TEXT_CONTENT = auto()
    SAVE_ARTICLE_IMAGE_CONTENT = auto()
    SAVE_ARTICLE_VIDEO_CONTENT = auto()
    ASK_QUESTION = auto()
    ADD_QUIZ_CONTENT = auto()
    SAVE_QUIZ = auto()
    DONE_ACTION = auto()
    REMOVE_ITEM = auto()

class TelegramBot:
    def __init__(self, token: str ) -> None:
        self.users = {}
        self.navigator = ContentNavigator("bot_content.json")

        self.navigation_helper = NavigationHelper(self)
        self.article_helper = ArticleHelper(self)
        self.quiz_helper = QuizHelper(self)

        self.application = Application.builder().token(token).build()
        # global conv_handler
        self.conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", self.startMenu)],
            states={
                BotActions.MENU: [MessageHandler(filters.Regex("^Add$"), self.addItem),
                                  MessageHandler(filters.Regex("^Delete$"), self.removeItemStart)],
                BotActions.ADD_ITEM: [MessageHandler(filters.Regex("^Navigation$"), self.navigation_helper.addNavigation),
                                      MessageHandler(filters.Regex("^Article$"), self.article_helper.addArticle),
                                      MessageHandler(filters.Regex("^Quiz$"), self.quiz_helper.addQuizName),
                                      MessageHandler(filters.Regex("^Back$"), self.updateMenu)],
                BotActions.ADD_NAVIGATION: [MessageHandler(filters.TEXT, self.navigation_helper.saveNavigation)],
                BotActions.ADD_ARTICLE_NAME: [MessageHandler(filters.TEXT, self.article_helper.addArticleName)],
                BotActions.SELECT_ARTICLE_CONTENT_TYPE: [MessageHandler(filters.TEXT, self.article_helper.articleSelectContentType)],
                BotActions.ADD_ARTICLE_CONTENT: [MessageHandler(filters.Regex("^Text$"), self.article_helper.addArticleTextContent),
                                                 MessageHandler(filters.Regex("^Image$"), self.article_helper.addArticleImageContent),
                                                 MessageHandler(filters.Regex("^Video$"), self.article_helper.addArticleVideoContent),
                                                 MessageHandler(filters.Regex("^Finish$"), self.article_helper.doneAddingArticle)],
                BotActions.SAVE_ARTICLE_TEXT_CONTENT: [MessageHandler(filters.TEXT, self.article_helper.saveArticleTextContent)],
                BotActions.SAVE_ARTICLE_IMAGE_CONTENT: [MessageHandler(filters.PHOTO, self.article_helper.saveArticleImageContent)],
                BotActions.SAVE_ARTICLE_VIDEO_CONTENT: [MessageHandler(filters.VIDEO, self.article_helper.saveArticleVideoContent)],
                BotActions.ASK_QUESTION: [MessageHandler(filters.TEXT, self.quiz_helper.askQuestion)],
                BotActions.ADD_QUIZ_CONTENT: [MessageHandler(filters.TEXT, self.quiz_helper.addQuizContent)],
                BotActions.SAVE_QUIZ: [MessageHandler(filters.Document.ALL, self.quiz_helper.saveQuiz)],
                BotActions.DONE_ACTION: [MessageHandler(filters.Regex("^Done$"), self.doneAction)],
                BotActions.REMOVE_ITEM: [MessageHandler(filters.Regex("^Back$"), self.updateMenu)]
            },
            fallbacks=[CommandHandler("cancel", self.cancel)]
        )

        self.navigation_message_handler = MessageHandler(filters.TEXT, self.updateMenu)
        self.remove_navigation_message_handler = MessageHandler(filters.TEXT, self.removeItemFinish)
        self.remove_article_message_handler = MessageHandler(filters.TEXT, self.removeItemFinish)
        self.remove_quiz_message_handler = MessageHandler(filters.TEXT, self.removeItemFinish)
        self.article_message_handler = MessageHandler(filters.TEXT, self.article_helper.printArticle)
        self.quiz_message_handler = MessageHandler(filters.TEXT, self.quiz_helper.startQuiz)

        self.updateFilters()

        self.application.add_handler(self.conv_handler)
        self.application.add_handler(CommandHandler("start", self.doneAction))

    def updateFilters(self) -> None:
        navigation_filter = self.navigator.navigation_filter
        article_filter = self.navigator.article_filter
        quiz_filter = self.navigator.quiz_filter

        if navigation_filter != "" and navigation_filter != "^()$":
            self.navigation_message_handler = MessageHandler(filters.Regex(navigation_filter), self.updateMenu)
            self.remove_navigation_message_handler = MessageHandler(filters.Regex(navigation_filter), self.removeItemFinish)
            self.conv_handler.states[BotActions.MENU].append(self.navigation_message_handler)
            self.conv_handler.states[BotActions.REMOVE_ITEM].append(self.remove_navigation_message_handler)
        else:
            if self.navigation_message_handler in self.conv_handler.states[BotActions.MENU]:
                self.conv_handler.states[BotActions.MENU].remove(self.navigation_message_handler)
            if self.remove_navigation_message_handler in self.conv_handler.states[BotActions.REMOVE_ITEM]:
                self.conv_handler.states[BotActions.REMOVE_ITEM].remove(self.remove_navigation_message_handler)

        if article_filter != "" and article_filter != "^()$":
            self.article_message_handler = MessageHandler(filters.Regex(article_filter), self.article_helper.printArticle)
            self.remove_article_message_handler = MessageHandler(filters.Regex(article_filter), self.removeItemFinish)
            self.conv_handler.states[BotActions.MENU].append(self.article_message_handler)
            self.conv_handler.states[BotActions.REMOVE_ITEM].append(self.remove_article_message_handler)
        else:
            if self.article_message_handler in self.conv_handler.states[BotActions.MENU]:
                self.conv_handler.states[BotActions.MENU].remove(self.article_message_handler)
            if self.remove_article_message_handler in self.conv_handler.states[BotActions.REMOVE_ITEM]:
                self.conv_handler.states[BotActions.REMOVE_ITEM].remove(self.remove_article_message_handler)

        if quiz_filter != "" and quiz_filter != "^()$":
            self.quiz_message_handler = MessageHandler(filters.Regex(quiz_filter), self.quiz_helper.startQuiz)
            self.remove_quiz_message_handler = MessageHandler(filters.Regex(quiz_filter), self.removeItemFinish)
            self.conv_handler.states[BotActions.MENU].append(self.quiz_message_handler)
            self.conv_handler.states[BotActions.REMOVE_ITEM].append(self.remove_quiz_message_handler)
        else:
            if self.quiz_message_handler in self.conv_handler.states[BotActions.MENU]:
                self.conv_handler.states[BotActions.MENU].remove(self.quiz_message_handler)
            if self.remove_quiz_message_handler in self.conv_handler.states[BotActions.REMOVE_ITEM]:
                self.conv_handler.states[BotActions.REMOVE_ITEM].remove(self.remove_quiz_message_handler)

    def run(self) -> None:
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)

    async def clearPreviousMessages(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        user = update.message.from_user
        try:
            await update.message.delete()
        except:
            logger.info("Can't delete message from %s", user.first_name)

        try:
            if "message_id" in context.user_data:
                await context.bot.delete_message(self.users[user.id].chat_id, context.user_data["message_id"])
        except:
            logger.info("Can't delete bot message")

    async def startMenu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = update.message.from_user
        logger.info("User %s start conversation", user.first_name)

        if user.id not in self.users:
            self.users[user.id] = UserInfo(user.first_name, user.id,
                                           update.effective_chat.id)

        return await self.updateMenu(update, context)

    async def updateMenu(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = update.message.from_user
        logger.info("User %s selecting menu", user.first_name)

        user_info = self.users[user.id]
        new_content = self.navigator.moveTo(user_info, update.message.text)
        temp_list = []
        buttons_markup = [temp_list]
        
        for idx, elem in enumerate(new_content):
            if idx % 2 == 0 and idx != 0:
                temp_list = []
                buttons_markup.append(temp_list)
            temp_list.append(KeyboardButton(elem.label))

        if len(user_info.history) > 0:
            buttons_markup.append([KeyboardButton("Back")])

        if user_info.is_admin:
            buttons_markup.append([KeyboardButton("Add"),
                                   KeyboardButton("Delete")])

        markup = ReplyKeyboardMarkup(buttons_markup, resize_keyboard=True)

        await self.clearPreviousMessages(update, context)

        new_message = await context.bot.send_message(user_info.chat_id, "Select value", reply_markup=markup)
        context.user_data["message_id"] = new_message.id

        return BotActions.MENU

    async def addItem(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = update.message.from_user
        logger.info("User %s adding item", user.first_name)

        await self.clearPreviousMessages(update, context)

        if not self.users[user.id].is_admin:
            return await self.updateMenu(update, context)

        markup = ReplyKeyboardMarkup([[KeyboardButton("Navigation"),
                                       KeyboardButton("Article"),
                                       KeyboardButton("Quiz"),
                                       KeyboardButton("Back")]],
                                       resize_keyboard=True)

        message = await update.message.reply_text("Select new item type", reply_markup=markup)
        context.user_data["messages_to_remove"] = [message.id]

        return BotActions.ADD_ITEM

    async def removeItemStart(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = update.message.from_user
        logger.info("User %s selecting item to remove", user.first_name)

        await self.clearPreviousMessages(update, context)

        if not self.users[user.id].is_admin:
            return await self.updateMenu(update, context)

        user_info = self.users[user.id]
        new_content = self.navigator.moveTo(user_info, update.message.text)
        temp_list = []
        buttons_markup = [temp_list]
        
        for idx, elem in enumerate(new_content):
            if idx % 2 == 0 and idx != 0:
                temp_list = []
                buttons_markup.append(temp_list)
            temp_list.append(KeyboardButton(elem.label))
        
        buttons_markup.append([KeyboardButton("Back")])

        markup = ReplyKeyboardMarkup(buttons_markup, resize_keyboard=True)

        new_message = await context.bot.send_message(self.users[user.id].chat_id, "Select item to delete", reply_markup=markup)

        context.user_data["messages_to_remove"] = [new_message.id]

        return BotActions.REMOVE_ITEM

    async def removeItemFinish(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = update.message.from_user
        logger.info("User %s removing item", user.first_name)

        context.user_data["messages_to_remove"].append(update.message.id)

        if not self.users[user.id].is_admin:
            return await self.updateMenu(update, context)

        user_info = self.users[user.id]
        if self.navigator.removeItem(user_info, update.message.text):
            new_message = await context.bot.send_message(self.users[user.id].chat_id, "The item is deleted",
                                                         reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Done")]], 
                                                         resize_keyboard=True))
            context.user_data["messages_to_remove"].append(new_message.id)
        else:
            new_message = await context.bot.send_message(self.users[user.id].chat_id, "Can't delete item",
                                                         reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Done")]], 
                                                         resize_keyboard=True))
            context.user_data["messages_to_remove"].append(new_message.id)

        return BotActions.DONE_ACTION
    
    async def doneAction(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = update.message.from_user
        logger.info("User %s done action", user.first_name)
        user_info = self.users[user.id]

        try:
            if "messages_to_remove" in context.user_data:
                await context.bot.delete_messages(user_info.chat_id, context.user_data["messages_to_remove"])
                del context.user_data["messages_to_remove"]
        except:
            logger.info("Can't can't clear message history from %s", user.first_name)

        try:
            if "message_id" in context.user_data:
                await context.bot.delete_message(self.users[user.id].chat_id, context.user_data["message_id"])
            del context.user_data["message_id"]
        except:
            logger.info("Can't delete message from %s", user.first_name)

        return await self.updateMenu(update, context)

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = update.message.from_user
        logger.info("User %s canceled the conversation.", user.first_name)

        await context.bot.send_message(self.users[user.id].chat_id, "Thank you for your cooperation", reply_markup=ReplyKeyboardRemove())

        if user.id in self.users:
            del self.users[user.id]

        return ConversationHandler.END

class NavigationHelper:
    def __init__(self, bot: TelegramBot) -> None:
        self.bot = bot

    async def addNavigation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = update.message.from_user
        logger.info("User %s adding Navigation", user.first_name)

        new_message = await update.message.reply_text("Enter navigation name", reply_markup=ReplyKeyboardRemove())
        context.user_data["messages_to_remove"].append(new_message.id)
        context.user_data["messages_to_remove"].append(update.message.id)

        return BotActions.ADD_NAVIGATION

    async def saveNavigation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = update.message.from_user
        logger.info("User %s saving Navigation", user.first_name)

        user_info = self.bot.users[user.id]
        if self.bot.navigator.addNavigation(user_info, update.message.text):
            new_message = await context.bot.send_message(user_info.chat_id, "Navigation added successfully", 
                                                         reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Done")]], 
                                                                                          resize_keyboard=True))
            context.user_data["messages_to_remove"].append(new_message.id)
        else:
            new_message = await context.bot.send_message(user_info.chat_id, "Adding navigation failed", 
                                                         reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Done")]], 
                                                                                          resize_keyboard=True))
            context.user_data["messages_to_remove"].append(new_message.id)

        context.user_data["messages_to_remove"].append(update.message.id)

        self.bot.updateFilters()
        return BotActions.DONE_ACTION

class ArticleHelper:
    def __init__(self, bot: TelegramBot) -> None:
        self.bot = bot

    async def addArticle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = update.message.from_user
        logger.info("User %s adding new article", user.first_name)

        new_message = await update.message.reply_text("Enter new article name", reply_markup=ReplyKeyboardRemove())
        context.user_data["messages_to_remove"].append(new_message.id)
        context.user_data["messages_to_remove"].append(update.message.id)

        return BotActions.ADD_ARTICLE_NAME

    async def addArticleName(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = update.message.from_user
        logger.info("User %s adding new article name", user.first_name)

        context.user_data["messages_to_remove"].append(update.message.id)
        user_info = self.bot.users[user.id]

        if not self.bot.navigator.addArticle(user_info, update.message.text):
            new_message = await context.bot.send_message(self.bot.users[user.id].chat_id, "Can't add new article",
                                                         reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Done")]],
                                                                                          resize_keyboard=True))
            context.user_data["messages_to_remove"].append(new_message.id)
            return BotActions.DONE_ACTION
        
        user_info.last_article = update.message.text
        self.bot.updateFilters()

        markup = ReplyKeyboardMarkup([[KeyboardButton("Text"),
                                       KeyboardButton("Image"),
                                       KeyboardButton("Video")]],
                                       resize_keyboard=True)
        
        new_message = await context.bot.send_message(self.bot.users[user.id].chat_id,
                                                     "Select new article content type", reply_markup=markup)

        context.user_data["messages_to_remove"].append(new_message.id)
        return BotActions.ADD_ARTICLE_CONTENT
    
    async def articleSelectContentType(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = update.message.from_user
        logger.info("User %s selecting article type", user.first_name)
        
        markup = ReplyKeyboardMarkup([[KeyboardButton("Text"),
                                       KeyboardButton("Image"),
                                       KeyboardButton("Video"),
                                       KeyboardButton("Finish")]],
                                       resize_keyboard=True)
        
        new_message = await context.bot.send_message(self.bot.users[user.id].chat_id,
                                                     "Select new article content type", reply_markup=markup)
        context.user_data["messages_to_remove"].append(new_message.id)
        context.user_data["messages_to_remove"].append(update.message.id)

        return BotActions.ADD_ARTICLE_CONTENT

    async def addArticleTextContent(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = update.message.from_user
        logger.info("User %s adding new article text", user.first_name)

        new_message = await context.bot.send_message(self.bot.users[user.id].chat_id,
                                                     "Enter article text", reply_markup=ReplyKeyboardRemove())
        context.user_data["messages_to_remove"].append(new_message.id)
        context.user_data["messages_to_remove"].append(update.message.id)

        return BotActions.SAVE_ARTICLE_TEXT_CONTENT

    async def saveArticleTextContent(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = update.message.from_user
        logger.info("User %s saving new article text", user.first_name)

        new_text = ArticleContent(ArticleContentType.TEXT, update.message.text)
        user_info = self.bot.users[user.id]
        if self.bot.navigator.appendArticleContent(user_info, user_info.last_article, new_text):
            new_message = await context.bot.send_message(self.bot.users[user.id].chat_id, "Article text added")
            context.user_data["messages_to_remove"].append(new_message.id)
        else:
            new_message = await context.bot.send_message(self.bot.users[user.id].chat_id, "Can't add article text")
            context.user_data["messages_to_remove"].append(new_message.id)

        context.user_data["messages_to_remove"].append(update.message.id)
        self.bot.updateFilters()

        return await self.articleSelectContentType(update, context)
    
    async def addArticleImageContent(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = update.message.from_user
        logger.info("User %s adding new article image", user.first_name)

        new_message = await context.bot.send_message(self.bot.users[user.id].chat_id,
                                                     "Upload image and caption", reply_markup=ReplyKeyboardRemove())
        
        context.user_data["messages_to_remove"].append(new_message.id)
        context.user_data["messages_to_remove"].append(update.message.id)

        return BotActions.SAVE_ARTICLE_IMAGE_CONTENT
    
    async def saveArticleImageContent(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = update.message.from_user
        logger.info("User %s saving new article image", user.first_name)

        file_id = update.message.photo[-1].file_id
        new_file = await context.bot.get_file(file_id)
        file_path = f"images/{file_id}.jpg"

        if not os.path.isfile(file_path):
            await new_file.download_to_drive(file_path)

        new_image = ArticleContent(ArticleContentType.IMAGE, file_path, update.message.caption)
        user_info = self.bot.users[user.id]
        
        if self.bot.navigator.appendArticleContent(user_info, user_info.last_article, new_image):
            new_message = await context.bot.send_message(self.bot.users[user.id].chat_id,
                                                         "Image uploaded", reply_markup=ReplyKeyboardRemove())
            context.user_data["messages_to_remove"].append(new_message.id)
        else:
            new_message = await context.bot.send_message(self.bot.users[user.id].chat_id,
                                                         "Can't upload image", reply_markup=ReplyKeyboardRemove())
            context.user_data["messages_to_remove"].append(new_message.id)
        self.bot.updateFilters()

        context.user_data["messages_to_remove"].append(update.message.id)

        return await self.articleSelectContentType(update, context)

    async def addArticleVideoContent(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = update.message.from_user
        logger.info("User %s adding new article video", user.first_name)

        new_message = await context.bot.send_message(self.bot.users[user.id].chat_id,
                                                     "Upload video and caption", reply_markup=ReplyKeyboardRemove())
        context.user_data["messages_to_remove"].append(new_message.id)
        context.user_data["messages_to_remove"].append(update.message.id)

        return BotActions.SAVE_ARTICLE_VIDEO_CONTENT

    async def saveArticleVideoContent(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = update.message.from_user
        logger.info("User %s saving new article video", user.first_name)

        file_id = update.message.video.file_id
        new_file = await context.bot.get_file(file_id)
        file_path = f"videos/{update.message.video.file_name}"

        if not os.path.isfile(file_path):
            await new_file.download_to_drive(file_path)

        new_video = ArticleContent(ArticleContentType.VIDEO, file_path, update.message.caption)
        user_info = self.bot.users[user.id]

        if self.bot.navigator.appendArticleContent(user_info, user_info.last_article, new_video):
            new_message = await context.bot.send_message(self.bot.users[user.id].chat_id,
                                                         "Video uploaded", reply_markup=ReplyKeyboardRemove())
            context.user_data["messages_to_remove"].append(new_message.id)
        else:
            new_message = await context.bot.send_message(self.bot.users[user.id].chat_id,
                                                         "Can't upload video", reply_markup=ReplyKeyboardRemove())
            context.user_data["messages_to_remove"].append(new_message.id)
        self.bot.updateFilters()

        context.user_data["messages_to_remove"].append(update.message.id)

        return await self.articleSelectContentType(update, context)
    
    async def doneAddingArticle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = update.message.from_user
        logger.info("User %s finished adding article", user.first_name)

        new_message = await context.bot.send_message(self.bot.users[user.id].chat_id, "New article added",
                                                     reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Done")]],
                                                                                      resize_keyboard=True))
        context.user_data["messages_to_remove"].append(new_message.id)
        context.user_data["messages_to_remove"].append(update.message.id)
        self.bot.updateFilters()

        return BotActions.DONE_ACTION

    async def printArticle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = update.message.from_user
        user_info = self.bot.users[user.id]
        logger.info("User %s print article", user.first_name)

        article_content = self.bot.navigator.getArticle(user_info, update.message.text)

        await self.bot.clearPreviousMessages(update, context)

        if len(article_content) == 0:
            new_message = await context.bot.send_message(self.bot.users[user.id].chat_id,
                                                         "Can't open article", reply_markup=ReplyKeyboardRemove())
            context.user_data["messages_to_remove"] = [update.message.id, new_message.id]
            return BotActions.DONE_ACTION

        context.user_data["messages_to_remove"] = [update.message.id]

        for elem in article_content:
            if elem.type == ArticleContentType.TEXT:
                new_message = await context.bot.send_message(user_info.chat_id, elem.content)
                context.user_data["messages_to_remove"].append(new_message.id)
            elif elem.type == ArticleContentType.IMAGE:
                with open(elem.content, "rb") as image:
                    new_message = await context.bot.send_photo(user_info.chat_id, image, caption=elem.caption)
                    context.user_data["messages_to_remove"].append(new_message.id)
                    image.close()
            elif elem.type == ArticleContentType.VIDEO:
                with open(elem.content, "rb") as video:
                    new_message = await context.bot.send_video(user_info.chat_id, video, caption=elem.caption, supports_streaming=True)
                    context.user_data["messages_to_remove"].append(new_message.id)
                    video.close()

        new_message = await context.bot.send_message(user_info.chat_id, "Done",
                                                     reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Done")]], 
                                                     resize_keyboard=True))
        context.user_data["messages_to_remove"].append(new_message.id)

        return BotActions.DONE_ACTION
    
class QuizHelper:
    def __init__(self, bot: TelegramBot) -> None:
        self.bot = bot

    async def addQuizName(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = update.message.from_user
        logger.info("User %s adding quiz name", user.first_name)

        await self.bot.clearPreviousMessages(update, context)

        new_message = await context.bot.send_message(self.bot.users[user.id].chat_id, "Enter quiz name",
                                                     reply_markup=ReplyKeyboardRemove())
        
        context.user_data["messages_to_remove"].append(new_message.id)

        return BotActions.ADD_QUIZ_CONTENT
    
    async def addQuizContent(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = update.message.from_user
        logger.info("User %s adding quiz content", user.first_name)

        context.user_data["new_quiz_name"] = update.message.text
        context.user_data["messages_to_remove"].append(update.message.id)

        new_message = await context.bot.send_message(self.bot.users[user.id].chat_id, "Upload file with quiz questions",
                                                     reply_markup=ReplyKeyboardRemove())
        
        context.user_data["messages_to_remove"].append(new_message.id)
    
        return BotActions.SAVE_QUIZ
    
    async def saveQuiz(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = update.message.from_user
        logger.info("User %s saving quiz", user.first_name)

        context.user_data["messages_to_remove"].append(update.message.id)

        file_id = update.message.document.file_id
        new_file = await context.bot.get_file(file_id)

        byte_content = await new_file.download_as_bytearray()
        content = byte_content.decode("utf-8")

        if self.bot.navigator.addQuiz(self.bot.users[user.id], context.user_data["new_quiz_name"], content):
            new_message = await context.bot.send_message(self.bot.users[user.id].chat_id, "Quiz added successfully",
                                                         reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Done")]], 
                                                         resize_keyboard=True))
            context.user_data["messages_to_remove"].append(new_message.id)
            self.bot.updateFilters()
        else:
            new_message = await context.bot.send_message(self.users[user.id].chat_id, "Error happend",
                                                         reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Done")]], 
                                                         resize_keyboard=True))
            context.user_data["messages_to_remove"].append(new_message.id)

        if "new_quiz_name" in context.user_data:
            del context.user_data["new_quiz_name"]

        return BotActions.DONE_ACTION
    
    async def startQuiz(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = update.message.from_user
        logger.info("User %s start quiz", user.first_name)

        user_info = self.bot.users[user.id]

        current_quiz = self.bot.navigator.getQuiz(user_info, update.message.text)
        if current_quiz is None:
            return await self.bot.updateMenu(self, update)
        
        if "message_id" in context.user_data:
            await context.bot.delete_message(user_info.chat_id, context.user_data["message_id"])

        context.user_data["quiz_questions"] = copy.deepcopy(current_quiz.questions)
        context.user_data["total_score"] = current_quiz.total_score
        context.user_data["current_score"] = 0.0
        context.user_data["messages_to_remove"] = []

        return await self.askQuestion(update, context)

    async def askQuestion(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = update.message.from_user
        logger.info("User %s asking question", user.first_name)
        user_info = self.bot.users[user.id]

        is_correct = False
        if "current_question" in context.user_data:
            for elem in context.user_data["current_question"].answers:
                if elem.is_correct and elem.label == update.message.text:
                    context.user_data["current_score"] += context.user_data["current_question"].points
                    message = await context.bot.send_message(user_info.chat_id, "Correct")
                    context.user_data["messages_to_remove"].append(message.id)
                    is_correct = True
                    break

            if not is_correct:
                message = await context.bot.send_message(user_info.chat_id,
                                                        "Incorrect\n" + context.user_data["current_question"].hint)
                context.user_data["messages_to_remove"].append(message.id)


        if len(context.user_data["quiz_questions"]) == 0:
            new_message = await context.bot.send_message(user_info.chat_id,
                                                          "Quiz finished.\nYour score is: " +
                                                          str(context.user_data["current_score"]) + "/" +
                                                          str(context.user_data["total_score"]),
                                                          reply_markup=ReplyKeyboardMarkup([[KeyboardButton("Done")]], 
                                                          resize_keyboard=True))
            context.user_data["message_id"] = new_message.id
            context.user_data["messages_to_remove"].append(new_message.id)
            context.user_data["messages_to_remove"].append(update.message.id)

            del context.user_data["quiz_questions"]
            del context.user_data["current_question"]
            del context.user_data["current_score"]
            del context.user_data["total_score"]
            return BotActions.DONE_ACTION

        question = context.user_data["quiz_questions"].pop(0)

        temp_list = []
        buttons_markup = [temp_list]

        shuffle(question.answers)
        for idx, elem in enumerate(question.answers):
            if idx % 2 == 0 and idx != 0:
                temp_list = []
                buttons_markup.append(temp_list)
            temp_list.append(KeyboardButton(elem.label))

        markup = ReplyKeyboardMarkup(buttons_markup, resize_keyboard=True)
        
        new_message = await context.bot.send_message(user_info.chat_id, question.label, reply_markup=markup)

        context.user_data["messages_to_remove"].append(update.message.id)
        context.user_data["messages_to_remove"].append(new_message.id)
        context.user_data["current_question"] = question

        return BotActions.ASK_QUESTION