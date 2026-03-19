from google import genai
from google.genai import types
import requests
import re
import os
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
FEISHU_WEBHOOK = os.environ.get("FEISHU_WEBHOOK", "")
FEISHU_WEBHOOKS = list(dict.fromkeys([
    wh for wh in [
        os.environ.get("FEISHU_WEBHOOK_1", ""),
        os.environ.get("FEISHU_WEBHOOK_2", ""),
        os.environ.get("FEISHU_WEBHOOK_3", ""),
        FEISHU_WEBHOOK,
    ] if wh
]))

GITHUB_REPO = os.environ.get("GITHUB_REPO", "")

VIDEO_PLATFORMS = [
    "抖音直播", "快手直播", "B站直播", "小红书直播",
    "微信视频号直播", "虎牙直播", "TikTok直播",
    "BigoLive", "Hiya", "Mico", "YY直播", "映客直播", "花椒直播"
]

VOICE_PLATFORMS = [
    "荔枝FM", "氧气语音", "Soul", "陌陌",
    "Look直播", "比心直播", "会玩直播", "hello直播"
]


def clean_for_feishu(text):
    text = re.sub(r'\n[A-Za-z0-9+/=_\-]{30,}\n', '\n', text)
    text = re.sub(r'[A-Za-z0-9+/=]{40,}', '', text)
    text = re.sub(r'^#{1,3}\s+(.+)$', r'**\1**', text, flags=re.MULTILINE)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def markdown_to_html_content(text):
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'^---$', '<hr>', text, flags=re.MULTILINE)
    text = re.sub(r'^\* (.+)$', r'<li>\1</li>', text, flags=re.MULTILINE)
    text = re.sub(r'^- (.+)$', r'<li>\1</li>', text, flags=re.MULTILINE)
    text = re.sub(r'^\d+\. (.+)$', r'<li>\1</li>', text, flags=re.MULTILINE)
    text = re.sub(r'\[(.+?)\]\((https?://[^\)]+)\)', r'<a href="\2" target="_blank">\1</a>', text)
    text = text.replace('\n', '<br>')
    return text


def generate_html_report(report_text, week_num, week_range, sources):
    now = datetime.now(timezone(timedelta(hours=8))).strftime('%Y年%m月%d日 %H:%M')
    html_content = markdown_to_html_content(report_text)

    sources_html = ""
    if sources:
        sources_items = ""
        for idx, (title, uri) in enumerate(sources[:15], 1):
            sources_items += f'<li><a href="{uri}" target="_blank">{title}</a></li>'
        sources_html = f"""
        <div class="sources">
            <h3>🔗 本期信息来源</h3>
            <ol>{sources_items}</ol>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{week_num} 娱乐直播竞品周报</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif;
            background: #f0f2f5;
            color: #333;
            line-height: 1.8;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px 20px;
            text-align: center;
        }}
        .header h1 {{ font-size: 28px; margin-bottom: 8px; }}
        .header .meta {{ font-size: 14px; opacity: 0.85; }}
        .badge {{
            display: inline-block;
            background: rgba(255,255,255,0.2);
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 13px;
            margin-top: 8px;
        }}
        .back-btn {{
            display: inline-block;
            margin-top: 14px;
            background: rgba(255,255,255,0.15);
            color: white;
            padding: 6px 16px;
            border-radius: 20px;
            font-size: 13px;
            text-decoration: none;
            border: 1px solid rgba(255,255,255,0.3);
        }}
        .back-btn:hover {{ background: rgba(255,255,255,0.25); }}
        .container {{
            max-width: 900px;
            margin: 30px auto;
            padding: 0 16px 60px;
        }}
        .card {{
            background: white;
            border-radius: 12px;
            padding: 28px 32px;
            margin-bottom: 20px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.06);
        }}
        .report-content {{ font-size: 15px; line-height: 1.9; }}
        .report-content strong {{ color: #5b4fcf; font-weight: 600; }}
        .report-content hr {{ border: none; border-top: 1px solid #eee; margin: 20px 0; }}
        .report-content li {{ margin: 6px 0 6px 20px; list-style: disc; }}
        .report-content a {{ color: #667eea; text-decoration: none; }}
        .report-content a:hover {{ text-decoration: underline; }}
        .sources {{
            background: #f8f9ff;
            border-radius: 10px;
            padding: 20px 24px;
            margin-top: 24px;
        }}
        .sources h3 {{ font-size: 15px; color: #5b4fcf; margin-bottom: 12px; }}
        .sources ol {{ padding-left: 20px; }}
        .sources li {{ margin: 6px 0; font-size: 13px; }}
        .sources a {{ color: #667eea; text-decoration: none; word-break: break-all; }}
        .footer {{ text-align: center; color: #999; font-size: 13px; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎙️ 娱乐直播竞品周报</h1>
        <div class="meta">统计周期：{week_range}</div>
        <div class="badge">🤖 Gemini AI + Google Search 实时生成</div>
        <br>
        <a class="back-btn" href="./index.html">← 返回历史报告列表</a>
    </div>
    <div class="container">
        <div class="card">
            <div class="report-content">{html_content}</div>
            {sources_html}
        </div>
        <div class="footer">生成时间：{now}（北京时间）· 由 Gemini AI 自动生成，请核实重要信息</div>
    </div>
</body>
</html>"""
    return html


