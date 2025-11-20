// 全局变量
let characters = [];
let uiTranslations = {}; // Store translations

// 打字机效果函数
function typeWriterEffect(element, text, speed = 30) {
    let i = 0;
    element.innerHTML = '';
    function type() {
        if (i < text.length) {
            element.innerHTML += text.charAt(i);
            i++;
            setTimeout(type, speed);
        }
    }
    type();
}

// 角色模态框相关函数
function openCharacterModal(characterId) {
    const c = characters.find(x => x.id === characterId);
    if (!c) {
        console.error("Character not found:", characterId);
        return;
    }

    const noDetail = uiTranslations.no_detail || '暂无详细信息';
    const noEvents = uiTranslations.no_events || '暂无相关事件';
    const eventsTitle = uiTranslations.events_title || '✦ 相关事件 ✦';

    document.getElementById('modal-body').innerHTML = `
        <div style="text-align: center;">
            <h3 style="color: var(--secondary-color); font-size: 1.5rem; margin-bottom: 1rem;">✧ ${c.name} ✧</h3>
            <div style="width: 100px; height: 100px; margin: 0 auto 1rem; border: 4px solid var(--border-color); background: #ddd;">
                <img src="${c.avatar}" class="pixel-art" style="width: 100%; height: 100%; object-fit: cover;">
            </div>
            <p style="margin-bottom: 1rem; color: var(--text-color);">${c.detail || noDetail}</p>
            <h4 style="color: var(--primary-color); border-bottom: 2px dashed var(--primary-color); padding-bottom: 0.5rem; margin-bottom: 0.5rem;">${eventsTitle}</h4>
            <ul style="text-align: left; padding-left: 1.5rem; color: #666;">
                ${c.events && c.events.length ? c.events.map(e => `<li>${e}</li>`).join('') : `<li>${noEvents}</li>`}
            </ul>
        </div>
    `;
    document.getElementById('character-modal').style.display = 'flex';
}

function closeCharacterModal() {
    document.getElementById('character-modal').style.display = 'none';
}

// 菜单控制相关函数
function toggleGameMenu() {
    document.getElementById('game-menu-modal').style.display = 'flex';
}

function closeGameMenu() {
    document.getElementById('game-menu-modal').style.display = 'none';
}

// 历史记录模态框控制
function toggleHistory() {
    document.getElementById('history-modal').style.display = 'flex';
}

function closeHistoryModal() {
    document.getElementById('history-modal').style.display = 'none';
}

// ============ 存档/读档功能 ============

// 保存游戏到localStorage
function saveGameToLocalStorage(saveName) {
    fetch('/save')
        .then(res => res.json())
        .then(data => {
            if (!data.success) {
                alert(uiTranslations.save_error || '存档失败');
                return;
            }

            const saveData = {
                name: saveName,
                timestamp: new Date().toISOString(),
                data: data.data
            };

            // 获取现有存档
            const saves = JSON.parse(localStorage.getItem('aiAdventureSaves') || '{}');

            // 生成存档ID
            const saveId = `save_${Date.now()}`;
            saves[saveId] = saveData;

            // 保存到localStorage
            try {
                localStorage.setItem('aiAdventureSaves', JSON.stringify(saves));
                alert(uiTranslations.save_success || `存档成功: ${saveName}`);
                closeSaveDialog();
            } catch (e) {
                if (e.name === 'QuotaExceededError') {
                    alert(uiTranslations.storage_full || 'localStorage已满，请删除旧存档');
                } else {
                    alert(uiTranslations.save_error || '存档失败: ' + e.message);
                }
            }
        })
        .catch(err => {
            console.error('Save error:', err);
            alert(uiTranslations.save_error || '存档失败');
        });
}

