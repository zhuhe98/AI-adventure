from openai import OpenAI
import openai
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import os
import re
import base64
import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

app = Flask(__name__)
app.secret_key = os.urandom(24)

# ----------- OpenAI API 配置 -----------
# 默认 Key (用于管理员测试)
DEFAULT_API_KEY = ""

# ----------- 启动页 -----------
@app.route('/')
def start():
    return render_template('start.html')

@app.route('/start', methods=['POST'])
def start_game():
    api_key_input = request.form.get('api_key', '').strip()
    enable_images = request.form.get('enable_images') == 'on'
    language = request.form.get('language', 'zh')
    
    # API Key 验证逻辑
    if api_key_input == "0611":
        api_key = DEFAULT_API_KEY
    else:
        api_key = api_key_input

    # 验证 API Key 是否有效
    try:
        test_client = OpenAI(api_key=api_key)
        # 尝试一个简单的请求来验证 Key
        test_client.models.list()
    except Exception as e:
        print(f"API Key validation failed: {e}")
        return jsonify({"success": False, "error": "API Key 验证失败，请检查后重试。"})

    # 保存设置到 Session
    session['api_key'] = api_key
    session['enable_images'] = enable_images
    session['language'] = language
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
    
    return jsonify({"success": True, "redirect_url": url_for('game')})


# ----------- 游戏主界面 -----------
# 修改 app.py 中的 game 函数，添加历史记录支持

# ----------- UI Translations -----------
UI_TRANSLATIONS = {
    'zh': {
        'title': '星露谷时光咖啡馆',
        'subtitle': '文字冒险',
        'history_btn': '📜 历史记录',
        'menu_btn': '⚙️ 菜单',
        'input_placeholder': '或者输入你的自定义行动...',
        'send_btn': '发送',
        'wait_option': '等待给出选项',
        'response_prompt': '你想如何回应？',
        'characters_title': '✦ 人物 ✦',
        'no_characters': '暂无角色',
        'loading_text': '正在生成',
        'image_loading': '图片生成中',
        'menu_title': '✧ 游戏菜单 ✧',
        'save_btn': '💾 存档',
        'load_btn': '📂 读档',
        'settings_btn': '🔧 设置',
        'home_btn': '🏠 回到标题',
        'history_title': '✧ 故事历史 ✧',
        'close_btn': '×',
        'no_detail': '暂无详细信息',
        'no_events': '暂无相关事件',
        'events_title': '✦ 相关事件 ✦',
        'save_success': '存档成功',
        'save_error': '存档失败',
        'load_error': '读档失败',
        'load_confirm': '读档会覆盖当前进度，确定要读档吗？',
        'delete_confirm': '确定要删除这个存档吗？',
        'delete_btn': '删除',
        'no_saves': '暂无存档',
        'storage_full': 'localStorage已满，请删除旧存档'
    },
    'ja': {
        'title': 'スターデュー・カフェ',
        'subtitle': 'テキストアドベンチャー',
        'history_btn': '📜 履歴',
        'menu_btn': '⚙️ メニュー',
        'input_placeholder': 'または自由に行動を入力...',
        'send_btn': '送信',
        'wait_option': '選択肢を待つ',
        'response_prompt': 'どう応えますか？',
        'characters_title': '✦ キャラクター ✦',
        'no_characters': 'キャラクターなし',
        'loading_text': '生成中',
        'image_loading': '画像生成中',
        'menu_title': '✧ メニュー ✧',
        'save_btn': '💾 セーブ',
        'load_btn': '📂 ロード',
        'settings_btn': '🔧 設定',
        'home_btn': '🏠 タイトルへ',
        'history_title': '✧ 物語の履歴 ✧',
        'close_btn': '×',
        'no_detail': '詳細情報なし',
        'no_events': '関連イベントなし',
        'events_title': '✦ 関連イベント ✦',
        'save_success': 'セーブ成功',
        'save_error': 'セーブ失敗',
        'load_error': 'ロード失敗',
        'load_confirm': 'ロードすると現在の進行状況が上書きされます。本当にロードしますか？',
        'delete_confirm': '本当にこのセーブデータを削除しますか？',
        'delete_btn': '削除',
        'no_saves': 'セーブデータなし',
        'storage_full': 'localStorageが満杯です。古いセーブを削除してください'
    }
}

@app.route('/game')
def game():
    if 'api_key' not in session:
        return redirect(url_for('start'))

    if not session.get('history'):
        try:
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
        except Exception as e:
            # 如果生成失败（例如Key过期），返回错误页或重定向
            print(f"Error generating first story: {e}")
            return redirect(url_for('start'))

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

    lang = session.get('language', 'zh')
    return render_template('index.html',
                           story=story_for_template,
                           characters=session.get('characters', []),
                           language=lang,
                           ui=UI_TRANSLATIONS.get(lang, UI_TRANSLATIONS['zh']))


