import sqlite3
from typing import Any

class DBManager:
    def __init__(self, db_file: str) -> None:
        self.db_file = db_file

    def initDB(self) -> None: 
        connect = sqlite3.connect(self.db_file)
        cursor = connect.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS quiz_results (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            quiz_name TEXT NOT NULL,
            quiz_score TEXT NOT NULL,
            UNIQUE(user_id,quiz_name)
        )
        """)
        connect.commit()
        connect.close()
    
    def getQuizScore(self, user_id: int, quiz_name: str) -> Any:
        connect = sqlite3.connect(self.db_file)
        cursor = connect.cursor()
        res = cursor.execute("SELECT quiz_score FROM quiz_results WHERE user_id = ? AND quiz_name = ?", (user_id, quiz_name))
        quiz_result = res.fetchone()
        print(type(quiz_result))
        print(quiz_result)
        connect.close()
        return quiz_result

    def getAllScores(self, user_id: int) -> list:
        connect = sqlite3.connect(self.db_file)
        cursor = connect.cursor()
        res = []
        for row in cursor.execute("SELECT quiz_name, quiz_score FROM quiz_results WHERE user_id = ?", [user_id]):
            res.append(row)
        connect.close()
        return res
    
    def addUserResult(self, user_id: int, quiz_name: str, quiz_score: str) -> None:
        connect = sqlite3.connect(self.db_file)
        cursor = connect.cursor()
        cursor.execute("""
            INSERT INTO quiz_results (quiz_score, user_id, quiz_name)  VALUES (?, ?, ?)
                ON CONFLICT (user_id, quiz_name) DO
                    UPDATE SET quiz_score = ? WHERE user_id = ? AND quiz_name = ?
        """, (quiz_score, user_id, quiz_name, quiz_score, user_id, quiz_name))
        connect.commit()
        connect.close()

    def deleteQuizFromDB(self, quiz_name: str) -> None:
        connect = sqlite3.connect(self.db_file)
        cursor = connect.cursor()
        cursor.execute("DELETE FROM quiz_results WHERE quiz_name = ?", (quiz_name,))
        connect.commit()
        connect.close()