// 从localStorage读档
function loadGameFromLocalStorage(saveId) {
    const saves = JSON.parse(localStorage.getItem('aiAdventureSaves') || '{}');
    const saveData = saves[saveId];

    if (!saveData) {
        alert(uiTranslations.load_error || '存档不存在');
        return;
    }

    // 确认读档（会覆盖当前进度）
    const confirmMsg = uiTranslations.load_confirm || '读档会覆盖当前进度，确定要读档吗？';
    if (!confirm(confirmMsg)) {
        return;
    }

    fetch('/load', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(saveData)
    })
        .then(res => res.json())
        .then(data => {
            if (data.success) {
                // 读档成功，刷新页面
                window.location.reload();
            } else {
                alert(uiTranslations.load_error || '读档失败');
            }
        })
        .catch(err => {
            console.error('Load error:', err);
            alert(uiTranslations.load_error || '读档失败');
        });
}

// 获取所有存档
function getSaveList() {
    const saves = JSON.parse(localStorage.getItem('aiAdventureSaves') || '{}');
    return Object.entries(saves).map(([id, save]) => ({
        id,
        name: save.name,
        timestamp: save.timestamp
    })).sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
}

// 删除存档
function deleteSave(saveId) {
    const confirmMsg = uiTranslations.delete_confirm || '确定要删除这个存档吗？';
    if (!confirm(confirmMsg)) {
        return;
    }

    const saves = JSON.parse(localStorage.getItem('aiAdventureSaves') || '{}');
    delete saves[saveId];
    localStorage.setItem('aiAdventureSaves', JSON.stringify(saves));

    // 刷新读档对话框
    showLoadDialog();
}

// 显示存档对话框
function showSaveDialog() {
    closeGameMenu();
    document.getElementById('save-dialog').style.display = 'flex';
}

// 关闭存档对话框
function closeSaveDialog() {
    document.getElementById('save-dialog').style.display = 'none';
}

// 执行存档
function doSave() {
    const saveNameInput = document.getElementById('save-name-input');
    const saveName = saveNameInput.value.trim() || `存档 ${new Date().toLocaleString()}`;
    saveGameToLocalStorage(saveName);
}

// 显示读档对话框
function showLoadDialog() {
    closeGameMenu();
    const saves = getSaveList();

    const saveListHtml = saves.length > 0
        ? saves.map(save => {
            const date = new Date(save.timestamp).toLocaleString();
            return `
                <div class="save-item">
                    <div class="save-info">
                        <div class="save-name">${save.name}</div>
                        <div class="save-date">${date}</div>
                    </div>
                    <div class="save-actions">
                        <button class="btn btn-small" onclick="loadGameFromLocalStorage('${save.id}')">
                            ${uiTranslations.load_btn || '读取'}
                        </button>
                        <button class="btn btn-small btn-danger" onclick="deleteSave('${save.id}')">
                            ${uiTranslations.delete_btn || '删除'}
                        </button>
                    </div>
                </div>
            `;
        }).join('')
        : `<div style="text-align: center; color: #999; padding: 2rem;">
            ${uiTranslations.no_saves || '暂无存档'}
        </div>`;

    document.getElementById('save-list').innerHTML = saveListHtml;
    document.getElementById('load-dialog').style.display = 'flex';
}

// 关闭读档对话框
function closeLoadDialog() {
    document.getElementById('load-dialog').style.display = 'none';
}


// 加载状态相关函数
function startLoading() {
    const loadingDots = document.getElementById('loading-dots');
    if (!loadingDots) return;

    loadingDots.style.display = 'block';
    let dotCount = 0;
    loadingDots.timer = setInterval(() => {
        dotCount = (dotCount + 1) % 4;
        document.getElementById('dots').textContent = '.'.repeat(dotCount);
    }, 500);
}

function stopLoading() {
    const loadingDots = document.getElementById('loading-dots');
    if (!loadingDots) return;

    clearInterval(loadingDots.timer);
    loadingDots.style.display = 'none';
}

// 动态省略号（通用）
function startLoadingDots(id) {
    const target = document.getElementById(id);
    if (!target) {
        console.error("Loading dots target not found:", id);
        return;
    }

    target.style.display = 'inline';
    let dotCount = 0;
    target.timer = setInterval(() => {
        dotCount = (dotCount + 1) % 4;
        target.innerText = '.'.repeat(dotCount);
    }, 500);
    console.log("Loading animation started for", id);
}

