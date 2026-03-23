import sqlite3
import random

DB_PATH = "../SQL/playlist.db" # (server.pyと合わせたパスです)

def save_random_number_for_user(user_id):
    # 8桁の乱数（0埋めされた文字列、例: '01234567'）を生成
    random_id_str = f"{random.randint(0, 99999999):08d}"
    
    # データベース接続
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # ユーザーごとの乱数を保存・管理するテーブルを作成（存在しなければ）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_numbers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            random_number TEXT
        )
    ''')
    
    # DBにユーザーIDと乱数を保存
    cursor.execute('INSERT INTO user_numbers (user_id, random_number) VALUES (?, ?)', (str(user_id), random_id_str))
    conn.commit()
    conn.close()
    
    print(f"User {user_id} に 乱数 {random_id_str} を保存しました。")
    return random_id_str

# --- 実行用テストコード ---
if __name__ == "__main__":
    # 例: "user_123" というユーザーに対して生成＆保存を実行
    save_random_number_for_user("user_123")
