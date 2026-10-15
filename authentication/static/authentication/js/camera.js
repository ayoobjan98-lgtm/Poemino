let stream = null;
let mediaRecorder = null;
let recordedChunks = [];
let videoBlob = null;
let timerInterval = null;

const startBtn = document.getElementById('start-camera');
const recordBtn = document.getElementById('record-btn');
const stopBtn = document.getElementById('stop-btn');
const preview = document.getElementById('preview');
const recordedPreview = document.getElementById('recorded-preview');
const recordedArea = document.getElementById('recorded-area');
const reRecordBtn = document.getElementById('re-record');
const fileInput = document.getElementById('video-file');
const submitBtn = document.getElementById('submit-btn');
const timerSpan = document.getElementById('timer');

startBtn.addEventListener('click', async () => {
    try {
        stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        preview.srcObject = stream;
        startBtn.disabled = true;
        recordBtn.disabled = false;
    } catch (err) {
        alert('Camera access denied.');
    }
});

recordBtn.addEventListener('click', () => {
    recordedChunks = [];
    mediaRecorder = new MediaRecorder(stream, { mimeType: 'video/webm' });
    mediaRecorder.ondataavailable = e => { if (e.data.size > 0) recordedChunks.push(e.data); };
    mediaRecorder.onstop = () => {
        videoBlob = new Blob(recordedChunks, { type: 'video/webm' });
        const url = URL.createObjectURL(videoBlob);
        recordedPreview.src = url;
        recordedArea.style.display = 'block';
        preview.style.display = 'none';
        recordBtn.style.display = 'none';
        stopBtn.style.display = 'none';
        submitBtn.disabled = false;
        const file = new File([videoBlob], 'verification.webm', { type: 'video/webm' });
        const dt = new DataTransfer();
        dt.items.add(file);
        fileInput.files = dt.files;
    };
    mediaRecorder.start();
    recordBtn.disabled = true;
    stopBtn.disabled = false;
    let sec = 0;
    timerSpan.textContent = '0s';
    timerInterval = setInterval(() => {
        sec++;
        timerSpan.textContent = sec + 's';
        if (sec >= 5) {
            clearInterval(timerInterval);
            mediaRecorder.stop();
            stopBtn.disabled = true;
        }
    }, 1000);
});

stopBtn.addEventListener('click', () => {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        clearInterval(timerInterval);
        mediaRecorder.stop();
        stopBtn.disabled = true;
    }
});

reRecordBtn.addEventListener('click', () => {
    videoBlob = null;
    recordedArea.style.display = 'none';
    preview.style.display = 'block';
    recordBtn.style.display = 'inline-block';
    stopBtn.style.display = 'inline-block';
    recordBtn.disabled = false;
    stopBtn.disabled = true;
    submitBtn.disabled = true;
    fileInput.value = '';
});