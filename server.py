import http.server
import socketserver
import json
import sqlite3
import os
from urllib.parse import urlparse, parse_qs, quote
import random

PORT = 8000
# list.pyが書き込むデータベースファイルを指定
DB_PATH = 'SQL/playlist.db'

# データベースの初期化（テーブル作成）
def init_db():
    # データベースディレクトリが存在しない場合は作成
    db_dir = os.path.dirname(DB_PATH)
    if db_dir: os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # プレイリスト一覧を管理するテーブル
    cursor.execute('CREATE TABLE IF NOT EXISTS playlists (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT)')
    # プレイリスト内の曲を管理するテーブル
    cursor.execute('CREATE TABLE IF NOT EXISTS playlist_songs (playlist_id INTEGER, filename TEXT)')
    conn.commit()
    conn.close()

class MyHttpRequestHandler(http.server.SimpleHTTPRequestHandler):
    """
    通常のファイル配信に加え、特定のAPIリクエスト(/api/playlists)を処理するハンドラ
    """
    def do_GET(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path

        if path == '/api/playlists':
            self.handle_api_playlists()
        elif path == '/api/get_number':
            self.handle_api_get_number(parsed_url.query)
        elif path == '/api/get_playlists':
            self.handle_api_get_playlists()
        elif path == '/api/get_playlist_songs':
            self.handle_api_get_playlist_songs(parsed_url.query)
        else:
            # 上記以外の場合は、通常のファイルを探して返す
            super().do_GET()

    def do_POST(self):
        """ファイルのアップロード処理 (/upload)"""
        if self.path == '/upload':
            self.handle_upload()
        elif self.path == '/api/create_playlist':
            self.handle_api_create_playlist()
        elif self.path == '/api/add_to_playlist':
            self.handle_api_add_to_playlist()
        else:
            self.send_error(404, "Not Found")

    def handle_upload(self):
        # ファイルサイズ制限 (10MB)
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 10 * 1024 * 1024:
            self.send_response(303)
            self.send_header('Location', '/playlist/test_playLiSt.html?error=FileTooLarge')
            self.end_headers()
            return

       # multipart/form-dataの解析
        fileitem = form['file']
        
        if fileitem.filename:
            # ファイル名を安全に取得 (パスを除去)
            filename = os.path.basename(fileitem.filename)
            save_path = os.path.join('playlist', filename)
            
            # 1. ファイルを保存
            os.makedirs('playlist', exist_ok=True) # フォルダがなければ作成
            with open(save_path, 'wb') as f:
                f.write(fileitem.file.read())

            # 2. データベースに登録 (list.pyと同様のロジック)
            self.register_to_db(filename)

            # 3. アップロードした曲のプレイヤー画面へリダイレクト
            self.send_response(303) # See Other
            # 日本語ファイル名に対応するためURLエンコードを行う
            self.send_header('Location', f'/playlist/test_playLiSt.html?file={quote(filename)}')
            self.end_headers()
        else:
            self.send_error(400, "Invalid file")

    def register_to_db(self, filename):
        """データベースにファイルとランダムな数値を登録"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # すでに登録されているか確認
            cursor.execute('SELECT id FROM numbers WHERE filename = ?', (filename,))
            if not cursor.fetchone():
                # 新規登録
                rand_num = random.randint(0, 99999999)
                cursor.execute('INSERT INTO numbers (filename, integer_val) VALUES (?, ?)', (filename, rand_num))
                conn.commit()
            
            conn.close()
        except Exception as e:
            print(f"Database error during upload: {e}")

    def handle_api_get_number(self, query):
        """ファイル名に紐付いた数値をデータベースから取得して返す"""
        query_components = parse_qs(query)
        filenames = query_components.get("file")
        filename = filenames[0] if filenames else None

        if not filename:
            self.send_error(400, "Bad Request: Missing 'file' parameter")
            return

        print(f"[API] 数値取得リクエスト: {filename}")
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('SELECT integer_val FROM numbers WHERE filename = ?', (filename,))
            row = cursor.fetchone()

            if row:
                number = row[0]
            else:
                # 数値が見つからない場合は自動生成して保存
                number = random.randint(0, 99999999)
                cursor.execute('INSERT INTO numbers (filename, integer_val) VALUES (?, ?)', (filename, number))
                conn.commit()
            
            conn.close()

            response_data = {'number': number}
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode('utf-8'))
        except Exception as e:
            self.send_error(500, f"Server error: {e}")

    def handle_api_playlists(self):
        """データベースからファイル名一覧を取得し、JSON形式で返す"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('SELECT filename FROM numbers WHERE filename IS NOT NULL ORDER BY id')
            rows = cursor.fetchall()
            conn.close()

            filenames = [row[0] for row in rows]

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(filenames).encode('utf-8'))

        except Exception as e:
            self.send_error(500, f"Server error: {e}")

    def handle_api_get_playlists(self):
        """作成済みのプレイリスト一覧を返す"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('SELECT id, name FROM playlists ORDER BY id')
            rows = cursor.fetchall()
            conn.close()
            
            playlists = [{'id': row[0], 'name': row[1]} for row in rows]
            self.send_json_response(playlists)
        except Exception as e:
            self.send_error(500, f"Server error: {e}")

    def handle_api_create_playlist(self):
        """新規プレイリストを作成"""
        length = int(self.headers.get('Content-Length', 0))
        data = json.loads(self.rfile.read(length))
        name = data.get('name')
        
        if name:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('INSERT INTO playlists (name) VALUES (?)', (name,))
            conn.commit()
            new_id = cursor.lastrowid
            conn.close()
            self.send_json_response({'status': 'success', 'id': new_id, 'name': name})
        else:
            self.send_error(400, "Missing name")

    def handle_api_add_to_playlist(self):
        """プレイリストに曲を追加"""
        length = int(self.headers.get('Content-Length', 0))
        data = json.loads(self.rfile.read(length))
        playlist_id = data.get('playlist_id')
        filename = data.get('filename')

        if playlist_id and filename:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('INSERT INTO playlist_songs (playlist_id, filename) VALUES (?, ?)', (playlist_id, filename))
            conn.commit()
            conn.close()
            self.send_json_response({'status': 'success'})
        else:
            self.send_error(400, "Missing parameters")

    def handle_api_get_playlist_songs(self, query):
        """特定のプレイリスト内の曲一覧を返す"""
        query_components = parse_qs(query)
        playlist_id = query_components.get("id", [None])[0]
        
        if playlist_id:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('SELECT filename FROM playlist_songs WHERE playlist_id = ?', (playlist_id,))
            rows = cursor.fetchall()
            conn.close()
            filenames = [row[0] for row in rows]
            self.send_json_response(filenames)
        else:
            self.send_error(400, "Missing playlist id")

    def send_json_response(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

if __name__ == '__main__':
    init_db() # 起動時にテーブル作成
    with socketserver.TCPServer(("", PORT), MyHttpRequestHandler) as httpd:
        print(f"サーバーを起動しました: http://localhost:{PORT}/main.html")
        httpd.serve_forever()