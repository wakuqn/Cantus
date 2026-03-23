function showPlaylistID() {
    const urlParams = new URLSearchParams(window.location.search);
    const playlistId = urlParams.get('playlist_id');

    if (!playlistId) {
        document.getElementById('playlistID').textContent = 'プレイリストが選択されていません';
        return;
    }

    fetch(`/api/get_playlist_number?id=${playlistId}`)
        .then(res => {
            if (!res.ok) throw new Error('エラーが発生しました');
            return res.json();
        })
        .then(data => {
            if(data.number) {
                document.getElementById('playlistID').textContent = 'Playlist Number: ' + data.number;
            } else {
                document.getElementById('playlistID').textContent = '数値が設定されていません';
            }
        })
        .catch(err => {
            console.error(err);
            document.getElementById('playlistID').textContent = '取得に失敗しました';
        });
}
