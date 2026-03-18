from google import genai
from google.genai import types
import requests
import os
from datetime import datetime, timezone, timedelta

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
FEISHU_WEBHOOK = os.environ["FEISHU_WEBHOOK"]

PLATFORMS = [
    "抖音直播", "快手直播", "B站直播", "小红书直播",
    "微信视频号直播", "虎牙直播", "YY直播", "荔枝FM", "氧气语音"
]

def generate_report():
    client = genai.Client(api_key=GEMINI_API_KEY)

    beijing_tz = timezone(timedelta(hours=8))
    today = datetime.now(beijing_tz).replace(tzinfo=None)
    last_week = today - timedelta(days=7)
    week_range = f"{last_week.strftime('%Y年%m月%d日')}～{today.strftime('%Y年%m月%d日')}"
    week_num = today.strftime("%Y年第%W周")
    platforms_str = "、".join(PLATFORMS)

    prompt = f"""你是一位专业的娱乐直播行业分析师。

今天的日期是 {today.strftime('%Y年%m月%d日')}，本次报告统计周期为 {week_range}。

请通过实时搜索，分别搜索以下每个平台的最新动态：{platforms_str}。
搜索时在查询词中加入"{today.strftime('%Y年%m月')}"或"近期"等时间词，优先获取最新信息。

调研平台：{platforms_str}

要求：
1. 优先采用 {last_week.strftime('%Y年%m月%d日')} 至 {today.strftime('%Y年%m月%d日')} 的信息，如该时间段内确实无信息，可采用最近1个月内的相关动态并注明日期
2. 每条信息附上来源，格式：【来源：XXX，日期】
3. 无法找到可靠来源的内容不得编造，注明"暂无可核实动态"
4. 聚焦娱乐直播场景：视频娱乐直播、语音直播、陪伴直播、才艺直播、游戏直播、语音房、PK直播等
5. 剔除电商带货、购物直播、商品推广等电商变现相关内容

请按以下结构输出，使用飞书支持的格式（用**加粗**代替标题，用---分隔）：

---
**📅 {week_num} 娱乐直播竞品周报（{week_range}）**
---

**🆕 一、新功能动态速览**
分平台列出各平台在娱乐直播场景上线或测试的新功能（电商功能不纳入）
格式：**平台名**：功能描述【来源：XXX，日期】

---

**💰 二、娱乐直播营收玩法动态**
梳理各平台娱乐直播营收动态，包括：打赏礼物更新、付费订阅变化、PK连麦商业化、主播激励政策
格式：**平台名**：营收动态描述【来源：XXX，日期】

---

**🤖 三、AI × 娱乐直播进展**
聚焦各平台AI在娱乐直播的应用：AI主播/数字人、AI变声美颜、AI弹幕互动、AIGC工具等
格式：**平台名**：AI进展描述【来源：XXX，日期】

---

**📊 四、本周竞争格局小结**
1. 本周最积极的平台及战略意图
2. 各平台差异化路线对比
3. 值得关注的行业趋势信号

---

**⚡ 五、下周重点关注事项**
列出3-5条下周需跟进的具体事项

---

输出要求：语言专业简洁，重要信息加粗，适合企业内部阅读。"""

    # 升级为 gemini-2.5-pro 提升搜索质量
    response = client.models.generate_content(
        model='gemini-2.5-pro',
        contents=prompt,
        config=types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())]
        )
    )

    try:
        for candidate in response.candidates:
            if hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
                print(f"DEBUG 引用来源数量：{len(candidate.grounding_metadata.grounding_chunks)}")
    except Exception as e:
        print(f"DEBUG 无搜索数据：{e}")

    report_text = response.text

    # 提取来源：展示标题 + 日期 + 可点击链接
    sources = []
    try:
        for candidate in response.candidates:
            if hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
                for chunk in candidate.grounding_metadata.grounding_chunks:
                    if hasattr(chunk, 'web') and chunk.web:
                        title = chunk.web.title if chunk.web.title else "未知来源"
                        uri = chunk.web.uri if chunk.web.uri else ""
                        if uri:
                            sources.append((title, uri))
    except Exception:
        pass

    if sources:
        # 去重保留前15条
        seen = set()
        unique_sources = []
        for title, uri in sources:
            if title not in seen:
                seen.add(title)
                unique_sources.append((title, uri))
        unique_sources = unique_sources[:15]

        source_lines = []
        for idx, (title, uri) in enumerate(unique_sources, 1):
            source_lines.append(f"{idx}. [{title}]({uri})")

        source_text = "\n\n---\n\n**🔗 本期信息来源**\n" + "\n".join(source_lines)
        report_text += source_text

    return report_text, week_num, week_range


def send_to_feishu(report, week_num, week_range):
    beijing_tz = timezone(timedelta(hours=8))
    now_beijing = datetime.now(beijing_tz).strftime('%Y-%m-%d %H:%M')
    max_len = 2800
    chunks = [report[i:i+max_len] for i in range(0, len(report), max_len)]
    total = len(chunks)

    for i, chunk in enumerate(chunks):
        if total > 1:
            title = f"🎙️ 娱乐直播竞品周报 · {week_num}（{i+1}/{total}）"
        else:
            title = f"🎙️ 娱乐直播竞品周报 · {week_num}"

        payload = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"tag": "plain_text", "content": title},
                    "template": "purple"
                },
                "elements": [
                    {
                        "tag": "markdown",
                        "content": f"**统计周期：{week_range}**\n\n{chunk}"
                    },
                    {"tag": "hr"},
                    {
                        "tag": "note",
                        "elements": [
                            {
                                "tag": "plain_text",
                                "content": f"🤖 Gemini 2.5 Pro + Google Search 实时生成 · {now_beijing} (北京时间)"
                            }
                        ]
                    }
                ]
            }
        }
        resp = requests.post(FEISHU_WEBHOOK, json=payload)
        print(f"第{i+1}段推送结果：{resp.json()}")

        if total > 1:
            import time
            time.sleep(1)


def main():
    print("🚀 开始生成娱乐直播竞品周报（含实时搜索）...")
    report, week_num, week_range = generate_report()
    print(f"✅ 报告生成完成，共 {len(report)} 字")
    send_to_feishu(report, week_num, week_range)
    print("📱 飞书推送完成！")


if __name__ == "__main__":
    main()