# 修改 next_step 函数中的返回部分
@app.route('/next_step', methods=['POST'])
def next_step():
    if 'api_key' not in session:
        return jsonify({"error": "Session expired"}), 401

    player_input = request.form.get('player_input')
    branch_choice = request.form.get('branch_choice')
    user_action = player_input or branch_choice

    # ------- AI 生成 story -------
    try:
        story = generate_story(user_action)  # story 已经包含 text, options, image
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    # 判断是否需要生成图片
    if story.get('image_pending'):
        session['pending_image_prompt'] = story['image_content']
    else:
        story['image_content'] = None
        story['image_pending'] = False

    # ------- AI 可能生成新角色 -------
    if story.get('new_character'):
        char = story['new_character']
        # 自动生成 avatar
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

    lang = session.get('language', 'zh')
    return render_template('index.html',
                           story=story_for_template,
                           characters=session.get('characters', []),
                           language=lang,
                           ui=UI_TRANSLATIONS.get(lang, UI_TRANSLATIONS['zh']))


@app.route('/get_image')
def get_image():
    print("get_image route called")

    # 检查 session 是否存在
    if not session or 'api_key' not in session:
        print("Error: No session or API key found")
        return jsonify({"image": None, "error": "No session"})

    # 检查是否开启了图像生成
    if not session.get('enable_images', True):
        return jsonify({"image": None})

    print("Session keys:", session.keys())

    if 'pending_image_prompt' in session:
        prompt = session.get('pending_image_prompt')
        print(f"Found image prompt in session: {prompt}")

        # 生成图片
        try:
            image_url = generate_image(prompt, session.get('story', ''))
            print(f"Generated image URL: {image_url}")

            # 更新故事记录
            if session.get('history'):
                session['history'][-1]['image'] = image_url
                session['history'][-1]['image_pending'] = False
                session.modified = True
            
            # 生成成功（或返回了占位符）后再清除 prompt
            session.pop('pending_image_prompt', None)
            session.modified = True

            return jsonify({"image": image_url})
        except Exception as e:
            print(f"Error generating image: {e}")
            # 出错也清除，避免死循环
            session.pop('pending_image_prompt', None)
            session.modified = True
            return jsonify({"image": None, "error": str(e)})
    else:
        print("No pending image prompt found in session")
        # 检查并修复不一致状态：前端在轮询但后端没有prompt
        if session.get('history') and session['history'][-1].get('image_pending'):
             print("Fixing inconsistent state: history says pending but no prompt.")
             session['history'][-1]['image_pending'] = False
             # 返回占位图以停止轮询
             fallback_url = "/api/placeholder/800/400"
             session['history'][-1]['image'] = fallback_url
             session.modified = True
             return jsonify({"image": fallback_url})
             
        return jsonify({"image": None})


# ----------- 存档导出 -----------
@app.route('/save')
def save():
    """返回完整的游戏状态用于localStorage存储"""
    if 'api_key' not in session:
        return jsonify({"error": "No active session"}), 401
    
    return jsonify({
        "success": True,
        "data": {
            "settings": session.get('settings'),
            "history": session.get('history', []),
            "characters": session.get('characters', []),
            "story": session.get('story', ''),
            "player_stats": session.get('player_stats', {}),
            "language": session.get('language', 'zh'),
            "enable_images": session.get('enable_images', True)
        }
    })

# ----------- 读档功能 -----------
@app.route('/load', methods=['POST'])
def load():
    """从localStorage接收存档数据并恢复到session"""
    if 'api_key' not in session:
        return jsonify({"error": "No active session"}), 401
    
    try:
        data = request.json
        save_data = data.get('data', {})
        
        # 恢复所有session数据
        session['settings'] = save_data.get('settings', {})
        session['history'] = save_data.get('history', [])
        session['characters'] = save_data.get('characters', [])
        session['story'] = save_data.get('story', '')
        session['player_stats'] = save_data.get('player_stats', {})
        session['language'] = save_data.get('language', 'zh')
        session['enable_images'] = save_data.get('enable_images', True)
        
        session.modified = True
        
        return jsonify({"success": True})
    except Exception as e:
        print(f"Error loading game: {e}")
        return jsonify({"error": str(e)}), 500

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
# ----------- Pydantic Models -----------
class NewCharacter(BaseModel):
    id: str
    name: str
    desc: str
    detail: str
    event: str

class StoryResponse(BaseModel):
    story_text: str = Field(..., description="The main story narrative")
    options: List[str] = Field(..., description="3-4 branching options for the player")
    image_prompt: Optional[str] = Field(None, description="Description for generating an image, if a new scene or important event occurs")
    new_character: Optional[NewCharacter] = Field(None, description="Details of a new character if one appears")


