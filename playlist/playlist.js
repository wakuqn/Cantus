const audio = document.getElementById('myAudio');
const playBtn = document.getElementById('playBtn');
const seekBar = document.getElementById('seekBar');
const currentTimeText = document.getElementById('currentTime');
const durationText = document.getElementById('duration');

let currentQueue = [];
let currentIndex = -1;

// ページの読み込み時にURLからファイル名を取得して設定する
window.addEventListener('DOMContentLoaded', () => {
    const urlParams = new URLSearchParams(window.location.search);
    const filename = urlParams.get('file');
    const error = urlParams.get('error');
    const playlistName = urlParams.get('playlist_name');
    const playlistId = urlParams.get('playlist_id');

    if (error === 'FileTooLarge') {
        alert("ファイルサイズが大きすぎます。10MB以下のファイルを選択してください。");
    }

    if (playlistId) {
        const queueTitle = document.getElementById('queueTitle');
        if (queueTitle) queueTitle.textContent = playlistName ? decodeURIComponent(playlistName) : "Playlist";
        loadPlaylistSongs(playlistId, filename);
    } else {
        // デフォルトは全曲をキューとして読み込む
        const queueTitle = document.getElementById('queueTitle');
        if (queueTitle) queueTitle.textContent = "Queue (All Songs)";
        loadAllSongsAsQueue(filename);
    }
});

// 全曲を読み込んでキューに設定
function loadAllSongsAsQueue(targetFilename) {
    fetch('/api/playlists')
        .then(res => res.json())
        .then(songs => {
            setupQueue(songs, targetFilename);
        });
}

// プレイリストの曲一覧を読み込んで表示
function loadPlaylistSongs(id, targetFilename) {
    fetch(`/api/get_playlist_songs?id=${id}`)
        .then(res => res.json())
        .then(songs => {
            setupQueue(songs, targetFilename);
        });
}

function setupQueue(songs, targetFilename) {
    currentQueue = songs;
    const container = document.getElementById('playlistContainer');
    const list = document.getElementById('playlistSongs');
    if (container) container.style.display = 'block';
    list.innerHTML = '';

    songs.forEach((song, index) => {
        const li = document.createElement('li');
        li.textContent = song;
        li.style.padding = '10px';
        li.style.borderBottom = '1px solid rgba(255,255,255,0.05)';
        li.style.cursor = 'pointer';
        li.id = 'queue-item-' + index;

        li.onmouseover = () => { if (currentIndex !== index) li.style.backgroundColor = 'rgba(255,255,255,0.1)'; };
        li.onmouseout = () => { if (currentIndex !== index) li.style.backgroundColor = 'transparent'; };

        li.onclick = () => {
            currentIndex = index;
            playTrack(song);
        };
        list.appendChild(li);
    });

    if (songs.length > 0) {
        // 指定されたファイルがあればそれを、なければ最初から
        let startIndex = 0;
        if (targetFilename) {
            const found = songs.findIndex(s => s === targetFilename);
            if (found !== -1) startIndex = found;
        }
        currentIndex = startIndex;
        // file指定されていれば自動再生、されていなければ停止状態でセット
        playTrack(songs[startIndex], !!targetFilename);
    } else if (targetFilename) {
        // キューには無いが直接ファイルが指定された場合
        playTrack(targetFilename, true);
    }
}

// 再生・一時停止の切り替え
function togglePlay() {
    if (audio.paused) {
        audio.play();
        playBtn.textContent = '⏸';
    } else {
        audio.pause();
        playBtn.textContent = '▶';
    }
}

// 停止（最初に戻る）
function stopAudio() {
    audio.pause();
    audio.currentTime = 0;
    playBtn.textContent = '▶';
}

// 指定した曲を再生する関数
function playTrack(filename, autoPlay = true) {
    const playerTitle = document.getElementById('playerTitle');
    playerTitle.textContent = decodeURIComponent(filename);

    audio.src = `/music/${encodeURIComponent(filename)}`;
    audio.load();

    if (autoPlay) {
        audio.play().catch(e => console.log("Playback prevented:", e));
        playBtn.textContent = '⏸';
    }

    // キューのハイライト更新
    const listItems = document.getElementById('playlistSongs').querySelectorAll('li');
    listItems.forEach((li, idx) => {
        if (idx === currentIndex) {
            li.style.backgroundColor = 'rgba(30, 215, 96, 0.2)';
            li.style.color = '#1ed760';
            li.style.fontWeight = 'bold';
        } else {
            li.style.backgroundColor = 'transparent';
            li.style.color = 'inherit';
            li.style.fontWeight = 'normal';
        }
    });
}

// 曲が終わったら自動的に次を再生
audio.addEventListener('ended', () => {
    if (currentIndex >= 0 && currentIndex < currentQueue.length - 1) {
        currentIndex++;
        playTrack(currentQueue[currentIndex], true);
    } else {
        stopAudio();
    }
});

// 次の曲へ
function nextTrack() {
    if (currentIndex >= 0 && currentIndex < currentQueue.length - 1) {
        currentIndex++;
        playTrack(currentQueue[currentIndex], true);
    } else if (currentQueue.length > 0) {
        currentIndex = 0;
        playTrack(currentQueue[currentIndex], true);
    }
}

// 前の曲へ
function prevTrack() {
    if (currentIndex > 0) {
        currentIndex--;
        playTrack(currentQueue[currentIndex], true);
    } else if (currentQueue.length > 0) {
        currentIndex = currentQueue.length - 1;
        playTrack(currentQueue[currentIndex], true);
    }
}

// スキップ機能
function skip(time) {
    audio.currentTime += time;
}

// 再生時間の更新に合わせてバーと数字を動かす
audio.addEventListener('timeupdate', () => {
    const current = Math.floor(audio.currentTime);
    seekBar.value = current;
    currentTimeText.textContent = formatTime(current);
});

// メタデータ読み込み完了時にバーの最大値を設定
audio.addEventListener('loadedmetadata', () => {
    seekBar.max = Math.floor(audio.duration);
    durationText.textContent = formatTime(audio.duration);
});

// シークバーを動かした時に再生位置を変える
seekBar.addEventListener('input', () => {
    audio.currentTime = seekBar.value;
});

// 時間の表示形式を整える (例: 75秒 -> 1:15)
function formatTime(seconds) {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return m + ":" + (s < 10 ? "0" + s : s);
}
