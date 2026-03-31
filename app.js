const state = {
    indexData: null,
    currentCourse: null,
    currentSubject: null,
    currentImages: [],
    currentFiles: [],
    currentIndex: 0,
    isQuizMode: false,
    quizScore: 0,
    quizAnswered: false,
    quizAnswered: false,
    isShuffled: false,
    currentZoom: 1,
    currentPath: null
};

const DOMElements = {
    subjectSelect: document.getElementById('select-subject'),
    threadSelect: document.getElementById('select-thread'),
    btnLoad: document.getElementById('btn-load'),
    btnPrev: document.getElementById('btn-prev'),
    btnNext: document.getElementById('btn-next'),
    btnShuffle: document.getElementById('btn-shuffle'),
    questionImage: document.getElementById('question-image'),
    questionCounter: document.getElementById('question-counter'),
    reviewPanel: document.getElementById('review-panel'),
    quizPanel: document.getElementById('quiz-panel'),
    commentsList: document.getElementById('comments-list'),
    optionsContainer: document.querySelector('.options'),
    quizFeedback: document.getElementById('quiz-feedback'),
    btnModeReview: document.getElementById('btn-review-mode'),
    btnModeQuiz: document.getElementById('btn-quiz-mode'),
    modeSelector: document.getElementById('mode-selector'),
    navBar: document.getElementById('nav-bar'),
    mainContent: document.getElementById('main-content'),
    imageWrapper: document.getElementById('image-wrapper'),
    zoomIn: document.getElementById('zoom-in'),
    zoomOut: document.getElementById('zoom-out'),
    zoomReset: document.getElementById('zoom-reset'),
    zoomLevel: document.getElementById('zoom-level'),
    btnAskGemini: document.getElementById('btn-ask-gemini'),
    btnGeminiSettings: document.getElementById('btn-gemini-settings'),
    btnSaveGemini: document.getElementById('btn-save-gemini'),
    geminiSetup: document.getElementById('gemini-setup'),
    geminiApiKey: document.getElementById('gemini-api-key'),
    geminiModel: document.getElementById('gemini-model'),
    geminiResponse: document.getElementById('gemini-response'),
    filesManager: document.getElementById('files-manager'),
    filesList: document.getElementById('files-list')
};

async function initApp() {
    try {
        const response = await fetch('./images/index.json?t=' + new Date().getTime());
        state.indexData = await response.json();
        populateSubjectSelect();
        setupEventListeners();
    } catch (error) {
        console.error('Error loading index.json:', error);
        alert('Lỗi khởi tạo: ' + error.message);
    }
}

function populateSubjectSelect() {
    DOMElements.subjectSelect.innerHTML = '<option value="">-- Chọn Môn --</option>';
    for (const subject of Object.keys(state.indexData)) {
        const option = document.createElement('option');
        option.value = subject;
        option.textContent = subject.toUpperCase();
        DOMElements.subjectSelect.appendChild(option);
    }
}

function populateThreadSelect(subject) {
    DOMElements.threadSelect.innerHTML = '<option value="">-- Chọn Đề --</option>';
    if (!subject) {
        DOMElements.threadSelect.disabled = true;
        return;
    }
    
    DOMElements.threadSelect.disabled = false;
    const threads = state.indexData[subject];
    for (const [thread, data] of Object.entries(threads)) {
        const option = document.createElement('option');
        option.value = JSON.stringify({subject, thread, path: data.path});
        option.textContent = data.title;
        DOMElements.threadSelect.appendChild(option);
    }
}

