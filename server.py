import http.server
import socketserver
import json
import sqlite3
import os
from urllib.parse import urlparse, parse_qs, quote
import random
import urllib.request
import urllib.error
import uuid

PORT = 8000
# list.pyが書き込むデータベースファイルを指定
DB_PATH = 'SQL/playlist.db'

# --- OAuth設定 (ここに取得したIDとSecretを入力してください) ---
OAUTH_CONFIG = {
    'github': {
        'client_id': 'YOUR_GITHUB_CLIENT_ID',
        'client_secret': 'YOUR_GITHUB_CLIENT_SECRET',
        'redirect_uri': 'http://localhost:8000/callback/github'
    },
    'google': {
        'client_id': 'YOUR_GOOGLE_CLIENT_ID',
        'client_secret': 'YOUR_GOOGLE_CLIENT_SECRET',
        'redirect_uri': 'http://localhost:8000/callback/google'
    }
}

# データベースの初期化（テーブル作成）
def init_db():
    # データベースディレクトリが存在しない場合は作成
    db_dir = os.path.dirname(DB_PATH)
    if db_dir: os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # プレイリスト一覧を管理するテーブル
    cursor.execute('CREATE TABLE IF NOT EXISTS playlists (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, number TEXT)')
    try:
        cursor.execute('ALTER TABLE playlists ADD COLUMN number TEXT')
    except sqlite3.OperationalError:
        pass
    # プレイリスト内の曲を管理するテーブル
    cursor.execute('CREATE TABLE IF NOT EXISTS playlist_songs (playlist_id INTEGER, filename TEXT)')
    # ユーザー管理テーブル
    cursor.execute('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, provider TEXT, provider_user_id TEXT, name TEXT)')
    # セッション管理テーブル
    cursor.execute('CREATE TABLE IF NOT EXISTS sessions (session_id TEXT PRIMARY KEY, user_id INTEGER)')
    # numbersテーブル (アップロード時の乱数保存用)
    cursor.execute('CREATE TABLE IF NOT EXISTS numbers (id INTEGER PRIMARY KEY AUTOINCREMENT, filename TEXT, integer_val INTEGER)')
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
        elif path == '/api/get_playlist_number':
            self.handle_api_get_playlist_number(parsed_url.query)
        elif path == '/api/get_number':
            self.handle_api_get_number(parsed_url.query)
        elif path == '/api/get_playlists':
            self.handle_api_get_playlists()
        elif path == '/api/get_playlist_songs':
            self.handle_api_get_playlist_songs(parsed_url.query)
        elif path == '/api/auth/github':
            self.auth_redirect_github()
        elif path == '/callback/github':
            self.auth_callback_github(parsed_url.query)
        elif path == '/api/auth/google':
            self.auth_redirect_google()
        elif path == '/callback/google':
            self.auth_callback_google(parsed_url.query)
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
        # ファイルサイズ制限 (50MB)
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > 50 * 1024 * 1024:
            self.send_response(303)
            self.send_header('Location', '/playlist/test_playLiSt.html?error=FileTooLarge')
            self.end_headers()
            return

        import cgi
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={'REQUEST_METHOD': 'POST',
                     'CONTENT_TYPE': self.headers['Content-Type'],
                     }
        )
        
        if 'file' not in form:
            self.send_error(400, "No file uploaded")
            return
            
        fileitems = form['file']
        # multiple属性で複数ファイルが送られた場合はリストになるので統一
        if not isinstance(fileitems, list):
            fileitems = [fileitems]

        last_filename = None
        os.makedirs('music', exist_ok=True)
        
        for fileitem in fileitems:
            if fileitem.filename:
                # ファイル名を安全に取得 (パスを除去)
                filename = os.path.basename(fileitem.filename)
                
                # mp3ファイルのみを許可する
                if not filename.lower().endswith('.mp3'):
                    print(f"[Upload] Skipped non-mp3 file: {filename}")
                    continue

                save_path = os.path.join('music', filename)
                
                # ファイルを保存
                with open(save_path, 'wb') as f:
                    f.write(fileitem.file.read())

                # データベースに登録
                self.register_to_db(filename)
                last_filename = filename
                print(f"[Upload] Saved: {filename}")

        if last_filename:
            self.send_response(303)
            # 最後にアップロードされた曲のプレイヤー画面へリダイレクト
            self.send_header('Location', f'/playlist/test_playLiSt.html?file={quote(last_filename)}')
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
            playlist_num = f"{random.randint(0, 99999999):08d}"
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('INSERT INTO playlists (name, number) VALUES (?, ?)', (name, playlist_num))
            conn.commit()
            new_id = cursor.lastrowid
            conn.close()
            self.send_json_response({'status': 'success', 'id': new_id, 'name': name, 'number': playlist_num})
        else:
            self.send_error(400, "Missing name")

    def handle_api_get_playlist_number(self, query):
        """プレイリストIDに紐づいた8桁の数値を取得"""
        query_components = parse_qs(query)
        playlist_id = query_components.get("id", [None])[0]
        if playlist_id:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('SELECT number FROM playlists WHERE id = ?', (playlist_id,))
            row = cursor.fetchone()
            conn.close()
            if row and row[0]:
                self.send_json_response({'number': row[0]})
            else:
                self.send_error(404, "Playlist or number not found")
        else:
            self.send_error(400, "Missing playlist id")

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

    # --- OAuth Logic ---

    def auth_redirect_github(self):
        """GitHubのログイン画面へリダイレクト"""
        client_id = OAUTH_CONFIG['github']['client_id']
        url = f"https://github.com/login/oauth/authorize?client_id={client_id}&scope=read:user"
        self.send_response(302)
        self.send_header('Location', url)
        self.end_headers()

    def auth_callback_github(self, query):
        """GitHubからのコールバック処理"""
        query_components = parse_qs(query)
        code = query_components.get("code", [None])[0]
        if not code:
            self.send_error(400, "Auth code missing")
            return

        # アクセストークンの取得
        data = urllib.parse.urlencode({
            'client_id': OAUTH_CONFIG['github']['client_id'],
            'client_secret': OAUTH_CONFIG['github']['client_secret'],
            'code': code
        }).encode()
        
        req = urllib.request.Request("https://github.com/login/oauth/access_token", data=data, headers={'Accept': 'application/json'})
        try:
            with urllib.request.urlopen(req) as res:
                token_data = json.loads(res.read())
                access_token = token_data.get('access_token')
            
            if not access_token:
                raise Exception("Failed to get access token")

            # ユーザー情報の取得
            req_user = urllib.request.Request("https://api.github.com/user", headers={
                'Authorization': f'token {access_token}',
                'Accept': 'application/json'
            })
            with urllib.request.urlopen(req_user) as res_user:
                user_info = json.loads(res_user.read())
                
            self.create_session_and_redirect( 'github', str(user_info['id']), user_info.get('login', 'Unknown'))

        except Exception as e:
            self.send_error(500, f"GitHub Auth Error: {e}")

    def auth_redirect_google(self):
        """Googleのログイン画面へリダイレクト"""
        params = {
            'client_id': OAUTH_CONFIG['google']['client_id'],
            'redirect_uri': OAUTH_CONFIG['google']['redirect_uri'],
            'response_type': 'code',
            'scope': 'https://www.googleapis.com/auth/userinfo.profile',
            'access_type': 'offline'
        }
        url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
        self.send_response(302)
        self.send_header('Location', url)
        self.end_headers()

    def auth_callback_google(self, query):
        """Googleからのコールバック処理"""
        query_components = parse_qs(query)
        code = query_components.get("code", [None])[0]
        if not code:
            self.send_error(400, "Auth code missing")
            return

        # アクセストークンの取得
        data = urllib.parse.urlencode({
            'client_id': OAUTH_CONFIG['google']['client_id'],
            'client_secret': OAUTH_CONFIG['google']['client_secret'],
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': OAUTH_CONFIG['google']['redirect_uri']
        }).encode()

        try:
            req = urllib.request.Request("https://oauth2.googleapis.com/token", data=data, headers={'Content-Type': 'application/x-www-form-urlencoded'})
            with urllib.request.urlopen(req) as res:
                token_data = json.loads(res.read())
                access_token = token_data.get('access_token')

            # ユーザー情報の取得
            req_user = urllib.request.Request("https://www.googleapis.com/oauth2/v1/userinfo", headers={
                'Authorization': f'Bearer {access_token}'
            })
            with urllib.request.urlopen(req_user) as res_user:
                user_info = json.loads(res_user.read())

            self.create_session_and_redirect('google', user_info['id'], user_info.get('name', 'Unknown'))

        except Exception as e:
            self.send_error(500, f"Google Auth Error: {e}")

    def create_session_and_redirect(self, provider, provider_user_id, name):
        """ユーザーを保存/検索し、セッションを作成してメイン画面へ"""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # ユーザーが存在するか確認
        cursor.execute('SELECT id FROM users WHERE provider = ? AND provider_user_id = ?', (provider, provider_user_id))
        row = cursor.fetchone()

        if row:
            user_id = row[0]
        else:
            # 新規ユーザー登録
            cursor.execute('INSERT INTO users (provider, provider_user_id, name) VALUES (?, ?, ?)', (provider, provider_user_id, name))
            user_id = cursor.lastrowid
            conn.commit()

        # セッションID生成
        session_id = str(uuid.uuid4())
        cursor.execute('INSERT INTO sessions (session_id, user_id) VALUES (?, ?)', (session_id, user_id))
        conn.commit()
        conn.close()

        # クッキーをセットしてリダイレクト
        self.send_response(303)
        self.send_header('Location', '/main.html')
        self.send_header('Set-Cookie', f'session_id={session_id}; Path=/; HttpOnly')
        self.end_headers()

if __name__ == '__main__':
    init_db() # 起動時にテーブル作成
    with socketserver.TCPServer(("", PORT), MyHttpRequestHandler) as httpd:
        print(f"サーバーを起動しました: http://localhost:{PORT}/login.html")
        httpd.serve_forever()