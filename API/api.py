from flask import Flask, request, jsonify
import os
import sqlite3
import random
import shutil

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ── パス設定 ──
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MUSIC_DIR = os.path.join(BASE_DIR, 'music')
DB_PATH = os.path.join(BASE_DIR, 'SQL', 'playlist.db')

ALLOWED_EXTENSIONS = {'mp3', 'flac', 'wav'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_db():
    """SQLite接続を取得するヘルパー"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """データベーステーブルの初期化"""
    db_dir = os.path.dirname(DB_PATH)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)
    os.makedirs(MUSIC_DIR, exist_ok=True)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'CREATE TABLE IF NOT EXISTS playlists '
        '(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, number TEXT)'
    )
    cursor.execute(
        'CREATE TABLE IF NOT EXISTS playlist_songs '
        '(playlist_id INTEGER, filename TEXT)'
    )
    cursor.execute(
        'CREATE TABLE IF NOT EXISTS numbers '
        '(id INTEGER PRIMARY KEY AUTOINCREMENT, filename TEXT, integer_val INTEGER)'
    )
    conn.commit()
    conn.close()


# ── CORS ──
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response


# ═══════════════════════════════════════
#  曲一覧
# ═══════════════════════════════════════
@app.route('/api/playlists', methods=['GET'])
def list_songs():
    """musicフォルダ内のオーディオファイル一覧を返す"""
    filenames = []
    if os.path.exists(MUSIC_DIR):
        filenames = sorted(
            f for f in os.listdir(MUSIC_DIR)
            if f.lower().endswith(('.mp3', '.flac', '.wav'))
        )

    # numbersテーブルに未登録のファイルを自動登録
    conn = get_db()
    cursor = conn.cursor()
    for filename in filenames:
        cursor.execute('SELECT id FROM numbers WHERE filename = ?', (filename,))
        if not cursor.fetchone():
            rand_num = random.randint(0, 99999999)
            cursor.execute(
                'INSERT INTO numbers (filename, integer_val) VALUES (?, ?)',
                (filename, rand_num)
            )
    conn.commit()
    conn.close()

    return jsonify(filenames)


# ═══════════════════════════════════════
#  曲のアップロード
# ═══════════════════════════════════════
@app.route('/api/upload', methods=['POST'])
def upload_song():
    """オーディオファイルをmusicフォルダにアップロード"""
    if 'file' not in request.files:
        return jsonify({"error": "ファイルが選択されていません"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "ファイル名が空です"}), 400

    if not allowed_file(file.filename):
        return jsonify({
            "error": f"許可されていないファイル形式です。対応形式: {', '.join(ALLOWED_EXTENSIONS)}"
        }), 400

    # musicフォルダに保存
    save_path = os.path.join(MUSIC_DIR, file.filename)
    file.save(save_path)

    # numbersテーブルに登録
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM numbers WHERE filename = ?', (file.filename,))
    if not cursor.fetchone():
        rand_num = random.randint(0, 99999999)
        cursor.execute(
            'INSERT INTO numbers (filename, integer_val) VALUES (?, ?)',
            (file.filename, rand_num)
        )
    conn.commit()
    conn.close()

    return jsonify({
        "status": "success",
        "filename": file.filename,
        "message": f"{file.filename} をアップロードしました"
    })


# ═══════════════════════════════════════
#  曲の削除
# ═══════════════════════════════════════
@app.route('/api/delete_song', methods=['POST'])
def delete_song():
    """musicフォルダからファイルを削除"""
    data = request.json
    if not data or 'filename' not in data:
        return jsonify({"error": "ファイル名が指定されていません"}), 400

    filename = data['filename']
    file_path = os.path.join(MUSIC_DIR, filename)

    if not os.path.exists(file_path):
        return jsonify({"error": "ファイルが見つかりません"}), 404

    os.remove(file_path)

    # DBからも削除
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM numbers WHERE filename = ?', (filename,))
    cursor.execute('DELETE FROM playlist_songs WHERE filename = ?', (filename,))
    conn.commit()
    conn.close()

    return jsonify({"status": "success", "message": f"{filename} を削除しました"})


# ═══════════════════════════════════════
#  プレイリスト管理
# ═══════════════════════════════════════
@app.route('/api/get_playlists', methods=['GET'])
def get_playlists():
    """プレイリスト一覧を返す"""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, number FROM playlists ORDER BY id')
    rows = cursor.fetchall()
    conn.close()

    playlists = [{'id': row['id'], 'name': row['name'], 'number': row['number']} for row in rows]
    return jsonify(playlists)


@app.route('/api/create_playlist', methods=['POST'])
def create_playlist():
    """新規プレイリストを作成"""
    data = request.json
    name = data.get('name') if data else None

    if not name:
        return jsonify({"error": "プレイリスト名が必要です"}), 400

    playlist_num = f"{random.randint(0, 99999999):08d}"

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO playlists (name, number) VALUES (?, ?)',
        (name, playlist_num)
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()

    return jsonify({
        "status": "success",
        "id": new_id,
        "name": name,
        "number": playlist_num
    })


@app.route('/api/delete_playlist', methods=['POST'])
def delete_playlist():
    """プレイリストを削除"""
    data = request.json
    playlist_id = data.get('playlist_id') if data else None

    if not playlist_id:
        return jsonify({"error": "プレイリストIDが必要です"}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM playlists WHERE id = ?', (playlist_id,))
    cursor.execute('DELETE FROM playlist_songs WHERE playlist_id = ?', (playlist_id,))
    conn.commit()
    conn.close()

    return jsonify({"status": "success", "message": "プレイリストを削除しました"})


# ═══════════════════════════════════════
#  プレイリスト内の曲管理
# ═══════════════════════════════════════
@app.route('/api/get_playlist_songs', methods=['GET'])
def get_playlist_songs():
    """プレイリスト内の曲一覧を返す"""
    playlist_id = request.args.get('id')
    if not playlist_id:
        return jsonify({"error": "プレイリストIDが必要です"}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'SELECT filename FROM playlist_songs WHERE playlist_id = ?',
        (playlist_id,)
    )
    rows = cursor.fetchall()
    conn.close()

    filenames = [row['filename'] for row in rows]
    return jsonify(filenames)


@app.route('/api/add_to_playlist', methods=['POST'])
def add_to_playlist():
    """プレイリストに曲を追加"""
    data = request.json
    playlist_id = data.get('playlist_id') if data else None
    filename = data.get('filename') if data else None

    if not playlist_id or not filename:
        return jsonify({"error": "playlist_id と filename が必要です"}), 400

    conn = get_db()
    cursor = conn.cursor()
    # 重複チェック
    cursor.execute(
        'SELECT rowid FROM playlist_songs WHERE playlist_id = ? AND filename = ?',
        (playlist_id, filename)
    )
    if cursor.fetchone():
        conn.close()
        return jsonify({"status": "already_exists", "message": "この曲は既に追加されています"})

    cursor.execute(
        'INSERT INTO playlist_songs (playlist_id, filename) VALUES (?, ?)',
        (playlist_id, filename)
    )
    conn.commit()
    conn.close()

    return jsonify({"status": "success", "message": f"{filename} をプレイリストに追加しました"})


@app.route('/api/remove_from_playlist', methods=['POST'])
def remove_from_playlist():
    """プレイリストから曲を削除"""
    data = request.json
    playlist_id = data.get('playlist_id') if data else None
    filename = data.get('filename') if data else None

    if not playlist_id or not filename:
        return jsonify({"error": "playlist_id と filename が必要です"}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'DELETE FROM playlist_songs WHERE playlist_id = ? AND filename = ?',
        (playlist_id, filename)
    )
    conn.commit()
    conn.close()

    return jsonify({"status": "success", "message": f"{filename} をプレイリストから削除しました"})


# ═══════════════════════════════════════
#  曲の数値取得
# ═══════════════════════════════════════
@app.route('/api/get_number', methods=['GET'])
def get_number():
    """ファイル名に紐付いた数値を返す"""
    filename = request.args.get('file')
    if not filename:
        return jsonify({"error": "file パラメータが必要です"}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT integer_val FROM numbers WHERE filename = ?', (filename,))
    row = cursor.fetchone()

    if row:
        number = row['integer_val']
    else:
        number = random.randint(0, 99999999)
        cursor.execute(
            'INSERT INTO numbers (filename, integer_val) VALUES (?, ?)',
            (filename, number)
        )
        conn.commit()

    conn.close()
    return jsonify({"number": number})


@app.route('/api/get_playlist_number', methods=['GET'])
def get_playlist_number():
    """プレイリストIDに紐づいた8桁の数値を返す"""
    playlist_id = request.args.get('id')
    if not playlist_id:
        return jsonify({"error": "id パラメータが必要です"}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT number FROM playlists WHERE id = ?', (playlist_id,))
    row = cursor.fetchone()
    conn.close()

    if row and row['number']:
        return jsonify({"number": row['number']})
    else:
        return jsonify({"error": "プレイリストが見つかりません"}), 404


# ═══════════════════════════════════════
#  ヘルスチェック
# ═══════════════════════════════════════
@app.route('/', methods=['GET'])
def index():
    return jsonify({
        "name": "Cantus API",
        "version": "1.0",
        "endpoints": [
            "GET  /api/playlists            - 全曲一覧",
            "POST /api/upload               - 曲のアップロード",
            "POST /api/delete_song          - 曲の削除",
            "GET  /api/get_playlists        - プレイリスト一覧",
            "POST /api/create_playlist      - プレイリスト作成",
            "POST /api/delete_playlist      - プレイリスト削除",
            "GET  /api/get_playlist_songs   - プレイリスト内の曲一覧",
            "POST /api/add_to_playlist      - プレイリストに曲追加",
            "POST /api/remove_from_playlist - プレイリストから曲削除",
            "GET  /api/get_number           - 曲の数値取得",
            "GET  /api/get_playlist_number  - プレイリストの数値取得",
        ]
    })


if __name__ == "__main__":
    init_db()
    print("Cantus API サーバーを起動中... http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)