function setupEventListeners() {
    DOMElements.subjectSelect.addEventListener('change', (e) => {
        populateThreadSelect(e.target.value);
    });

    DOMElements.btnLoad.addEventListener('click', loadSelectedCourse);
    DOMElements.btnPrev.addEventListener('click', () => navigate(-1));
    DOMElements.btnNext.addEventListener('click', () => navigate(1));
    DOMElements.btnShuffle.addEventListener('click', toggleShuffle);
    
    DOMElements.btnModeReview.addEventListener('click', () => setMode(false));
    DOMElements.btnModeQuiz.addEventListener('click', () => setMode(true));

    document.addEventListener('keydown', handleKeyboardShortcuts);
    
    // Bind Quiz Buttons
    const quizBtns = document.querySelectorAll('.opt-btn');
    quizBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const val = e.target.getAttribute('data-val');
            const item = state.currentImages[state.currentIndex];
            handleQuizAnswer(val, item);
        });
    });

    // Zoom Controls
    DOMElements.zoomIn.addEventListener('click', () => handleZoom(0.2));
    DOMElements.zoomOut.addEventListener('click', () => handleZoom(-0.2));
    DOMElements.zoomReset.addEventListener('click', () => {
        state.currentZoom = 1;
        applyZoom();
    });

    DOMElements.imageWrapper.addEventListener('wheel', (e) => {
        if (e.ctrlKey) {
            e.preventDefault();
            if (e.deltaY < 0) {
                handleZoom(0.1);
            } else {
                handleZoom(-0.1);
            }
        }
    });

    // Gemini Setup
    DOMElements.btnAskGemini.addEventListener('click', handleGeminiClick);
    DOMElements.btnGeminiSettings.addEventListener('click', () => {
        DOMElements.geminiSetup.classList.toggle('hidden');
    });
    
    DOMElements.btnSaveGemini.addEventListener('click', () => {
        const apiKey = DOMElements.geminiApiKey.value.trim();
        const model = DOMElements.geminiModel.value;
        if (apiKey) {
            localStorage.setItem('gemini_api_key', apiKey);
            localStorage.setItem('gemini_model', model);
            DOMElements.geminiSetup.classList.add('hidden');
            handleGeminiRequest(apiKey, model);
        } else {
            alert("Vui lòng nhập API Key!");
        }
    });
    
    // Load saved Gemini Settings
    if (localStorage.getItem('gemini_api_key')) {
        DOMElements.geminiApiKey.value = localStorage.getItem('gemini_api_key');
    }
    if (localStorage.getItem('gemini_model')) {
        DOMElements.geminiModel.value = localStorage.getItem('gemini_model');
    }
}

function toggleShuffle() {
    state.isShuffled = !state.isShuffled;
    if (state.isShuffled) {
        DOMElements.btnShuffle.style.backgroundColor = '#f39c12';
        DOMElements.btnShuffle.style.color = 'white';
        // Simple shuffle algorithm (Fisher-Yates)
        for (let i = state.currentImages.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [state.currentImages[i], state.currentImages[j]] = [state.currentImages[j], state.currentImages[i]];
        }
    } else {
        DOMElements.btnShuffle.style.backgroundColor = '';
        DOMElements.btnShuffle.style.color = '';
        // Sort back by filename number normally
        state.currentImages.sort((a, b) => {
            const numA = parseInt(a.image.match(/\d+/)[0] || 0);
            const numB = parseInt(b.image.match(/\d+/)[0] || 0);
            return numA - numB;
        });
    }
    state.currentIndex = 0;
    renderCurrentItem();
}

