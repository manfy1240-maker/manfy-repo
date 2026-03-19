import anthropic
import requests
import re
import os
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
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
    # 加粗
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # 分隔线
    text = re.sub(r'^---$', '<hr class="section-hr">', text, flags=re.MULTILINE)
    # 无序列表
    text = re.sub(r'^[\*\-] (.+)$', r'<li>\1</li>', text, flags=re.MULTILINE)
    # 有序列表
    text = re.sub(r'^\d+\. (.+)$', r'<li>\1</li>', text, flags=re.MULTILINE)
    # 链接
    text = re.sub(r'\[(.+?)\]\((https?://[^\)]+)\)', r'<a href="\2" target="_blank">\1</a>', text)
    # 换行
    lines = text.split('\n')
    result = []
    for line in lines:
        if line.startswith('<li>') or line.startswith('<hr') or line.strip() == '':
            result.append(line)
        else:
            result.append(f'<p>{line}</p>' if line.strip() else '')
    return '\n'.join(result)


def generate_html_report(report_text, week_num, week_range, sources):
    now = datetime.now(timezone(timedelta(hours=8))).strftime('%Y年%m月%d日 %H:%M')
    html_content = markdown_to_html_content(report_text)

    sources_html = ""
    if sources:
        sources_items = ""
        for idx, (title, uri) in enumerate(sources[:15], 1):
            sources_items += f'<li><a href="{uri}" target="_blank">{title}</a></li>'
        sources_html = f"""
        <div class="sources-box">
            <div class="sources-title">🔗 本期信息来源</div>
            <ol class="sources-list">{sources_items}</ol>
        </div>"""

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{week_num} 娱乐直播竞品周报</title>
    <style>
        :root {{
            --primary: #6c63ff;
            --primary-dark: #5a52d5;
            --secondary: #764ba2;
            --bg: #f4f5f9;
            --card-bg: #ffffff;
            --text: #2d2d2d;
            --text-light: #888;
            --border: #eaeaea;
            --accent: #f0eeff;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', 'Segoe UI', sans-serif;
            background: var(--bg);
            color: var(--text);
            line-height: 1.85;
            font-size: 15px;
        }}

        /* 顶部 Header */
        .header {{
            background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
            color: white;
            padding: 52px 24px 40px;
            text-align: center;
            position: relative;
            overflow: hidden;
        }}
        .header::before {{
            content: '';
            position: absolute;
            top: -60px; right: -60px;
            width: 220px; height: 220px;
            background: rgba(255,255,255,0.06);
            border-radius: 50%;
        }}
        .header::after {{
            content: '';
            position: absolute;
            bottom: -80px; left: -40px;
            width: 280px; height: 280px;
            background: rgba(255,255,255,0.04);
            border-radius: 50%;
        }}
        .header h1 {{
            font-size: 26px;
            font-weight: 700;
            letter-spacing: 0.5px;
            margin-bottom: 10px;
        }}
        .header .period {{
            font-size: 14px;
            opacity: 0.88;
            margin-bottom: 14px;
        }}
        .header-badges {{
            display: flex;
            justify-content: center;
            gap: 10px;
            flex-wrap: wrap;
            margin-bottom: 18px;
        }}
        .badge {{
            display: inline-block;
            background: rgba(255,255,255,0.18);
            padding: 4px 14px;
            border-radius: 20px;
            font-size: 12px;
            border: 1px solid rgba(255,255,255,0.25);
        }}
        .back-btn {{
            display: inline-block;
            background: rgba(255,255,255,0.15);
            color: white;
            padding: 7px 18px;
            border-radius: 20px;
            font-size: 13px;
            text-decoration: none;
            border: 1px solid rgba(255,255,255,0.3);
            transition: background 0.2s;
        }}
        .back-btn:hover {{ background: rgba(255,255,255,0.28); }}

        /* 主体容器 */
        .container {{
            max-width: 920px;
            margin: 32px auto;
            padding: 0 18px 72px;
        }}

        /* 卡片 */
        .card {{
            background: var(--card-bg);
            border-radius: 14px;
            padding: 32px 36px;
            margin-bottom: 20px;
            box-shadow: 0 2px 16px rgba(0,0,0,0.06);
        }}

        /* 报告正文 */
        .report-content p {{
            margin-bottom: 10px;
            color: var(--text);
        }}
        .report-content p:empty {{ display: none; }}
        .report-content strong {{
            color: var(--primary-dark);
            font-weight: 600;
        }}
        .report-content .section-hr {{
            border: none;
            border-top: 2px solid var(--accent);
            margin: 28px 0;
        }}
        .report-content li {{
            margin: 7px 0 7px 22px;
            list-style: disc;
            color: var(--text);
        }}
        .report-content a {{
            color: var(--primary);
            text-decoration: none;
            border-bottom: 1px solid transparent;
            transition: border-color 0.2s;
        }}
        .report-content a:hover {{ border-bottom-color: var(--primary); }}

        /* 模块标题识别高亮 */
        .report-content p strong:first-child {{
            display: inline-block;
        }}

        /* 来源区域 */
        .sources-box {{
            background: var(--accent);
            border-radius: 10px;
            padding: 20px 24px;
            margin-top: 28px;
            border-left: 4px solid var(--primary);
        }}
        .sources-title {{
            font-size: 14px;
            font-weight: 600;
            color: var(--primary-dark);
            margin-bottom: 12px;
        }}
        .sources-list {{
            padding-left: 20px;
        }}
        .sources-list li {{
            margin: 7px 0;
            font-size: 13px;
            color: var(--text-light);
            list-style: decimal;
        }}
        .sources-list a {{
            color: var(--primary);
            text-decoration: none;
            word-break: break-all;
        }}
        .sources-list a:hover {{ text-decoration: underline; }}

        /* 底部 */
        .footer {{
            text-align: center;
            color: var(--text-light);
            font-size: 12px;
            margin-top: 24px;
            padding: 0 16px;
        }}

        /* 响应式 */
        @media (max-width: 600px) {{
            .card {{ padding: 20px 18px; }}
            .header h1 {{ font-size: 22px; }}
            .container {{ padding: 0 12px 60px; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎙️ 娱乐直播竞品周报</h1>
        <div class="period">统计周期：{week_range}</div>
        <div class="header-badges">
            <span class="badge">🤖 Claude AI 生成</span>
            <span class="badge">🔍 实时搜索增强</span>
            <span class="badge">📊 双赛道分析</span>
        </div>
        <a class="back-btn" href="./index.html">← 返回历史报告列表</a>
    </div>

    <div class="container">
        <div class="card">
            <div class="report-content">
                {html_content}
            </div>
            {sources_html}
        </div>
        <div class="footer">
            生成时间：{now}（北京时间）&nbsp;·&nbsp;
            由 Claude Sonnet 4.6 + Web Search 自动生成，重要信息请以官方来源为准
        </div>
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
    for i, item in enumerate(history):
        is_latest = item["filename"] == filename
        badge = '<span class="latest-badge">最新</span>' if is_latest else f'<span class="issue-num">第 {len(history)-i} 期</span>'
        history_items += f"""
        <div class="report-item {'latest' if is_latest else ''}">
            <div class="report-info">
                <div class="report-title">{item['week_num']} 娱乐直播竞品周报 {badge}</div>
                <div class="report-meta">📅 {item['week_range']} &nbsp;·&nbsp; 🕐 生成于 {item['generated_at']}</div>
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
        :root {{
            --primary: #6c63ff;
            --secondary: #764ba2;
            --bg: #f4f5f9;
            --text: #2d2d2d;
            --text-light: #999;
            --accent: #f0eeff;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif;
            background: var(--bg);
            color: var(--text);
        }}
        .header {{
            background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
            color: white;
            padding: 52px 24px 44px;
            text-align: center;
            position: relative;
            overflow: hidden;
        }}
        .header::before {{
            content: '';
            position: absolute;
            top: -50px; right: -50px;
            width: 200px; height: 200px;
            background: rgba(255,255,255,0.06);
            border-radius: 50%;
        }}
        .header h1 {{ font-size: 28px; font-weight: 700; margin-bottom: 10px; }}
        .header p {{ font-size: 14px; opacity: 0.85; margin-bottom: 16px; }}
        .header-stats {{
            display: flex;
            justify-content: center;
            gap: 20px;
            flex-wrap: wrap;
        }}
        .stat-item {{
            background: rgba(255,255,255,0.15);
            padding: 6px 16px;
            border-radius: 20px;
            font-size: 13px;
            border: 1px solid rgba(255,255,255,0.2);
        }}
        .container {{
            max-width: 820px;
            margin: 32px auto;
            padding: 0 18px 72px;
        }}
        .section-title {{
            font-size: 15px;
            font-weight: 600;
            color: #666;
            margin-bottom: 16px;
            padding-left: 2px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .report-item {{
            background: white;
            border-radius: 14px;
            padding: 20px 24px;
            margin-bottom: 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 16px;
            transition: box-shadow 0.2s, transform 0.2s;
        }}
        .report-item:hover {{
            box-shadow: 0 6px 20px rgba(108,99,255,0.12);
            transform: translateY(-1px);
        }}
        .report-item.latest {{
            border-left: 4px solid var(--primary);
            background: linear-gradient(to right, #faf9ff, white);
        }}
        .report-info {{ flex: 1; min-width: 0; }}
        .report-title {{
            font-size: 15px;
            font-weight: 600;
            color: var(--text);
            margin-bottom: 5px;
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
        }}
        .report-meta {{ font-size: 12px; color: var(--text-light); }}
        .latest-badge {{
            background: var(--primary);
            color: white;
            font-size: 11px;
            padding: 2px 9px;
            border-radius: 10px;
            font-weight: 500;
        }}
        .issue-num {{
            background: var(--accent);
            color: var(--primary);
            font-size: 11px;
            padding: 2px 9px;
            border-radius: 10px;
        }}
        .view-btn {{
            background: linear-gradient(135deg, var(--primary), var(--secondary));
            color: white;
            padding: 8px 20px;
            border-radius: 20px;
            font-size: 13px;
            text-decoration: none;
            white-space: nowrap;
            transition: opacity 0.2s;
            flex-shrink: 0;
        }}
        .view-btn:hover {{ opacity: 0.88; }}
        .footer {{
            text-align: center;
            color: var(--text-light);
            font-size: 12px;
            margin-top: 32px;
        }}
        @media (max-width: 600px) {{
            .report-item {{ flex-direction: column; align-items: flex-start; }}
            .view-btn {{ align-self: flex-end; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎙️ 娱乐直播竞品周报</h1>
        <p>娱乐直播 · 语音直播 · AI进展 · 每周自动更新</p>
        <div class="header-stats">
            <span class="stat-item">📚 共 {len(history)} 期报告</span>
            <span class="stat-item">🤖 Claude AI 驱动</span>
            <span class="stat-item">🔄 每周一自动更新</span>
        </div>
    </div>
    <div class="container">
        <div class="section-title">📋 历史报告归档</div>
        {history_items}
        <div class="footer">
            由 Claude Sonnet 4.6 + Web Search 自动生成 · 每周一北京时间 09:00 更新
        </div>
    </div>
</body>
</html>"""

    index_path.write_text(index_html, encoding='utf-8')
    print(f"✅ 历史首页已更新，共 {len(history)} 期报告")


def generate_report():
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

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

输出要求：语言专业简洁，重要数据加粗，适合企业内部阅读。"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8000,
        tools=[{
            "type": "web_search_20250305",
            "name": "web_search"
        }],
        messages=[{"role": "user", "content": prompt}]
    )

    # 提取文本内容
    report_text = ""
    for block in response.content:
        if hasattr(block, 'text'):
            report_text += block.text

    report_text = clean_for_feishu(report_text)
    print(f"✅ 报告生成完成，共 {len(report_text)} 字")

    # Claude API 暂无 grounding metadata，来源从正文提取
    sources = []
    url_pattern = re.findall(r'\[([^\]]+)\]\((https?://[^\)]+)\)', report_text)
    for title, uri in url_pattern:
        if len(title) > 5:
            sources.append((title, uri))
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
    print(f"✅ HTML 报告已保存：docs/{filename}")

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
            "content": f"🤖 Claude Sonnet 4.6 + Web Search 实时生成 · {now_beijing} (北京时间)"}]
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
    print("🚀 开始生成娱乐直播竞品周报（Claude Sonnet 4.6）...")
    report_text, week_num, week_range, sources, report_url, index_url = generate_report()
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
