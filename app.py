from openai import OpenAI
import openai
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import os
import re
from datetime import datetime

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ----------- OpenAI API 配置 -----------
API_KEY = ""  # 替换成你的API Key
client = OpenAI(api_key=API_KEY)
image_client = OpenAI(api_key=API_KEY)

# ----------- 启动页 -----------
@app.route('/')
def start():
    return render_template('start.html')

@app.route('/start', methods=['POST'])
def start_game():
    session['settings'] = {
        'theme': request.form.get('theme'),
        'style': request.form.get('style'),
        'difficulty': request.form.get('difficulty'),
        'custom_intro': request.form.get('custom_intro')
    }
    session['history'] = []
    session['characters'] = []
    session['story'] = ''
    session['player_stats'] = {
        'items': [],
        'relationships': {},
        'stats': {'energy': 100, 'mood': 50},
        'achievements': []
    }
    return redirect(url_for('game'))


# ----------- 游戏主界面 -----------
# 修改 app.py 中的 game 函数，添加历史记录支持

@app.route('/game')
def game():
    if not session.get('history'):
        first_story = generate_story("初始")
        first_story_record = {
            "full_text": first_story['text'],
            "new_text": first_story['text'],
            "history_text": "",  # 首次没有历史文本
            "image": first_story.get('image_content'),
            "image_pending": first_story.get('image_pending', False),
            "options": first_story['options'],
            "player_action": "初始"
        }
        session['history'] = [first_story_record]
        session['story'] = first_story['text']
        if first_story.get('image_pending'):
            session['pending_image_prompt'] = first_story.get('image_content', '')

    # 确保从session获取最新的记录
    current_record = session['history'][-1] if session.get('history') else {}

    # 获取最近的历史文本（最多3条，不包括当前记录）
    recent_history = ""
    if len(session.get('history', [])) > 1:
        recent_records = session['history'][:-1][-3:]  # 最近的3条历史记录
        recent_history = "\n\n".join([rec.get('new_text', '') for rec in recent_records])

    # 转换记录格式为模板可用格式
    story_for_template = {
        'text': current_record.get('new_text', ''),
        'history_text': recent_history,
        'full_text': session.get('story', ''),  # 完整历史
        'image': current_record.get('image'),
        'image_pending': current_record.get('image_pending', False),
        'options': current_record.get('options', [])
    }

    # 打印调试信息
    print("传递给模板的数据:")
    print("Story:", story_for_template)
    print("Characters:", session.get('characters', []))

    return render_template('index.html',
                           story=story_for_template,
                           characters=session.get('characters', []))


# 修改 next_step 函数中的返回部分
@app.route('/next_step', methods=['POST'])
def next_step():
    player_input = request.form.get('player_input')
    branch_choice = request.form.get('branch_choice')
    user_action = player_input or branch_choice

    # ------- AI 生成 story -------
    story = generate_story(user_action)  # story 已经包含 text, options, image

    # 判断是否需要生成图片
    if story.get('image_pending'):
        session['pending_image_prompt'] = story['image_content']
    else:
        story['image_content'] = None
        story['image_pending'] = False

    # ------- AI 可能生成新角色 -------
    if story.get('new_character'):
        char = story['new_character']
        # 自动生成 avatar（这里只是示范，后续接绘图接口）
        avatar_url = generate_avatar(char.get('desc', '神秘角色'))

        # 检查是否已存在
        if not any(c['id'] == char['id'] for c in session['characters']):
            session['characters'].append({
                "id": char['id'],
                "name": char['name'],
                "avatar": avatar_url,
                "desc": char['desc'],
                "detail": char['detail'],
                "events": [char['event']]
            })
        else:
            # 已存在则追加事件
            for c in session['characters']:
                if c['id'] == char['id']:
                    c['events'].append(char['event'])

    # ------- 存入历史 -------
    session['story'] += story['text'] + "\n"

    # 计算历史文本（不包含最新生成的文本）
    previous_text = session['story'][:-len(story['text'])] if session['story'] else ""

    # 创建story记录
    story_record = {
        "full_text": session['story'],  # 完整故事历史
        "new_text": story['text'],  # 只有新生成的文本
        "history_text": previous_text,  # 历史文本（不含新文本）
        "image": story['image_content'],
        "image_pending": story['image_pending'],
        "options": story['options'],
        "player_action": user_action
    }
    session['history'].append(story_record)

    # 获取最近的历史文本（最多3条，不包括当前记录）
    recent_history = ""
    if len(session.get('history', [])) > 1:
        recent_records = session['history'][:-1][-3:]  # 最近的3条历史记录
        recent_history = "\n\n".join([rec.get('new_text', '') for rec in recent_records])

    # 强制保存session
    session.modified = True

    # 打印调试信息
    print("生成的记录:", story_record)
    print("当前角色:", session.get('characters', []))

    # 转换记录格式为模板可用格式
    story_for_template = {
        'text': story_record.get('new_text', ''),
        'history_text': recent_history,
        'full_text': session.get('story', ''),  # 完整历史
        'image': story_record.get('image'),
        'image_pending': story_record.get('image_pending', False),
        'options': story_record.get('options', [])
    }

    return render_template('index.html',
                           story=story_for_template,
                           characters=session.get('characters', []))


