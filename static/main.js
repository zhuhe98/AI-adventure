// 全局变量
let characters = [];

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

    document.getElementById('modal-body').innerHTML = `
        <h3>✧ ${c.name} ✧</h3>
        <img src="${c.avatar}" class="pixel-art" style="width:100px; height:100px; border-radius:0; margin: 10px auto; display:block; border:4px solid #5c3e24;">
        <p>${c.detail || '暂无详细信息'}</p>
        <h4>✦ 相关事件 ✦</h4>
        <ul>${c.events && c.events.length ? c.events.map(e => `<li>${e}</li>`).join('') : '<li>暂无相关事件</li>'}</ul>
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
    document.getElementById("image-loading").style.display = "block";
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
        if(data.image){
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
                document.getElementById("image-loading").textContent = "图片加载失败，重试中...";
                setTimeout(checkImage, 3000);
            };
        } else {
            console.log("[Polling] No image yet, continuing to poll...");
            setTimeout(checkImage, 2000);
        }
    })
    .catch(error => {
        console.error("[Polling] Fetch error:", error);
        document.getElementById("image-loading").textContent = "检查图片中...";
        setTimeout(checkImage, 3000);
    });
}

// 初始化函数 - 页面加载完成后调用
function initializeGame(charactersData, storyData, imagePending) {
    try {
        // 解析角色数据
        if (typeof charactersData === 'string') {
            characters = JSON.parse(charactersData);
        } else {
            characters = charactersData || [];
        }

        // 增强像素效果
        enhancePixelEffects();

        // 输出调试信息
        debugInfo(storyData, characters);

        // 检查文本是否为空
        const storyText = document.querySelector('.story-text');
        if (storyText && (!storyText.textContent || storyText.textContent.trim() === '')) {
            storyText.textContent = '欢迎来到星露谷时光咖啡馆，这里的故事正等待你的探索...';
        }

        // 如果需要，开始检查图片
        if (imagePending) {
            setTimeout(checkImage, 1000);
        } else {
            const imageContainer = document.getElementById("image-container");
            if (imageContainer) {
                imageContainer.style.display = "none";
            }
        }
    } catch (e) {
        console.error("初始化游戏出错:", e);
    }
}

// 页面加载时仅对新文本应用打字机效果
document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM loaded, enhancing interface");

    // 查找故事文本元素并应用打字机效果（如果存在）
    const storyTextElement = document.querySelector('.story-text');
    if (storyTextElement && storyTextElement.textContent.trim() !== '') {
        const newText = storyTextElement.textContent;
        typeWriterEffect(storyTextElement, newText);
    }

    // 检查是否有图片需要加载
    if (document.getElementById("image-loading") &&
        document.getElementById("image-loading").style.display === "block") {
        console.log("Image loading is active, initializing dots");
        startLoadingDots("image-dots");
    }
});