# ----------- AI 生成剧情 (Structured Outputs) -----------
def generate_story(user_input):
    client = OpenAI(api_key=session['api_key'])
    
    messages = []
    
    # 1. 系统提示
    settings = session.get('settings', {})
    language = session.get('language', 'zh')
    lang_instruction = "请使用中文回复。" if language == 'zh' else "Please respond in Japanese (日本語)."
    
    messages.append({"role": "system", "content": f"""
                        你是一名 AI DM，负责主持一场文字冒险游戏。
                        - 主题：{settings.get('theme')}
                        - 风格：{settings.get('style')}
                        - 难度：{settings.get('difficulty')}
                        
                        请根据前序剧情和用户选项完成续写。
                        当前处于故事的{get_narrative_stage()}阶段，请据此调整叙事节奏与情节深度。
                        
                        {lang_instruction}
                        
                        请生成 JSON 格式的输出，包含剧情文本、分支选项、图片描述（可选）和新角色信息（可选）。
                        """})

    # 2. 最近的故事历史
    character_names = [c['name'] for c in session.get('characters', [])]
    messages.append({"role": "user", "content": "已知角色：" + ("，".join(character_names) if character_names else "当前还没有已知角色。")})
    messages.append({"role": "user", "content": "之前的情节内容为：" + session.get('story', '')})
    for record in session.get('history', [])[-5:]:
        messages.append({"role": "user", "content": record.get('player_action', '')})

    # 3. 当前输入
    messages.append({"role": "user", "content": "用户当前选项为：" + user_input})

    print("Sending request to GPT (Structured Output)...")
    
    try:
        completion = client.responses.parse(
            model="gpt-4o-mini",
            input=messages,
            text_format=StoryResponse,
        )

        message = completion.output_parsed
        
        # 检查是否允许生成图片
        image_prompt = message.image_prompt
        if not session.get('enable_images', True):
            image_prompt = None

        # Construct the return dictionary expected by the app
        return {
            "text": message.story_text,
            "image_content": image_prompt,
            "image_pending": bool(image_prompt),
            "options": message.options,
            "new_character": {
                "id": message.new_character.id,
                "name": message.new_character.name,
                "desc": message.new_character.desc,
                "detail": message.new_character.detail,
                "event": message.new_character.event
            } if message.new_character else None
        }

    except Exception as e:
        print(f"Error in generate_story: {e}")
        # Fallback or re-raise
        raise e


# ----------- AI 生成图片（示例） -----------
def generate_image(prompt, story):
    if not session.get('enable_images', True):
        return None

    client = OpenAI(api_key=session['api_key'])

    # 简化：直接返回占位图
    # 如果接 DALL·E:
    print("开始生成图像")
    try:
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
    
        response = client.responses.create(
            model="gpt-4.1-mini",
            input="【画风要求】Japanese anime style or galgame visual novel artwork。\n" + img_prompt,
            tools=[{"type": "image_generation"}],
        )
        
        image_data = [
            output.result
            for output in response.output
            if output.type == "image_generation_call"
        ]
        
        if image_data:
            image_base64 = image_data[0]
            # 确保 static/images 目录存在
            save_dir = os.path.join(app.static_folder, 'images')
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
                
            filename = f"{uuid.uuid4()}.png"
            filepath = os.path.join(save_dir, filename)
            
            with open(filepath, "wb") as f:
                f.write(base64.b64decode(image_base64))
                
            return url_for('static', filename=f'images/{filename}')
            
    except Exception as e:
        print(f"Image generation failed: {e}")
        return "/api/placeholder/800/400"

    return "/api/placeholder/800/400"


def generate_avatar(prompt):
    # 开发期占位
    if not prompt:
        return "/api/placeholder/100/100"
        
    if not session.get('enable_images', True):
        return "/api/placeholder/100/100"

    client = OpenAI(api_key=session['api_key'])

    # 未来可接 OpenAI Image 或 MJ
    print("开始生成头像")
    try:
        response = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "你是一个专业的prompt工程师，需要根据给出的内容生成合适的prompt以让DALL-E生成合适的人物介绍界面的头像"},
                {"role": "user", "content": f"在进行一场AI文字冒险游戏，现在需要生成{prompt}的头像，图片风格需要时日式轻小说的黑白插图风。请你生成一段适合的prompt。"},
            ],
            model="gpt-4o-mini",
        )
        img_prompt = response.choices[0].message.content
        print(f"头像Prompt: {img_prompt}.")
    
        response = client.responses.create(
            model="gpt-4.1-mini",
            input="【画风要求】Japanese anime style or galgame visual novel artwork。\n" + img_prompt,
            tools=[{"type": "image_generation"}],
        )
        
        image_data = [
            output.result
            for output in response.output
            if output.type == "image_generation_call"
        ]
        
        if image_data:
            image_base64 = image_data[0]
            # 确保 static/images 目录存在
            save_dir = os.path.join(app.static_folder, 'images')
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
                
            filename = f"{uuid.uuid4()}.png"
            filepath = os.path.join(save_dir, filename)
            
            with open(filepath, "wb") as f:
                f.write(base64.b64decode(image_base64))
                
            return url_for('static', filename=f'images/{filename}')
            
    except Exception as e:
        print(f"Avatar generation failed: {e}")
        return "/api/placeholder/100/100"


if __name__ == '__main__':
    app.run(debug=True)