@app.route('/get_image')
def get_image():
    print("get_image route called")

    # 检查 session 是否存在
    if not session:
        print("Error: No session found")
        return jsonify({"image": None, "error": "No session"})

    print("Session keys:", session.keys())

    if 'pending_image_prompt' in session:
        prompt = session.get('pending_image_prompt')
        print(f"Found image prompt in session: {prompt}")

        # 先清除 session 中的值，然后再生成图片
        # 这样如果生成失败，下次请求不会重复尝试同一个请求
        session.pop('pending_image_prompt', None)
        session.modified = True

        # 生成图片
        try:
            image_url = generate_image(prompt, session.get('story', ''))
            print(f"Generated image URL: {image_url}")

            # 更新故事记录
            if session.get('history'):
                session['history'][-1]['image'] = image_url
                session['history'][-1]['image_pending'] = False
                session.modified = True

            return jsonify({"image": image_url})
        except Exception as e:
            print(f"Error generating image: {e}")
            return jsonify({"image": None, "error": str(e)})
    else:
        print("No pending image prompt found in session")
        return jsonify({"image": None})


# ----------- 存档导出 -----------
@app.route('/save')
def save():
    return jsonify({
        "settings": session.get('settings'),
        "history": session.get('history'),
        "characters": session.get('characters'),
        "player_stats": session.get('player_stats', {})
    })

# ----------- 存档系统 -----------
@app.route('/save_game', methods=['POST'])
def save_game():
    save_name = request.form.get('save_name', f"存档 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    save_data = {
        'timestamp': datetime.now().isoformat(),
        'settings': session.get('settings'),
        'history': session.get('history'),
        'characters': session.get('characters'),
        'player_stats': session.get('player_stats')
    }
    # 这里应该添加存档到数据库或文件系统的逻辑
    # 简化实现：存到session中
    if 'saves' not in session:
        session['saves'] = {}
    save_id = str(len(session['saves']) + 1)
    session['saves'][save_id] = save_data
    return jsonify({"save_id": save_id, "save_name": save_name})

@app.route('/load_game/<save_id>')
def load_game(save_id):
    # 简化实现：从session中读取
    if 'saves' in session and save_id in session['saves']:
        save_data = session['saves'][save_id]
        session['settings'] = save_data.get('settings')
        session['history'] = save_data.get('history')
        session['characters'] = save_data.get('characters')
        session['player_stats'] = save_data.get('player_stats')
        session['story'] = '\n'.join([h.get('text', '') for h in session['history']])
        return redirect(url_for('game'))
    return render_template('error.html', message="存档未找到")

# ----------- 游戏状态系统 -----------
@app.route('/game_status')
def game_status():
    player_stats = session.get('player_stats', {
        'items': [],
        'relationships': {},
        'stats': {'energy': 100, 'mood': 50},
        'achievements': []
    })
    return jsonify(player_stats)

# ----------- 获取叙事阶段 -----------
def get_narrative_stage():
    # 根据历史长度判断故事阶段
    history_length = len(session.get('history', []))
    if history_length < 3:
        return "开场/介绍"
    elif history_length < 8:
        return "发展/冲突"
    elif history_length < 12:
        return "高潮/转折"
    else:
        return "结局/收尾"

