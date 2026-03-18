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

请通过实时搜索输出本期娱乐直播平台竞品周报。搜索时必须在每个查询词中加入明确的时间限定词（如"{today.strftime('%Y年%m月')}""近7天""本周"等），确保检索结果严格限定在统计周期内。

调研平台：{platforms_str}

⚠️ 严格要求：
1. 所有信息必须来自 {last_week.strftime('%Y年%m月%d日')} 至 {today.strftime('%Y年%m月%d日')} 期间的公开报道，请在搜索时主动加入日期限定词筛选
2. 超出该时间范围的信息一律不采用，标注"本周暂无可核实的最新动态"
3. 每条信息必须附上来源（媒体名称 + 发布日期），格式：【来源：XXX，XXXX年XX月XX日】
4. 无法找到可靠来源的内容不得编造，直接注明"未检索到可靠信息"
5. 【重要】本报告聚焦娱乐直播场景，包括：视频娱乐直播、语音直播、陪伴直播、才艺直播、游戏直播、语音房、PK直播等
6. 【重要】严格剔除以下内容，不得纳入报告：电商直播、带货直播、购物直播、商品推广、品牌合作带货、直播间购物车、直播卖货等一切与电商变现相关的内容

请按以下结构输出报告：

---

## 一、🆕 新功能动态速览
分平台列出过去一周各平台在娱乐直播场景（视频直播、语音直播等）上线或测试的新功能。
电商直播相关功能不纳入此模块。
格式：
**平台名**：具体功能描述
【来源：媒体名称，发布日期】

---

## 二、💰 娱乐直播营收玩法与功能最新动态
重点梳理各平台在娱乐直播场景下的营收动态，包括：
- 打赏/礼物系统更新（新礼物、连击玩法、排行榜等）
- 付费订阅/会员体系变化
- 语音房/PK/连麦等互动玩法的商业化更新
- 主播激励与分成政策调整
- 娱乐直播广告/品牌植入新模式
注意：电商带货、直播购物、商品佣金等内容一律不纳入本模块。
格式：
**平台名**：具体营收动态描述
【来源：媒体名称，发布日期】

---

## 三、🤖 AI × 娱乐直播 最新进展
聚焦各平台在娱乐直播场景下的AI应用落地，包括：
- AI虚拟主播/数字人娱乐直播
- AI实时音效/变声/美颜优化
- AI互动玩法（智能弹幕、AI礼物推荐、AI陪伴等）
- AI内容审核与娱乐直播风控
- AI推荐算法在娱乐内容分发上的优化
- AIGC娱乐内容生成工具
注意：AI在电商选品、商品推荐、带货场景中的应用不纳入本模块。
格式：
**平台名**：具体AI进展描述
【来源：媒体名称，发布日期】

---

## 四、📊 本周娱乐直播竞争格局小结
基于以上已核实信息，分析：
1. 本周哪些平台在娱乐直播方向动作最积极？有何战略意图？
2. 各平台在娱乐直播营收和AI方向上的差异化路线
3. 值得重点关注的娱乐直播行业趋势信号

---

## 五、⚡ 下周重点关注事项
列出3-5条下周需跟进的娱乐直播方向具体事项或预期动向

---

输出要求：语言专业简洁，适合企业内部报告，重要信息加粗标注。"""

    response = client.models.generate_content(
        model='gemini-2.5-flash',
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

    sources = []
    try:
        for candidate in response.candidates:
            if hasattr(candidate, 'grounding_metadata') and candidate.grounding_metadata:
                for chunk in candidate.grounding_metadata.grounding_chunks:
                    if hasattr(chunk, 'web') and chunk.web:
                        title = chunk.web.title if chunk.web.title else "未知来源"
                        uri = chunk.web.uri if chunk.web.uri else ""
                        if uri and "vertexaisearch" not in uri:
                            sources.append(f"- {title}：{uri}")
                        elif title and title not in [s.split("：")[0].replace("- ", "") for s in sources]:
                            sources.append(f"- {title}")
    except Exception:
        pass

    if sources:
        unique_sources = list(dict.fromkeys(sources))[:10]
        source_text = "\n\n---\n\n## 🔗 本期搜索来源（Top 10）\n" + "\n".join(unique_sources)
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
                                "content": f"🤖 Gemini AI + Google Search 实时生成 · {now_beijing} (北京时间)"
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