async function loadSelectedCourse() {
    const selected = DOMElements.threadSelect.value;
    if (!selected) {
        alert('Vui lòng chọn một đề!');
        return;
    }

    const { subject, thread, path } = JSON.parse(selected);
    state.currentCourse = thread;
    state.currentSubject = subject;
    state.currentPath = path;
    
    try {
        const response = await fetch(`./${path}/data.json?t=` + new Date().getTime());
        state.currentImages = await response.json();
        
        try {
            const filesResponse = await fetch(`./${path}/files.json?t=` + new Date().getTime());
            if (filesResponse.ok) {
                state.currentFiles = await filesResponse.json();
            } else {
                state.currentFiles = [];
            }
        } catch (e) {
            state.currentFiles = [];
        }

        state.currentIndex = 0;
        state.quizScore = 0;
        state.isShuffled = false;
        state.currentZoom = 1;
        applyZoom();
        DOMElements.btnShuffle.style.backgroundColor = '';
        DOMElements.btnShuffle.style.color = '';
        
        // Show UI elements
        if (state.currentImages && state.currentImages.length > 0) {
            DOMElements.modeSelector.classList.remove('hidden');
            DOMElements.navBar.classList.remove('hidden');
            DOMElements.mainContent.classList.remove('hidden');
        } else {
            // No images to show
            DOMElements.modeSelector.classList.add('hidden');
            DOMElements.navBar.classList.add('hidden');
            DOMElements.mainContent.classList.add('hidden');
            DOMElements.questionImage.src = '';
            DOMElements.questionImage.alt = 'Chưa có hình ảnh câu hỏi cho đề này.';
        }
        
        if (state.currentFiles && state.currentFiles.length > 0) {
            DOMElements.filesManager.classList.remove('hidden');
            DOMElements.filesList.innerHTML = '';
            state.currentFiles.forEach(file => {
                const li = document.createElement('li');
                const a = document.createElement('a');
                a.href = `./${path}/${file.url}`;
                a.target = '_blank';
                a.textContent = file.name;
                a.style.color = '#3498db';
                a.style.textDecoration = 'none';
                a.style.fontWeight = 'bold';
                li.appendChild(a);
                DOMElements.filesList.appendChild(li);
            });
        } else {
            DOMElements.filesManager.classList.add('hidden');
        }
        
        setMode(false); // Default to Review mode
    } catch (error) {
        console.error('Error loading data.json:', error);
        alert('Could not load course data.');
    }
}

function setMode(isQuiz) {
    state.isQuizMode = isQuiz;
    state.quizScore = 0;
    
    if (isQuiz) {
        DOMElements.btnModeQuiz.classList.add('active');
        DOMElements.btnModeReview.classList.remove('active');
        DOMElements.quizPanel.classList.remove('hidden');
        DOMElements.reviewPanel.classList.add('hidden');
    } else {
        DOMElements.btnModeReview.classList.add('active');
        DOMElements.btnModeQuiz.classList.remove('active');
        DOMElements.reviewPanel.classList.remove('hidden');
        DOMElements.quizPanel.classList.add('hidden');
    }
    
    if (state.currentImages.length > 0) {
        renderCurrentItem();
    }
}

function renderCurrentItem() {
    if (!state.currentImages || state.currentImages.length === 0) return;

    // Lưu lại vị trí cuộn hiện tại để tái lập khi ảnh mới nạp xong
    const prevScrollTop = DOMElements.imageWrapper.scrollTop;
    const prevScrollLeft = DOMElements.imageWrapper.scrollLeft;

    const item = state.currentImages[state.currentIndex];
    
    DOMElements.questionImage.onload = () => {
        DOMElements.imageWrapper.scrollTop = prevScrollTop;
        DOMElements.imageWrapper.scrollLeft = prevScrollLeft;
        DOMElements.questionImage.onload = null; // Xóa sự kiện sau khi dùng
    };

    DOMElements.questionImage.src = `./images/${state.currentSubject}/${state.currentCourse}/${item.image}`;
    
    DOMElements.questionCounter.textContent = `Câu hỏi: ${state.currentIndex + 1} / ${state.currentImages.length}`;

    if (state.isQuizMode) {
        renderQuizMode(item);
    } else {
        renderReviewMode(item);
    }
}

