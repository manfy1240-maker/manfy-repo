import google.generativeai as genai
import requests
import os
from datetime import datetime, timedelta

GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
FEISHU_WEBHOOK = os.environ["FEISHU_WEBHOOK"]

PLATFORMS = [
    "抖音直播", "快手直播", "B站直播", "小红书直播",
    "微信视频号直播", "虎牙直播", "YY直播", "荔枝FM", "氧气语音"
]

def generate_report():
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')

    today = datetime.now()
    last_week = today - timedelta(days=7)
    week_range = f"{last_week.strftime('%m月%d日')}～{today.strftime('%m月%d日')}"
    week_num = today.strftime("%Y年第%W周")

    platforms_str = "、".join(PLATFORMS)

    prompt = f"""你是一位专业的娱乐直播行业分析师。

请输出【{week_num}（{week_range}）娱乐直播平台竞品周报】

调研平台：{platforms_str}

严格按照以下结构输出报告，每个模块都必须覆盖所有相关平台：

---

## 一、🆕 新功能动态速览
分平台列出过去一周各平台上线或测试的新功能，包括：直播间互动功能、推流工具、主播端工具、观众端体验升级等。
格式：
**平台名**：具体功能描述

---

## 二、💰 营收玩法与功能最新动态
重点梳理各平台在以下方向的最新动作：
- 打赏/礼物系统更新（新礼物、连击玩法、排行榜等）
- 付费订阅/会员体系变化
- 电商带货/直播购物新机制
- 主播分成/激励政策调整
- 商业化新产品或广告变现方式

格式：
**平台名**：具体营收动态描述

---

## 三、🤖 AI × 直播 最新进展
聚焦各平台在以下方向的AI应用落地：
- AI虚拟主播/数字人直播
- AI实时翻译/字幕
- AI内容审核与风控
- AI推荐算法优化
- AI辅助互动（智能弹幕、AI礼物推荐等）
- AIGC内容生成工具

格式：
**平台名**：具体AI进展描述

---

## 四、📊 本周竞争格局小结
用2-3段话总结：
1. 本周哪些平台动作最积极？有何战略意图？
2. 各平台在营收和AI方向上的差异化路线
3. 值得重点关注的行业趋势信号

---

## 五、⚡ 下周重点关注事项
列出3-5条下周需跟进的具体事项或预期动向

---

输出要求：
- 语言专业简洁，适合企业内部报告
- 如某平台本周无明显动态，注明"本周暂无重大更新"
- 重要信息加粗标注
"""

    response = model.generate_content(prompt)
    return response.text, week_num, week_range

def send_to_feishu(report, week_num, week_range):
    # 飞书卡片有字数限制，超长时分段发送
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
                        "content": f"**周期：{week_range}**\n\n{chunk}"
                    },
                    {"tag": "hr"},
                    {
                        "tag": "note",
                        "elements": [{
                            "tag": "plain_text",
                            "content": f"🤖 由 Gemini AI 自动生成 · {datetime.now().strftime('%Y-%m-%d %H:%M')}"
                        }]
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
    print("🚀 开始生成娱乐直播竞品周报...")
    report, week_num, week_range = generate_report()
    print(f"✅ 报告生成完成，共 {len(report)} 字")
    send_to_feishu(report, week_num, week_range)
    print("📱 飞书推送完成！")

if __name__ == "__main__":
    main()
```

点右上角「**Commit changes**」保存。

---

**创建自动执行配置文件**

再次点「**Add file**」→「**Create new file**」→ 文件名输入：
```
.github/workflows/weekly_report.yml
