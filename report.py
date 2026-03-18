from google import genai
from google.genai import types
import requests
import re
import os
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
FEISHU_WEBHOOK = os.environ["FEISHU_WEBHOOK"]
GITHUB_REPO = os.environ.get("GITHUB_REPO", "")

PLATFORMS = [
    "抖音直播", "快手直播", "B站直播", "小红书直播",
    "微信视频号直播", "虎牙直播", "YY直播", "荔枝FM", "氧气语音"
]

def clean_for_feishu(text):
    text = re.sub(r'\n[A-Za-z0-9+/=_\-]{30,}\n', '\n', text)
    text = re.sub(r'[A-Za-z0-9+/=]{40,}', '', text)
    text = re.sub(r'^#{1,3}\s+(.+)$', r'**\1**', text, flags=re.MULTILINE)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def markdown_to_html_content(text):
    """简单转换 Markdown 为 HTML"""
    # 加粗
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # 分隔线
    text = re.sub(r'^---$', '<hr>', text, flags=re.MULTILINE)
    # 列表项
    text = re.sub(r'^\* (.+)$', r'<li>\1</li>', text, flags=re.MULTILINE)
    text = re.sub(r'^- (.+)$', r'<li>\1</li>', text, flags=re.MULTILINE)
    # 数字列表
    text = re.sub(r'^\d+\. (.+)$', r'<li>\1</li>', text, flags=re.MULTILINE)
    # 链接
    text = re.sub(r'\[(.+?)\]\((https?://[^\)]+)\)', r'<a href="\2" target="_blank">\1</a>', text)
    # 换行
    text = text.replace('\n', '<br>')
    return text