function stopLoadingDots(id) {
    const target = document.getElementById(id);
    if (!target) {
        console.error("Loading dots target not found:", id);
        return;
    }

    clearInterval(target.timer);
    target.style.display = 'none';
}

// 像素效果增强
function enhancePixelEffects() {
    // 为所有图片添加像素处理类
    const allImages = document.querySelectorAll('img');
    allImages.forEach(img => {
        img.classList.add('pixel-art');
    });
}

// 显示调试信息
function debugInfo(storyData, charactersData) {
    console.log('Story object:', storyData);
    console.log('Characters:', charactersData);
}

// 异步图片检查函数
function checkImage() {
    console.log("[Polling] Checking for image");

    document.getElementById("image-container").style.display = "flex";
    document.getElementById("image-loading").style.display = "flex"; // Changed to flex for centering
    startLoadingDots("image-dots");  // 图片 loading 省略号

    fetch('/get_image', {
        method: 'GET',
        headers: {
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        },
        credentials: 'same-origin'
    })
        .then(res => res.json())
        .then(data => {
            if (data.image) {
                const img = document.getElementById("story-image");
                img.src = data.image;
                img.onload = () => {
                    stopLoadingDots("image-dots");
                    document.getElementById("image-loading").style.display = "none";
                    img.style.display = 'block';
                    // 淡入效果
                    img.style.opacity = 0;
                    setTimeout(() => {
                        img.style.transition = "opacity 0.5s ease-in-out";
                        img.style.opacity = 1;
                    }, 50);
                };

                img.onerror = () => {
                    console.error("[Polling] Failed to load image URL:", data.image);
                    // document.getElementById("image-loading").textContent = "图片加载失败，重试中...";
                    setTimeout(checkImage, 3000);
                };
            } else {
                console.log("[Polling] No image yet, continuing to poll...");
                setTimeout(checkImage, 2000);
            }
        })
        .catch(error => {
            console.error("[Polling] Fetch error:", error);
            // document.getElementById("image-loading").textContent = "检查图片中...";
            setTimeout(checkImage, 3000);
        });
}

// 初始化函数 - 页面加载完成后调用
function initializeGame(charactersData, storyData, imagePending, translations) {
    try {
        // 解析角色数据
        if (typeof charactersData === 'string') {
            characters = JSON.parse(charactersData);
        } else {
            characters = charactersData || [];
        }

        // Store translations
        if (translations) {
            uiTranslations = translations;
        }

        // 增强像素效果
        enhancePixelEffects();

        // 输出调试信息
        debugInfo(storyData, characters);

        // 检查文本是否为空
        const storyText = document.querySelector('.story-text');
        if (storyText && (!storyText.textContent || storyText.textContent.trim() === '')) {
            storyText.textContent = '...';
        }

        // 如果需要，开始检查图片
        if (imagePending) {
            setTimeout(checkImage, 1000);
        } else {
            const imageContainer = document.getElementById("image-container");
            // Only hide if no image exists
            const img = document.getElementById("story-image");
            if (imageContainer && (!img.src || img.src === '' || img.style.display === 'none')) {
                // Keep it hidden if no image
                if (!storyData.image) imageContainer.style.display = "none";
            }
        }
    } catch (e) {
        console.error("初始化游戏出错:", e);
    }
}

// 页面加载时仅对新文本应用打字机效果
document.addEventListener('DOMContentLoaded', function () {
    console.log("DOM loaded, enhancing interface");

    // 查找故事文本元素并应用打字机效果（如果存在）
    const storyTextElement = document.querySelector('.story-text');
    if (storyTextElement && storyTextElement.textContent.trim() !== '') {
        const newText = storyTextElement.textContent;
        typeWriterEffect(storyTextElement, newText);
    }

    // 检查是否有图片需要加载
    if (document.getElementById("image-loading") &&
        document.getElementById("image-loading").style.display !== "none") {
        console.log("Image loading is active, initializing dots");
        startLoadingDots("image-dots");
    }
});