def update_index_page(docs_dir, week_num, week_range, filename):
    index_path = docs_dir / "index.html"
    history_file = docs_dir / "history.json"

    history = []
    if history_file.exists():
        try:
            history = json.loads(history_file.read_text(encoding='utf-8'))
        except Exception:
            history = []

    new_entry = {
        "week_num": week_num,
        "week_range": week_range,
        "filename": filename,
        "generated_at": datetime.now(timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M')
    }
    history = [h for h in history if h.get("filename") != filename]
    history.insert(0, new_entry)
    history_file.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding='utf-8')

    history_items = ""
    for item in history:
        is_latest = item["filename"] == filename
        badge = '<span class="latest-badge">最新</span>' if is_latest else ''
        history_items += f"""
        <div class="report-item {'latest' if is_latest else ''}">
            <div class="report-info">
                <div class="report-title">{item['week_num']} 娱乐直播竞品周报 {badge}</div>
                <div class="report-meta">统计周期：{item['week_range']} · 生成于 {item['generated_at']}</div>
            </div>
            <a class="view-btn" href="./{item['filename']}">查看报告 →</a>
        </div>"""

    index_html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>娱乐直播竞品周报 · 历史归档</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif;
            background: #f0f2f5;
            color: #333;
            line-height: 1.8;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 48px 20px;
            text-align: center;
        }}
        .header h1 {{ font-size: 30px; margin-bottom: 8px; }}
        .header p {{ font-size: 14px; opacity: 0.85; }}
        .container {{
            max-width: 800px;
            margin: 30px auto;
            padding: 0 16px 60px;
        }}
        .section-title {{
            font-size: 16px;
            font-weight: 600;
            color: #555;
            margin-bottom: 16px;
            padding-left: 4px;
        }}
        .report-item {{
            background: white;
            border-radius: 12px;
            padding: 20px 24px;
            margin-bottom: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            display: flex;
            align-items: center;
            justify-content: space-between;
            transition: box-shadow 0.2s;
        }}
        .report-item:hover {{ box-shadow: 0 4px 16px rgba(0,0,0,0.1); }}
        .report-item.latest {{ border-left: 4px solid #667eea; }}
        .report-title {{ font-size: 16px; font-weight: 600; color: #333; margin-bottom: 4px; }}
        .report-meta {{ font-size: 13px; color: #999; }}
        .latest-badge {{
            display: inline-block;
            background: #667eea;
            color: white;
            font-size: 11px;
            padding: 2px 8px;
            border-radius: 10px;
            margin-left: 8px;
            vertical-align: middle;
        }}
        .view-btn {{
            background: linear-gradient(135deg, #667eea, #764ba2);
            color: white;
            padding: 8px 18px;
            border-radius: 20px;
            font-size: 13px;
            text-decoration: none;
            white-space: nowrap;
            margin-left: 16px;
        }}
        .view-btn:hover {{ opacity: 0.9; }}
        .footer {{ text-align: center; color: #bbb; font-size: 13px; margin-top: 30px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎙️ 娱乐直播竞品周报</h1>
        <p>娱乐直播 · 语音直播 · AI进展 · 每周自动更新</p>
    </div>
    <div class="container">
        <div class="section-title">📚 历史报告归档（共 {len(history)} 期）</div>
        {history_items}
        <div class="footer">🤖 由 Gemini AI + Google Search 自动生成 · 每周一更新</div>
    </div>
</body>
</html>"""

    index_path.write_text(index_html, encoding='utf-8')
    print(f"✅ 历史首页已更新，共 {len(history)} 期报告")


def generate_report():
    client = genai.Client(api_key=GEMINI_API_KEY)

    beijing_tz = timezone(timedelta(hours=8))
    today = datetime.now(beijing_tz).replace(tzinfo=None)
    last_week = today - timedelta(days=7)
    week_range = f"{last_week.strftime('%Y年%m月%d日')}～{today.strftime('%Y年%m月%d日')}"
    week_num = today.strftime("%Y年第%W周")
    date_start = last_week.strftime('%Y-%m-%d')
    month_str = today.strftime('%Y年%m月')

    video_str = "、".join(VIDEO_PLATFORMS)
    voice_str = "、".join(VOICE_PLATFORMS)

    prompt = f"""你是一位专业的娱乐直播行业分析师。
今天的日期是 {today.strftime('%Y年%m月%d日')}，本次报告统计周期为 {week_range}。

---
⚠️ 搜索与筛选执行策略（必须严格执行）：

1. 【强制前置搜索令】：搜索时查询词必须包含时间限定，格式：
   '平台名' + '直播' + '{month_str}' 或 'after:{date_start}'
   识别网页原始发布时间标签，不被文章内文日期误导，无法确定日期标注'日期待核实'。

2. 【分级采纳原则】：
   - 核心区（{last_week.strftime('%Y年%m月%d日')}～{today.strftime('%Y年%m月%d日')}）：优先采用，报告主体。
   - 缓冲区（{today.strftime('%Y年%m月')}1日至今）：本周无动态时补充，加注【补录】。
   - 财报数据：可采用最近一期财报数据，注明财报期间。

3. 【数据收集要求】：每个平台尽力搜集以下数据指标（有则填，无则注明"暂无公开数据"）：
   - MAU（月活跃用户数）
   - 收入/打赏流水（季度或年度）
   - 付费用户数及付费率
   - 平台全球收入趋势
   数据来源优先级：①官方财报/官方公告（标注"来源可靠"）②行业媒体报道（标注"来源：媒体，需核实"）

4. 【防空置指令】：平台无动态时输出行业趋势观察，不返回空白。

5. 【严格剔除】：电商带货、购物直播、商品推广等电商变现内容不纳入报告。

---

请按以下结构输出报告，只使用**加粗**和---分隔线，不使用##标题：

**📅 {week_num} 娱乐直播竞品周报（{week_range}）**

---

**🎬 模块一：娱乐直播赛道**
分析平台：{video_str}

**🆕 1.1 新功能动态**
格式：**平台名**：功能描述【来源：XXX，日期】

**💰 1.2 营收与消费数据**
格式：
**平台名**：
- MAU：xxx（来源：xxx）
- 收入/流水：xxx（来源：xxx）
- 付费用户：xxx（来源：xxx）
- 本周营收动态：xxx【来源：XXX，日期】

**🤖 1.3 AI × 娱乐直播进展**
格式：**平台名**：AI进展描述【来源：XXX，日期】

---

**🎙️ 模块二：语音直播赛道**
分析平台：{voice_str}

**🆕 2.1 新功能动态**
格式：**平台名**：功能描述【来源：XXX，日期】

**💰 2.2 营收与消费数据**
格式：
**平台名**：
- MAU：xxx（来源：xxx）
- 收入/流水：xxx（来源：xxx）
- 付费用户：xxx（来源：xxx）
- 本周营收动态：xxx【来源：XXX，日期】

**🤖 2.3 AI × 语音直播进展**
格式：**平台名**：AI进展描述【来源：XXX，日期】

---

**📊 模块三：本周竞争格局小结**
1. 娱乐直播赛道：本周最积极平台及战略意图
2. 语音直播赛道：本周最积极平台及战略意图
3. 跨赛道趋势：共同信号与差异化路线
4. 值得关注的行业趋势

---

**⚡ 下周重点关注事项**
列出3-5条跨赛道需跟进的具体事项

---

输出要求：语言专业简洁，重要数据加粗，适合企业内部阅读。
⚠️ 字数控制：全文控制在3000字以内，每条动态不超过60字。"""

    response = None
    for model_name in ['gemini-2.5-pro-preview-03-25', 'gemini-2.5-pro', 'gemini-2.5-flash']:
        try:
            print(f"尝试使用模型：{model_name}")
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())]
                )
            )
            print(f"✅ 模型 {model_name} 调用成功")
            break
        except Exception as e:
            print(f"⚠️ 模型 {model_name} 失败：{e}，尝试降级...")
            continue

    if response is None:
        raise Exception("所有模型均调用失败")

    try:
        for candidate in response.candidates:
            if hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
                print(f"DEBUG 引用来源数量：{len(candidate.grounding_metadata.grounding_chunks)}")
    except Exception as e:
        print(f"DEBUG 无搜索数据：{e}")

    report_text = clean_for_feishu(response.text)

    sources = []
    try:
        for candidate in response.candidates:
            if hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
                for chunk in candidate.grounding_metadata.grounding_chunks:
                    if hasattr(chunk, 'web') and chunk.web:
                        title = chunk.web.title if chunk.web.title else ""
                        uri = chunk.web.uri if chunk.web.uri else ""
                        if uri and title and len(title) > 5 and "." not in title:
                            sources.append((title, uri))
                        elif uri and title and len(title) > 10:
                            sources.append((title, uri))
    except Exception:
        pass

    seen = set()
    unique_sources = []
    for title, uri in sources:
        if title not in seen:
            seen.add(title)
            unique_sources.append((title, uri))
    unique_sources = unique_sources[:15]

    filename = f"report_{today.strftime('%Y_%W')}.html"
    docs_dir = Path("docs")
    docs_dir.mkdir(exist_ok=True)

    html = generate_html_report(report_text, week_num, week_range, unique_sources)
    (docs_dir / filename).write_text(html, encoding='utf-8')
    print(f"✅ 本期 HTML 报告已保存：docs/{filename}")

    update_index_page(docs_dir, week_num, week_range, filename)

    if GITHUB_REPO:
        owner, repo = GITHUB_REPO.split('/')
        report_url = f"https://{owner}.github.io/{repo}/{filename}"
        index_url = f"https://{owner}.github.io/{repo}/"
    else:
        report_url = ""
        index_url = ""

    return report_text, week_num, week_range, unique_sources, report_url, index_url


def send_to_feishu(summary, week_num, week_range, sources, report_url, index_url, webhook_url):
    beijing_tz = timezone(timedelta(hours=8))
    now_beijing = datetime.now(beijing_tz).strftime('%Y-%m-%d %H:%M')

    lines = [l.strip() for l in summary.split('\n') if l.strip() and '---' not in l]
    preview_lines = [l for l in lines if '**' in l and '：' in l][:6]
    preview_text = '\n'.join(preview_lines) if preview_lines else summary[:400]

    elements = [
        {
            "tag": "markdown",
            "content": f"**统计周期：{week_range}**\n\n**📌 本周核心动态速览**\n\n{preview_text}"
        },
        {"tag": "hr"}
    ]

    action_buttons = []
    if report_url:
        action_buttons.append({
            "tag": "button",
            "text": {"tag": "plain_text", "content": "📄 本期完整报告"},
            "type": "primary",
            "url": report_url
        })
    if index_url:
        action_buttons.append({
            "tag": "button",
            "text": {"tag": "plain_text", "content": "📚 历史报告归档"},
            "type": "default",
            "url": index_url
        })

    if action_buttons:
        elements.append({"tag": "action", "actions": action_buttons})

    elements.append({
        "tag": "note",
        "elements": [{"tag": "plain_text",
            "content": f"🤖 Gemini AI + Google Search 实时生成 · {now_beijing} (北京时间)"}]
    })

    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": f"🎙️ 娱乐直播竞品周报 · {week_num}"},
                "template": "purple"
            },
            "elements": elements
        }
    }

    resp = requests.post(webhook_url, json=payload)
    print(f"推送结果：{resp.json()}")


def main():
    print("🚀 开始生成娱乐直播竞品周报（含实时搜索）...")
    report_text, week_num, week_range, sources, report_url, index_url = generate_report()
    print(f"✅ 报告生成完成，共 {len(report_text)} 字")
    print(f"📎 本期报告：{report_url}")
    print(f"📚 历史归档：{index_url}")

    if not FEISHU_WEBHOOKS:
        print("⚠️ 未配置飞书 Webhook，跳过推送")
        return

    for idx, webhook in enumerate(FEISHU_WEBHOOKS, 1):
        print(f"📱 推送到第 {idx} 个飞书群...")
        send_to_feishu(report_text, week_num, week_range, sources, report_url, index_url, webhook)

    print("✅ 全部推送完成！")


if __name__ == "__main__":
    main()