function renderReviewMode(item) {
    DOMElements.commentsList.innerHTML = '';
    DOMElements.geminiSetup.classList.add('hidden');
    DOMElements.geminiResponse.classList.add('hidden');
    DOMElements.geminiResponse.innerHTML = '';
    
    // Nếu có đáp án Gemini đã lưu từ trước
    if (item.gemini_answer) {
        DOMElements.geminiResponse.classList.remove('hidden');
        DOMElements.geminiResponse.innerHTML = `<strong>🤖 Giải thích từ Gemini:</strong><br><br>${markedUp(item.gemini_answer)}`;
    }
    
    // Add Best Answer to top if exists
    if (item.best_answer) {
        const bestDiv = document.createElement('div');
        bestDiv.className = 'comment-item';
        bestDiv.style.backgroundColor = '#ecfdf5';
        bestDiv.style.borderLeft = '4px solid #2ecc71';
        bestDiv.style.padding = '10px';
        bestDiv.style.fontWeight = 'bold';
        bestDiv.innerHTML = `<div>🌟 ĐÁP ÁN ĐÚNG: ${item.best_answer}</div>`;
        DOMElements.commentsList.appendChild(bestDiv);
    }

    item.comments.forEach(commentObj => {
        const div = document.createElement('div');
        div.className = 'comment-item';
        div.innerHTML = `
            <div>${(commentObj.text || '').replace(/\n/g, '<br>')}</div>
            <div class="comment-count">Tần suất: ${commentObj.count} người đồng tình</div>
        `;
        DOMElements.commentsList.appendChild(div);
    });
    
    if(item.comments.length === 0){
        DOMElements.commentsList.innerHTML = '<i>Không có dữ liệu cho câu hỏi này.</i>';
    }
}

function renderQuizMode(item) {
    state.quizAnswered = false;
    DOMElements.quizFeedback.classList.add('hidden');
    DOMElements.quizFeedback.textContent = '';
    DOMElements.quizFeedback.className = 'hidden';
    
    DOMElements.geminiSetup.classList.add('hidden');
    DOMElements.geminiResponse.classList.add('hidden');

    const buttons = DOMElements.optionsContainer.querySelectorAll('.opt-btn');
    buttons.forEach(btn => {
        btn.classList.remove('correct', 'wrong');
    });
}

function handleQuizAnswer(selectedOption, item) {
    if (state.quizAnswered) return;
    state.quizAnswered = true;

    const correctAnswer = item.best_answer || '';
    const isCorrect = correctAnswer.includes(selectedOption);

    const buttons = DOMElements.optionsContainer.querySelectorAll('.opt-btn');
    buttons.forEach(btn => {
        const val = btn.getAttribute('data-val');
        if (correctAnswer.includes(val)) {
            btn.classList.add('correct');
        }
        if (val === selectedOption && !isCorrect) {
            btn.classList.add('wrong');
        }
    });

    DOMElements.quizFeedback.classList.remove('hidden');
    if (isCorrect) {
        state.quizScore++;
        DOMElements.quizFeedback.textContent = 'Chính xác! 🎉';
        DOMElements.quizFeedback.style.color = '#27ae60';
        setTimeout(() => navigate(1), 1200);
    } else {
        DOMElements.quizFeedback.textContent = `Sai rồi. Đáp án đúng có chứa: ${correctAnswer || 'Không rõ, hãy xem Review'}`;
        DOMElements.quizFeedback.style.color = '#c0392b';
    }
}

function navigate(direction) {
    if (!state.currentImages.length) return;
    
    let newIndex = state.currentIndex + direction;
    if (newIndex < 0) newIndex = state.currentImages.length - 1;
    if (newIndex >= state.currentImages.length) newIndex = 0;
    
    state.currentIndex = newIndex;
    renderCurrentItem();
}

function handleKeyboardShortcuts(e) {
    if (!state.currentImages.length) return;

    if (e.key === 'ArrowLeft') {
        navigate(-1);
    } else if (e.key === 'ArrowRight') {
        navigate(1);
    }

    if (state.isQuizMode && !state.quizAnswered) {
        const key = e.key.toUpperCase();
        if (['A', 'B', 'C', 'D', 'E', 'F'].includes(key)) {
            const item = state.currentImages[state.currentIndex];
            handleQuizAnswer(key, item);
        }
    }
}

