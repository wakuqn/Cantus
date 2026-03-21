window.addEventListener('DOMContentLoaded', () => {
    const audioEl = document.getElementById('myAudio');
    const volumeBar = document.getElementById('volumeBar');
    const volumeText = document.getElementById('volumeText');

    if (audioEl && volumeBar) {
        // 初期ボリューム設定 (0.0 から 1.0)
        audioEl.volume = volumeBar.value;
        if (volumeText) volumeText.textContent = Math.round(volumeBar.value * 100) + '%';

        // ボリュームの変更を検知
        volumeBar.addEventListener('input', (e) => {
            const vol = e.target.value;
            audioEl.volume = vol;
            if (volumeText) volumeText.textContent = Math.round(vol * 100) + '%';
        });
    }
});