# ----------- AI 生成剧情 -----------
def generate_story(user_input):
    messages = []
    char_info = {}
    # 1. 系统提示
    settings = session.get('settings', {})
    messages.append({"role": "system", "content": f"""
                        你是一名 AI DM，负责主持一场文字冒险游戏。
                        - 主题：{settings.get('theme')}
                        - 风格：{settings.get('style')}
                        - 难度：{settings.get('difficulty')}
                        【严格规则】
                            1. 你的输出必须包含【剧情】和【分支】这两个标记，缺少其中任意一个都会导致程序崩溃。
                            2. 不允许在输出中包含除格式外的任何解释、备注、自然语言。
                            3. 输出的格式、标记、标点都要与以下示例严格一致。
                        如果有前序剧情请根据之前的剧情内容和用户选项完成续写。
                        当前处于故事的{get_narrative_stage()}阶段，请据此调整叙事节奏与情节深度。
                        格式为:
                        【剧情】...
                        【分支】1. xxx 2. xxx 3. xxx
                        【图片】图片描述 (可选，如果没有则不要输出这一项) 
                        【新角色】(可选，如果有新角色出场则输出, 如果没有则不要输出这一项, 如果是游戏开始则输出初始角色)
                        - id: xxx
                          name: xxx
                          desc: xxx
                          detail: xxx
                          event: xxx"""})

    # 2. 最近的故事历史
    character_names = [c['name'] for c in session.get('characters', [])]
    messages.append({"role": "user", "content": "已知角色：" + "，".join(character_names) if character_names else "当前还没有已知角色。"})
    messages.append({"role": "user", "content": "之前的情节内容为：" + session['story']})
    for record in session.get('history', [])[-5:]:
        messages.append({"role": "user", "content": record.get('player_action', '')})


    # 3. 当前输入
    messages.append({"role": "user", "content": "用户当前选项为：" + user_input})

    # 4. 调用 GPT
    # ========== retry 机制 ==========
    max_retry = 3
    for attempt in range(1, max_retry + 1):
        response = client.chat.completions.create(
            messages=messages,
            model="gpt-4o-mini",
        )
        reply = response.choices[0].message.content
        print(f"GPT Output (Attempt {attempt}):", reply)

        # 检查是否完整
        has_story = bool(re.search(r'【剧情】', reply))
        has_branch = bool(re.search(r'【分支】', reply))

        if has_story and has_branch:
            break
        else:
            print(f"⚠️ 第 {attempt} 次生成缺少必要标记，自动重试")
    else:
        raise ValueError("GPT 连续3次输出格式错误，请检查 Prompt 或模型状态")
    # 5. 解析 GPT 输出
    # 提取剧情
    story_match = re.search(r'【剧情】([\s\S]*?)(?=【分支】)', reply)
    story_text = story_match.group(1).strip() if story_match else ""
    # 提取分支
    branch_match = re.search(r'【分支】([\s\S]*?)(?=【|$)', reply)
    branches = []
    if branch_match:
        branch_text = branch_match.group(1).strip()
        # 直接提取形如 "1. xxx 2. xxx 3. xxx" 里的内容
        branches = re.findall(r'\d+\.\s*([^0-9【】]+?)(?=\d+\.|$)', branch_text)
        branches = [b.strip() for b in branches]

    # 3. 提取图片（可选）
    image_content = None
    image_match = re.search(r'【图片】([\s\S]*?)(?=【|$)', reply)
    if image_match:
        image_content = image_match.group(1).strip()

    # 4. 提取新角色（可选）
    char_info = {}
    role_match = re.search(r'【新角色】([\s\S]*?)$', reply)
    if role_match:
        new_char_block = role_match.group(1).strip()
        lines = [line.strip('- ').strip() for line in new_char_block.strip().split('\n') if line.strip()]
        char_info = {line.split(":")[0]: line.split(":", 1)[1].strip() for line in lines if ':' in line}


    return {
        "text": story_text,
        "image_content": image_content,
        "image_pending": bool(image_content),
        "options": branches,
        "new_character": {
            "id": char_info.get('id', ''),
            "name": char_info.get('name', ''),
            "desc": char_info.get('desc', ''),
            "detail": char_info.get('detail', ''),
            "event": char_info.get('event', '')
        } if "id" in char_info else None
    }


# ----------- AI 生成图片（示例） -----------
def generate_image(prompt, story):
    # 简化：直接返回占位图
    # 如果接 DALL·E:
    print("开始生成图像")
    response = client.chat.completions.create(
        messages=[
            {"role": "system", "content": "你是一个专业的prompt工程师，需要根据给出的内容生成合适的prompt以让DALL-E生成合适的图像"},
            {"role": "user", "content": f"在进行一场AI文字冒险游戏，现在需要生成描绘{prompt}的图片。请你根据目前的故事内容，生成一段适合的prompt。"},
            {"role": "user", "content": f"目前的故事内容是：{story}."}
        ],
        model="gpt-4o-mini",
    )
    img_prompt = response.choices[0].message.content
    print(f"图像Prompt: {img_prompt}.")
    response = client.images.generate(
        model="dall-e-2",
        prompt="【画风要求】Japanese anime style or galgame visual novel artwork。\n" + img_prompt,
        size="512x512",
        quality="standard",
        n=1,
    )
    return response.data[0].url
    #return "/api/placeholder/800/400"


def generate_avatar(prompt):
    # 开发期占位
    if not prompt:
        return "/api/placeholder/100/100"
    # 未来可接 OpenAI Image 或 MJ
    print("开始生成头像")
    response = client.chat.completions.create(
        messages=[
            {"role": "system", "content": "你是一个专业的prompt工程师，需要根据给出的内容生成合适的prompt以让DALL-E生成合适的人物介绍界面的头像"},
            {"role": "user", "content": f"在进行一场AI文字冒险游戏，现在需要生成{prompt}的头像，图片风格需要时日式轻小说的黑白插图风。请你生成一段适合的prompt。"},
        ],
        model="gpt-4o-mini",
    )
    img_prompt = response.choices[0].message.content
    print(f"头像Prompt: {img_prompt}.")
    response = client.images.generate(
        model="dall-e-2",
        prompt="【画风要求】Japanese anime style or galgame visual novel artwork。\n" + img_prompt,
        size="256x256",
        quality="standard",
        n=1,
    )
    return response.data[0].url
    #return f"/api/placeholder/100/100?desc={prompt}"


if __name__ == '__main__':
    app.run(debug=True)