document.addEventListener('DOMContentLoaded', initApp);

// Zoom Functions
function handleZoom(amount) {
    state.currentZoom += amount;
    if (state.currentZoom < 0.2) state.currentZoom = 0.2;
    if (state.currentZoom > 5) state.currentZoom = 5;
    applyZoom();
}

function applyZoom() {
    if (state.currentZoom === 1) {
        DOMElements.questionImage.style.width = '';
        DOMElements.questionImage.style.height = '';
        DOMElements.questionImage.style.maxWidth = '100%';
        DOMElements.questionImage.style.maxHeight = '100%';
        DOMElements.questionImage.style.objectFit = 'contain';
        DOMElements.imageWrapper.style.alignItems = 'center';
        DOMElements.imageWrapper.style.justifyContent = 'center';
    } else {
        DOMElements.questionImage.style.width = `${state.currentZoom * 100}%`;
        DOMElements.questionImage.style.height = 'auto'; 
        DOMElements.questionImage.style.maxWidth = 'none';
        DOMElements.questionImage.style.maxHeight = 'none';
        DOMElements.questionImage.style.objectFit = 'fill'; 
        DOMElements.imageWrapper.style.alignItems = 'flex-start';
        DOMElements.imageWrapper.style.justifyContent = 'flex-start';
    }
    if (DOMElements.zoomLevel) {
        DOMElements.zoomLevel.textContent = Math.round(state.currentZoom * 100) + '%';
    }
}

// Gemini Functions
function markedUp(text) {
    return text.replace(/\n/g, '<br>')
               .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
               .replace(/\*(.*?)\*/g, '<em>$1</em>')
               .replace(/`(.*?)`/g, '<code style="background-color:#eee;padding:2px 4px;border-radius:3px;">$1</code>');
}

function handleGeminiClick() {
    const apiKey = localStorage.getItem('gemini_api_key');
    const model = localStorage.getItem('gemini_model') || 'gemini-2.0-flash';
    
    if (!apiKey) {
        DOMElements.geminiSetup.classList.remove('hidden');
        DOMElements.geminiResponse.classList.add('hidden');
    } else {
        handleGeminiRequest(apiKey, model);
    }
}

async function handleGeminiRequest(apiKey, model) {
    const item = state.currentImages[state.currentIndex];
    if (!item) return;

    // Nếu đã có đáp án thì không gọi lại
    if (item.gemini_answer) {
        return;
    }

    DOMElements.geminiResponse.classList.remove('hidden');
    DOMElements.geminiResponse.innerHTML = '<span style="color:#8e44ad; font-weight:bold;">🤖 Trợ lý đang xem ảnh và suy nghĩ (Có thể mất đến 10 giây)...</span>';
    DOMElements.btnAskGemini.disabled = true;

    try {
        const imagePath = `images/${state.currentSubject}/${state.currentCourse}/${item.image}`;
        const courseJsonPath = `${state.currentPath}/data.json`;
        
        const response = await fetch('/api/gemini', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                api_key: apiKey,
                model: model,
                image_path: imagePath,
                course_json_path: courseJsonPath,
                item_id: item.id
            })
        });

        const result = await response.json();
        
        if (response.ok && result.status === 'success') {
            item.gemini_answer = result.answer; // Cập nhật state cục bộ
            DOMElements.geminiResponse.innerHTML = `<strong>🤖 Giải thích từ Gemini:</strong><br><br>${markedUp(result.answer)}`;
        } else {
            throw new Error(result.message || 'Lỗi kết nối tới Server');
        }
    } catch (err) {
        DOMElements.geminiResponse.innerHTML = `<span style="color:#c0392b;"><strong>Lỗi:</strong> ${err.message}</span>`;
        if(err.message.includes('Thiếu API Key')) {
             DOMElements.geminiSetup.classList.remove('hidden');
        }
    } finally {
        DOMElements.btnAskGemini.disabled = false;
    }
}