def generate_html_report(report_text, week_num, week_range, sources):
    """生成美观的 HTML 报告"""
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
        .container {{
            max-width: 860px;
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
        .report-content {{
            font-size: 15px;
            line-height: 1.9;
        }}
        .report-content strong {{
            color: #5b4fcf;
            font-weight: 600;
        }}
        .report-content hr {{
            border: none;
            border-top: 1px solid #eee;
            margin: 20px 0;
        }}
        .report-content li {{
            margin: 6px 0 6px 20px;
            list-style: disc;
        }}
        .report-content a {{
            color: #667eea;
            text-decoration: none;
        }}
        .report-content a:hover {{ text-decoration: underline; }}
        .sources {{
            background: #f8f9ff;
            border-radius: 10px;
            padding: 20px 24px;
            margin-top: 24px;
        }}
        .sources h3 {{
            font-size: 15px;
            color: #5b4fcf;
            margin-bottom: 12px;
        }}
        .sources ol {{
            padding-left: 20px;
        }}
        .sources li {{
            margin: 6px 0;
            font-size: 13px;
        }}
        .sources a {{
            color: #667eea;
            text-decoration: none;
            word-break: break-all;
        }}
        .sources a:hover {{ text-decoration: underline; }}
        .footer {{
            text-align: center;
            color: #999;
            font-size: 13px;
            margin-top: 20px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎙️ 娱乐直播竞品周报</h1>
        <div class="meta">统计周期：{week_range}</div>
        <div class="badge">🤖 Gemini AI + Google Search 实时生成</div>
    </div>
    <div class="container">
        <div class="card">
            <div class="report-content">
                {html_content}
            </div>
            {sources_html}
        </div>
        <div class="footer">
            生成时间：{now}（北京时间）· 由 Gemini AI 自动生成，请核实重要信息
        </div>
    </div>
</body>
</html>"""
    return html

def generate_report():
    client = genai.Client(api_key=GEMINI_API_KEY)

    beijing_tz = timezone(timedelta(hours=8))
    today = datetime.now(beijing_tz).replace(tzinfo=None)
    last_week = today - timedelta(days=7)
    week_range = f"{last_week.strftime('%Y年%m月%d日')}～{today.strftime('%Y年%m月%d日')}"
    week_num = today.strftime("%Y年第%W周")
    platforms_str = "、".join(PLATFORMS)
    date_start = last_week.strftime('%Y-%m-%d')
    month_str = today.strftime('%Y年%m月')

    prompt = f"""你是一位专业的娱乐直播行业分析师。
今天的日期是 {today.strftime('%Y年%m月%d日')}，本次报告统计周期为 {week_range}。

---
⚠️ 搜索与筛选执行策略（必须严格执行）：

1. 【强制前置搜索令】：在执行搜索时，必须将查询词构造为：
   '平台名' + '直播' + '{month_str}' 或 '平台名' + '直播新功能' + 'after:{date_start}'
   强制搜索引擎优先抓取本周快讯。
   请务必识别搜索结果网页的原始发布时间标签，不要被文章内文提到的往期回顾日期误导。
   如果无法确定发布日期，请标注'日期待核实'。

2. 【分级采纳原则】：
   - 核心区（{last_week.strftime('%Y年%m月%d日')}～{today.strftime('%Y年%m月%d日')}）：全力搜集并详细阐释，这是报告的主体。
   - 缓冲区（{today.strftime('%Y年%m月')}1日至今）：若本周无动态，可作为'近期回顾'少量补充，必须加注【本周：补录动态】。
   - 严禁此范围之外：严禁出现在报告中，除非是重大的季度财报数据且在本周被媒体解读。

3. 【防空置指令】：若某平台在本周确实无任何公开动态，请输出一份'行业本周大盘趋势观察'，而非直接返回空白。

---

调研平台：{platforms_str}

聚焦娱乐直播场景：视频娱乐直播、语音直播、陪伴直播、才艺直播、游戏直播、语音房、PK直播等。
严格剔除：电商带货、购物直播、商品推广等电商变现相关内容。

---

请按以下结构输出报告，只使用**加粗**和---分隔线，不要使用##标题：

**📅 {week_num} 娱乐直播竞品周报（{week_range}）**

---

**🆕 一、新功能动态速览**
分平台列出娱乐直播场景新功能（电商功能不纳入）
格式：**平台名**：功能描述【来源：XXX，日期】
若本周无动态：标注"本周暂无最新动态"，并补充近期最重要动作【本周：补录动态】

---

**💰 二、娱乐直播营收玩法动态**
打赏礼物更新、付费订阅变化、PK连麦商业化、主播激励政策（剔除电商带货内容）
格式：**平台名**：营收动态描述【来源：XXX，日期】
若本周无动态：标注"本周暂无最新动态"，并补充近期动向【本周：补录动态】

---

**🤖 三、AI × 娱乐直播进展**
AI主播/数字人、AI变声美颜、AI弹幕互动、AIGC工具等（剔除电商AI应用）
格式：**平台名**：AI进展描述【来源：XXX，日期】
若本周无动态：标注"本周暂无最新动态"，并补充近期动向【本周：补录动态】

---

**📊 四、本周竞争格局小结**
1. 本周最积极的平台及战略意图
2. 各平台差异化路线对比
3. 值得关注的行业趋势信号

---

**⚡ 五、下周重点关注事项**
列出3-5条下周需跟进的具体事项

---

输出要求：语言专业简洁，重要信息加粗，适合企业内部阅读。
⚠️ 字数控制：全文总字数严格控制在2000字以内，每个平台每条动态不超过50字，优先保留最重要的信息，删除冗余描述。"""

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
        raise Exception("所有模型均调用失败，请检查 API Key 或额度")

    try:
        for candidate in response.candidates:
            if hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
                print(f"DEBUG 引用来源数量：{len(candidate.grounding_metadata.grounding_chunks)}")
    except Exception as e:
        print(f"DEBUG 无搜索数据：{e}")

    report_text = clean_for_feishu(response.text)

    # 提取来源
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

    # 生成并保存 HTML 报告
    html = generate_html_report(report_text, week_num, week_range, unique_sources)
    docs_dir = Path("docs")
    docs_dir.mkdir(exist_ok=True)
    html_path = docs_dir / "index.html"
    html_path.write_text(html, encoding='utf-8')
    print(f"✅ HTML 报告已保存：{html_path}")

    # 生成 GitHub Pages 链接
    if GITHUB_REPO:
        owner, repo = GITHUB_REPO.split('/')
        report_url = f"https://{owner}.github.io/{repo}/"
    else:
        report_url = ""

    return report_text, week_num, week_range, unique_sources, report_url


def send_to_feishu(summary, week_num, week_range, sources, report_url):
    beijing_tz = timezone(timedelta(hours=8))
    now_beijing = datetime.now(beijing_tz).strftime('%Y-%m-%d %H:%M')

    # 提取前3条关键动态作为飞书摘要
    lines = [l.strip() for l in summary.split('\n') if l.strip() and '---' not in l and '**📅' not in l]
    preview_lines = [l for l in lines if '**' in l and '：' in l][:5]
    preview_text = '\n'.join(preview_lines) if preview_lines else summary[:300]

    # 构造飞书卡片：摘要 + 链接按钮
    elements = [
        {
            "tag": "markdown",
            "content": f"**统计周期：{week_range}**\n\n**📌 本周核心动态速览**\n\n{preview_text}"
        },
        {"tag": "hr"}
    ]

    # 添加报告链接按钮
    if report_url:
        elements.append({
            "tag": "action",
            "actions": [
                {
                    "tag": "button",
                    "text": {"tag": "plain_text", "content": "📄 查看完整 HTML 报告"},
                    "type": "primary",
                    "url": report_url
                }
            ]
        })

    elements.append({
        "tag": "note",
        "elements": [
            {
                "tag": "plain_text",
                "content": f"🤖 Gemini AI + Google Search 实时生成 · {now_beijing} (北京时间)"
            }
        ]
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

    resp = requests.post(FEISHU_WEBHOOK, json=payload)
    print(f"飞书推送结果：{resp.json()}")


def main():
    print("🚀 开始生成娱乐直播竞品周报（含实时搜索）...")
    report_text, week_num, week_range, sources, report_url = generate_report()
    print(f"✅ 报告生成完成，共 {len(report_text)} 字")
    print(f"📎 报告链接：{report_url}")
    send_to_feishu(report_text, week_num, week_range, sources, report_url)
    print("📱 飞书推送完成！")


if __name__ == "__main__":
    main()
