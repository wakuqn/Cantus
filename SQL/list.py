import sqlite3
import random
import os

# プレイリストフォルダのパス (環境に合わせて調整してください)
PLAYLIST_DIR = '/Users/hiro/Desktop/Cantus/playlist'

# 1. データベースに接続 (ファイルがなければ作成される)
conn = sqlite3.connect('SQL/playlist.db')
cursor = conn.cursor()

# フォルダからファイルを1つランダムに選ぶ
target_filename = None
if os.path.exists(PLAYLIST_DIR):
    # 隠しファイル（.で始まるもの）を除外してリスト取得
    files = [f for f in os.listdir(PLAYLIST_DIR) if not f.startswith('.')]
    if files:
        target_filename = random.choice(files)
    else:
        print("プレイリストフォルダにファイルがありません。")
else:
    print(f"フォルダが見つかりません: {PLAYLIST_DIR}")

# 2. テーブル作成 (データ保持のため、あれば作成しない設定に変更)
cursor.execute('''
    CREATE TABLE IF NOT EXISTS numbers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT,
        integer_val INTEGER
    )
''')

if target_filename:
    # すでに登録されているかチェック
    cursor.execute('SELECT id FROM numbers WHERE filename = ?', (target_filename,))
    existing = cursor.fetchone()

    if existing:
        print(f"ファイル '{target_filename}' はすでに紐付け済みです。保存しません。")
    else:
        # 3. 保存する数字データ
        my_int = random.randint(00000000, 99999999)
        # 4. データを挿入
        cursor.execute('INSERT INTO numbers (filename, integer_val) VALUES (?, ?)', (target_filename, my_int))
        conn.commit()
        print(f"ファイル '{target_filename}' に数字 {my_int} を紐付けて保存しました。")
else:
    print("ファイルが選択されませんでした。")

# 6. 接続を閉じる
conn.close()