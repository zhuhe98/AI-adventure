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
        <h3>${c.name}</h3>
        <img src="${c.avatar}" style="width:80px; border-radius:50%; margin: 10px 0;">
        <p>${c.detail}</p>
        <h4>相关事件</h4>
        <ul>${c.events.map(e => `<li>${e}</li>`).join('')}</ul>
    `;
    document.getElementById('character-modal').style.display = 'flex';
}

function closeCharacterModal() {
    document.getElementById('character-modal').style.display = 'none';
}

// 加载状态相关函数
function startLoading() {
    const loadingDots = document.getElementById('loading-dots');
    loadingDots.style.display = 'block';
    let dotCount = 0;
    loadingDots.timer = setInterval(() => {
        dotCount = (dotCount + 1) % 4;
        document.getElementById('dots').textContent = '.'.repeat(dotCount);
    }, 500);
}

function stopLoading() {
    const loadingDots = document.getElementById('loading-dots');
    clearInterval(loadingDots.timer);
    loadingDots.style.display = 'none';
}

// 动态省略号（通用）
function startLoadingDots(id) {
    console.log("Starting loading dots for:", id);
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
    console.log("Loading animation started");
}

function stopLoadingDots(id) {
    console.log("Stopping loading dots for:", id);
    const target = document.getElementById(id);
    if (!target) {
        console.error("Loading dots target not found:", id);
        return;
    }
    clearInterval(target.timer);
    target.style.display = 'none';
}

// 页面加载时仅对新文本应用打字机效果
document.addEventListener('DOMContentLoaded', function() {
    console.log("DOM loaded, applying typewriter effect");
    const storyTextElement = document.querySelector('.story-text');
    if (storyTextElement && storyTextElement.textContent.trim() !== '') {
        const newText = storyTextElement.textContent;
        typeWriterEffect(storyTextElement, newText);
    }

    // 检查是否有图片需要加载（确保这里的代码和HTML中的条件一致）
    if (document.getElementById("image-loading").style.display === "block") {
        console.log("Image loading is active, initializing dots");
        startLoadingDots("image-dots");
    }
});

// 异步图片检查函数
function checkImage() {
    console.log("[Polling] Checking for image at " + new Date().toLocaleTimeString());

    // 使用绝对路径，确保在任何路由下都正确
    const imageUrl = window.location.origin + '/get_image?nocache=' + Date.now();
    console.log("[Polling] Sending request to:", imageUrl);

    // 确保图片加载UI元素显示
    document.getElementById("image-container").style.display = "flex";
    document.getElementById("image-loading").style.display = "block";
    startLoadingDots("image-dots");

    // 使用fetch API请求图片
    fetch(imageUrl, {
        method: 'GET',
        headers: {
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        },
        credentials: 'same-origin' // 确保发送cookies
    })
    .then(response => {
        console.log("[Polling] Response status:", response.status);
        if (!response.ok) {
            throw new Error("Server returned " + response.status);
        }
        return response.json();
    })
    .then(data => {
        console.log("[Polling] Response data:", data);

        if (data.image) {
            // 图片URL返回成功
            console.log("[Polling] Image URL received:", data.image);

            const img = document.getElementById("story-image");
            img.src = data.image;

            img.onload = () => {
                console.log("[Polling] Image loaded successfully");
                stopLoadingDots("image-dots");
                document.getElementById("image-loading").style.display = "none";
                img.style.display = 'block';
                img.style.opacity = 0;
                setTimeout(() => {
                    img.style.transition = "opacity 0.5s ease-in-out";
                    img.style.opacity = 1;
                }, 50);
            };

            img.onerror = () => {
                console.error("[Polling] Failed to load image URL:", data.image);
                document.getElementById("image-loading").textContent = "图片加载失败，重试中...";
                // 即使图片加载失败，也继续轮询
                setTimeout(checkImage, 3000);
            };
        } else {
            // 没有图片，继续轮询
            console.log("[Polling] No image yet, continuing to poll...");
            setTimeout(checkImage, 2000);
        }
    })
    .catch(error => {
        // 请求出错
        console.error("[Polling] Fetch error:", error);
        document.getElementById("image-loading").textContent = "检查图片中...";
        // 出错后继续轮询
        setTimeout(checkImage, 3000);
    });
}