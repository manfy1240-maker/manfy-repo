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

ALL_PLATFORMS = VIDEO_PLATFORMS + VOICE_PLATFORMS


def clean_text(text):
    text = re.sub(r'\n[A-Za-z0-9+/=_\-]{30,}\n', '\n', text)
    text = re.sub(r'[A-Za-z0-9+/=]{40,}', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def md_to_html(text):
    """Markdown 转 HTML"""
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'^#{1,3}\s+(.+)$', r'<h4>\1</h4>', text, flags=re.MULTILINE)
    text = re.sub(r'^---$', '<hr>', text, flags=re.MULTILINE)
    text = re.sub(r'^\* (.+)$', r'<li>\1</li>', text, flags=re.MULTILINE)
    text = re.sub(r'^- (.+)$', r'<li>\1</li>', text, flags=re.MULTILINE)
    text = re.sub(r'^\d+\. (.+)$', r'<li>\1</li>', text, flags=re.MULTILINE)
    text = re.sub(r'\[(.+?)\]\((https?://[^\)]+)\)', r'<a href="\2" target="_blank">\1</a>', text)
    lines = text.split('\n')
    result = []
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if s.startswith('<h4>') or s.startswith('<hr>') or s.startswith('<li>'):
            result.append(s)
        else:
            result.append(f'<p>{s}</p>')
    return '\n'.join(result)


def generate_html_report(report_text, week_num, week_range, sources):
    now = datetime.now(timezone(timedelta(hours=8))).strftime('%Y年%m月%d日 %H:%M')

    # 解析各章节内容
    sections = parse_sections(report_text)

    # 生成各章节 HTML
    s1_html = render_section1(sections.get('insights', ''))
    s2_html = render_section2(sections.get('revenue', ''))
    s3_html = render_section3(sections.get('ai', ''))
    s4_html = render_section4(sections.get('features', ''))
    s5_html = render_section5(sections.get('forecast', ''))

    sources_html = ""
    if sources:
        items = "".join(f'<li><a href="{u}" target="_blank">{t}</a></li>' for t, u in sources[:15])
        sources_html = f'<div class="sources-box"><div class="sources-title">🔗 本期信息来源</div><ol>{items}</ol></div>'

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{week_num} 娱乐直播竞品周报</title>
<style>
:root{{
  --p:#6c63ff;--pd:#5a52d5;--ps:#764ba2;
  --bg:#f4f5f9;--card:#fff;--text:#2d2d2d;--light:#888;
  --border:#eaeaea;--accent:#f0eeff;--accent2:#fff8f0;
  --green:#10b981;--orange:#f59e0b;--blue:#3b82f6;--red:#ef4444;
}}
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif;background:var(--bg);color:var(--text);line-height:1.85;font-size:15px}}

/* Header */
.header{{background:linear-gradient(135deg,var(--p),var(--ps));color:#fff;padding:48px 24px 36px;text-align:center;position:relative;overflow:hidden}}
.header::before{{content:'';position:absolute;top:-60px;right:-60px;width:240px;height:240px;background:rgba(255,255,255,.06);border-radius:50%}}
.header::after{{content:'';position:absolute;bottom:-80px;left:-40px;width:280px;height:280px;background:rgba(255,255,255,.04);border-radius:50%}}
.header h1{{font-size:26px;font-weight:700;margin-bottom:8px}}
.header .period{{font-size:14px;opacity:.88;margin-bottom:14px}}
.hbadges{{display:flex;justify-content:center;gap:8px;flex-wrap:wrap;margin-bottom:16px}}
.hbadge{{background:rgba(255,255,255,.18);padding:4px 14px;border-radius:20px;font-size:12px;border:1px solid rgba(255,255,255,.25)}}
.back-btn{{display:inline-block;background:rgba(255,255,255,.15);color:#fff;padding:7px 18px;border-radius:20px;font-size:13px;text-decoration:none;border:1px solid rgba(255,255,255,.3)}}
.back-btn:hover{{background:rgba(255,255,255,.28)}}

/* 目录导航 */
.toc{{background:#fff;border-radius:14px;padding:20px 24px;margin:28px auto 0;max-width:940px;box-shadow:0 2px 12px rgba(0,0,0,.06)}}
.toc-title{{font-size:13px;font-weight:600;color:var(--light);margin-bottom:12px;text-transform:uppercase;letter-spacing:.5px}}
.toc-list{{display:flex;flex-wrap:wrap;gap:8px}}
.toc-item{{background:var(--accent);color:var(--pd);padding:5px 14px;border-radius:20px;font-size:13px;text-decoration:none;transition:background .2s}}
.toc-item:hover{{background:#e0dcff}}

/* 容器 */
.container{{max-width:940px;margin:24px auto;padding:0 18px 72px}}

/* 通用卡片 */
.card{{background:var(--card);border-radius:14px;padding:28px 32px;margin-bottom:20px;box-shadow:0 2px 14px rgba(0,0,0,.06)}}
.section-header{{display:flex;align-items:center;gap:10px;margin-bottom:20px;padding-bottom:14px;border-bottom:2px solid var(--accent)}}
.section-icon{{font-size:22px}}
.section-title{{font-size:18px;font-weight:700;color:var(--text)}}
.section-num{{background:var(--p);color:#fff;width:24px;height:24px;border-radius:50%;font-size:12px;font-weight:700;display:flex;align-items:center;justify-content:center;flex-shrink:0}}

/* 第1节：核心发现 */
.insights-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:14px}}
.insight-card{{background:var(--accent);border-radius:10px;padding:16px 18px;border-left:4px solid var(--p)}}
.insight-num{{font-size:11px;font-weight:700;color:var(--p);margin-bottom:6px;text-transform:uppercase}}
.insight-text{{font-size:14px;color:var(--text);line-height:1.7}}
.insight-text strong{{color:var(--pd)}}

/* 第2节：平台营收 */
.platform-tabs{{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:20px}}
.tab-btn{{padding:5px 14px;border-radius:20px;font-size:13px;border:1px solid var(--border);background:#fff;color:var(--light);cursor:pointer;transition:all .2s}}
.tab-btn.active{{background:var(--p);color:#fff;border-color:var(--p)}}
.platform-block{{display:none}}
.platform-block.active{{display:block}}
.platform-name-bar{{display:flex;align-items:center;gap:10px;margin-bottom:16px}}
.platform-name{{font-size:16px;font-weight:700;color:var(--text)}}
.platform-tag{{font-size:11px;padding:2px 8px;border-radius:10px}}
.tag-video{{background:#e0f2fe;color:#0369a1}}
.tag-voice{{background:#f0fdf4;color:#15803d}}

.revenue-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:10px;margin-bottom:18px}}
.rev-dim{{background:var(--bg);border-radius:8px;padding:12px 14px}}
.rev-dim-title{{font-size:11px;font-weight:600;color:var(--light);margin-bottom:6px;display:flex;align-items:center;gap:4px}}
.rev-dim-content{{font-size:13px;color:var(--text);line-height:1.6}}
.rev-dim-content strong{{color:var(--pd)}}
.no-data{{color:#bbb;font-style:italic}}

.policy-block{{background:var(--accent2);border-radius:8px;padding:14px 16px;margin-top:10px}}
.policy-title{{font-size:12px;font-weight:600;color:var(--orange);margin-bottom:8px}}
.policy-content{{font-size:13px;color:var(--text);line-height:1.7}}
.policy-content strong{{color:#d97706}}

/* 第3节：AI动态 */
.ai-category{{margin-bottom:20px}}
.ai-cat-title{{font-size:14px;font-weight:700;color:var(--text);padding:8px 14px;background:var(--accent);border-radius:8px;margin-bottom:10px;display:flex;align-items:center;gap:6px}}
.ai-items{{display:flex;flex-direction:column;gap:8px}}
.ai-item{{background:var(--bg);border-radius:8px;padding:12px 14px;border-left:3px solid var(--p)}}
.ai-platform{{font-size:11px;font-weight:700;color:var(--p);margin-bottom:4px}}
.ai-content{{font-size:13px;color:var(--text);line-height:1.6}}
.ai-content strong{{color:var(--pd)}}
.ai-source{{font-size:11px;color:var(--light);margin-top:4px}}

/* 第4节：值得借鉴 */
.feature-list{{display:flex;flex-direction:column;gap:12px}}
.feature-item{{background:var(--bg);border-radius:10px;padding:16px 18px;display:flex;gap:14px;align-items:flex-start}}
.feature-icon{{font-size:20px;flex-shrink:0;margin-top:2px}}
.feature-body{{flex:1}}
.feature-platform{{font-size:11px;font-weight:600;color:var(--p);margin-bottom:4px}}
.feature-desc{{font-size:14px;color:var(--text);line-height:1.7}}
.feature-desc strong{{color:var(--pd)}}
.feature-why{{font-size:12px;color:var(--light);margin-top:4px;font-style:italic}}

/* 第5节：趋势预测 */
.forecast-list{{display:flex;flex-direction:column;gap:10px}}
.forecast-item{{background:var(--bg);border-radius:10px;padding:14px 18px;display:flex;gap:12px;align-items:flex-start}}
.forecast-dot{{width:8px;height:8px;background:var(--p);border-radius:50%;flex-shrink:0;margin-top:7px}}
.forecast-text{{font-size:14px;color:var(--text);line-height:1.7}}
.forecast-text strong{{color:var(--pd)}}

/* 来源 */
.sources-box{{background:var(--accent);border-radius:10px;padding:18px 22px;margin-top:24px;border-left:4px solid var(--p)}}
.sources-title{{font-size:13px;font-weight:600;color:var(--pd);margin-bottom:10px}}
.sources-box ol{{padding-left:18px}}
.sources-box li{{margin:5px 0;font-size:12px;color:var(--light)}}
.sources-box a{{color:var(--p);text-decoration:none;word-break:break-all}}

/* 正文通用 */
.prose p{{margin-bottom:10px;font-size:14px;line-height:1.8}}
.prose p:empty{{display:none}}
.prose strong{{color:var(--pd);font-weight:600}}
.prose li{{margin:6px 0 6px 20px;list-style:disc;font-size:14px}}
.prose a{{color:var(--p);text-decoration:none}}
.prose h4{{font-size:14px;font-weight:700;color:var(--text);margin:14px 0 8px}}

/* 底部 */
.footer{{text-align:center;color:var(--light);font-size:12px;margin-top:20px}}

@media(max-width:600px){{
  .card{{padding:20px 16px}}
  .insights-grid{{grid-template-columns:1fr}}
  .revenue-grid{{grid-template-columns:1fr}}
  .header h1{{font-size:22px}}
}}
</style>
</head>
<body>

<div class="header">
  <h1>🎙️ 娱乐直播竞品周报</h1>
  <div class="period">统计周期：{week_range}</div>
  <div class="hbadges">
    <span class="hbadge">🤖 Claude Sonnet 4.6</span>
    <span class="hbadge">🔍 实时搜索增强</span>
    <span class="hbadge">📊 双赛道分析</span>
  </div>
  <a class="back-btn" href="./index.html">← 历史报告列表</a>
</div>

<div class="toc" style="padding:18px 24px">
  <div class="toc-title">本期内容</div>
  <div class="toc-list">
    <a class="toc-item" href="#s1">💡 核心发现</a>
    <a class="toc-item" href="#s2">💰 平台营收动态</a>
    <a class="toc-item" href="#s3">🤖 AI融合动态</a>
    <a class="toc-item" href="#s4">⭐ 值得借鉴</a>
    <a class="toc-item" href="#s5">📈 下周趋势</a>
  </div>
</div>

<div class="container">

  <!-- 第1节 -->
  <div class="card" id="s1">
    <div class="section-header">
      <span class="section-num">1</span>
      <span class="section-icon">💡</span>
      <span class="section-title">本周核心发现</span>
    </div>
    {s1_html}
  </div>

  <!-- 第2节 -->
  <div class="card" id="s2">
    <div class="section-header">
      <span class="section-num">2</span>
      <span class="section-icon">💰</span>
      <span class="section-title">各平台营收玩法 & 公会政策</span>
    </div>
    {s2_html}
  </div>

  <!-- 第3节 -->
  <div class="card" id="s3">
    <div class="section-header">
      <span class="section-num">3</span>
      <span class="section-icon">🤖</span>
      <span class="section-title">AI 与直播深度融合动态</span>
    </div>
    {s3_html}
  </div>

  <!-- 第4节 -->
  <div class="card" id="s4">
    <div class="section-header">
      <span class="section-num">4</span>
      <span class="section-icon">⭐</span>
      <span class="section-title">值得借鉴的功能点</span>
    </div>
    {s4_html}
  </div>

  <!-- 第5节 -->
  <div class="card" id="s5">
    <div class="section-header">
      <span class="section-num">5</span>
      <span class="section-icon">📈</span>
      <span class="section-title">下周趋势预测</span>
    </div>
    {s5_html}
  </div>

  {sources_html}
  <div class="footer">生成时间：{now}（北京时间）&nbsp;·&nbsp;由 Claude Sonnet 4.6 + Web Search 自动生成，重要信息请以官方来源为准</div>
</div>

<script>
// 平台 Tab 切换
function initTabs(){{
  document.querySelectorAll('.platform-tabs').forEach(function(tabs){{
    tabs.querySelectorAll('.tab-btn').forEach(function(btn){{
      btn.addEventListener('click',function(){{
        var parent=btn.closest('.card');
        parent.querySelectorAll('.tab-btn').forEach(function(b){{b.classList.remove('active')}});
        parent.querySelectorAll('.platform-block').forEach(function(b){{b.classList.remove('active')}});
        btn.classList.add('active');
        var target=parent.querySelector('#pb-'+btn.dataset.target);
        if(target)target.classList.add('active');
      }});
    }});
  }});
}}
document.addEventListener('DOMContentLoaded',initTabs);
</script>
</body>
</html>"""


def parse_sections(text):
    """从报告文本中提取各章节内容"""
    sections = {}
    markers = {
        'insights': ['SECTION_INSIGHTS', '核心发现', '关键洞察'],
        'revenue': ['SECTION_REVENUE', '平台营收', '营收玩法'],
        'ai': ['SECTION_AI', 'AI融合', 'AI动态'],
        'features': ['SECTION_FEATURES', '值得借鉴'],
        'forecast': ['SECTION_FORECAST', '趋势预测', '下周预测'],
    }
    lines = text.split('\n')
    current = None
    buf = []
    for line in lines:
        matched = None
        for key, kws in markers.items():
            if any(kw in line for kw in kws):
                matched = key
                break
        if matched:
            if current and buf:
                sections[current] = '\n'.join(buf).strip()
            current = matched
            buf = []
        elif current:
            buf.append(line)
    if current and buf:
        sections[current] = '\n'.join(buf).strip()

    # 如果解析失败，把全文放到 insights
    if not sections:
        sections['insights'] = text
    return sections


def render_section1(text):
    if not text:
        return '<p style="color:#bbb">暂无内容</p>'
    items = []
    for i, line in enumerate([l.strip() for l in text.split('\n') if l.strip() and len(l.strip()) > 5], 1):
        line_html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line)
        line_html = re.sub(r'^[\*\-\d\.\s]+', '', line_html).strip()
        if line_html:
            items.append(f'''<div class="insight-card">
  <div class="insight-num">发现 {i}</div>
  <div class="insight-text">{line_html}</div>
</div>''')
    if not items:
        return f'<div class="prose">{md_to_html(text)}</div>'
    return f'<div class="insights-grid">{"".join(items)}</div>'


def render_section2(text):
    if not text:
        return '<p style="color:#bbb">暂无内容</p>'

    dims = ['礼物打赏', '会员订阅', '虚拟商品', '付费内容', '社交变现', '广告变现', '电商联动']
    dim_icons = ['🎁', '👑', '💎', '🔒', '💬', '📢', '🛒']

    # 按平台分割
    platform_data = {}
    current_platform = None
    buf = []

    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        # 检测平台名
        matched_platform = None
        for p in ALL_PLATFORMS:
            if p in line and ('**' in line or line.startswith(p)):
                matched_platform = p
                break
        if matched_platform:
            if current_platform and buf:
                platform_data[current_platform] = '\n'.join(buf)
            current_platform = matched_platform
            buf = [line]
        elif current_platform:
            buf.append(line)

    if current_platform and buf:
        platform_data[current_platform] = '\n'.join(buf)

    if not platform_data:
        return f'<div class="prose">{md_to_html(text)}</div>'

    # 生成 Tab
    tabs_html = '<div class="platform-tabs">'
    blocks_html = ''
    for idx, (platform, content) in enumerate(platform_data.items()):
        active = 'active' if idx == 0 else ''
        is_voice = platform in VOICE_PLATFORMS
        tag_class = 'tag-voice' if is_voice else 'tag-video'
        tag_text = '语音直播' if is_voice else '娱乐直播'
        safe_id = re.sub(r'[^\w]', '_', platform)

        tabs_html += f'<button class="tab-btn {active}" data-target="{safe_id}">{platform}</button>'

        # 提取各维度内容
        dims_html = '<div class="revenue-grid">'
        for dim, icon in zip(dims, dim_icons):
            dim_content = ''
            for line in content.split('\n'):
                if dim in line:
                    cleaned = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line)
                    cleaned = re.sub(r'^[\*\-\s]*', '', cleaned).strip()
                    dim_content = cleaned
                    break
            if not dim_content:
                dim_content = '<span class="no-data">暂无动态</span>'
            dims_html += f'''<div class="rev-dim">
  <div class="rev-dim-title">{icon} {dim}</div>
  <div class="rev-dim-content">{dim_content}</div>
</div>'''
        dims_html += '</div>'

        # 提取公会政策
        policy_content = ''
        in_policy = False
        policy_lines = []
        for line in content.split('\n'):
            if any(kw in line for kw in ['公会', '分成', '主播扶持', '主播政策']):
                in_policy = True
            if in_policy:
                policy_lines.append(line)
        if policy_lines:
            raw = ' '.join(policy_lines[:4])
            policy_content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', raw)
            policy_content = re.sub(r'^[\*\-\s]*', '', policy_content).strip()

        policy_html = ''
        if policy_content:
            policy_html = f'''<div class="policy-block">
  <div class="policy-title">🤝 主播公会扶持 & 分成政策</div>
  <div class="policy-content">{policy_content}</div>
</div>'''
        else:
            policy_html = '''<div class="policy-block">
  <div class="policy-title">🤝 主播公会扶持 & 分成政策</div>
  <div class="policy-content"><span class="no-data">本周暂无相关动态</span></div>
</div>'''

        blocks_html += f'''<div class="platform-block {active}" id="pb-{safe_id}">
  <div class="platform-name-bar">
    <span class="platform-name">{platform}</span>
    <span class="platform-tag {tag_class}">{tag_text}</span>
  </div>
  {dims_html}
  {policy_html}
</div>'''

    tabs_html += '</div>'
    return tabs_html + blocks_html


def render_section3(text):
    if not text:
        return '<p style="color:#bbb">暂无内容</p>'

    categories = [
        ('AI主播/数字人', '🧑‍💻'),
        ('AI互动玩法', '🎮'),
        ('AI内容生成', '✨'),
        ('AI运营优化', '📊'),
        ('AI数据分析', '🔬'),
    ]

    result = ''
    for cat_name, cat_icon in categories:
        items_html = ''
        in_cat = False
        cat_lines = []
        for line in text.split('\n'):
            if cat_name in line or any(kw in line for kw in [cat_name.replace('AI', '').strip()]):
                in_cat = True
                cat_lines = []
                continue
            if in_cat:
                if any(c[0] in line for c in categories if c[0] != cat_name):
                    in_cat = False
                else:
                    if line.strip():
                        cat_lines.append(line.strip())

        if cat_lines:
            for line in cat_lines[:8]:
                # 提取平台名
                platform_match = None
                for p in ALL_PLATFORMS:
                    if p in line:
                        platform_match = p
                        break
                content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line)
                content = re.sub(r'^[\*\-\s]*', '', content).strip()
                source_match = re.search(r'【来源[：:].+?】', content)
                source_html = ''
                if source_match:
                    source_html = f'<div class="ai-source">{source_match.group()}</div>'
                    content = content.replace(source_match.group(), '').strip()
                platform_html = f'<div class="ai-platform">{platform_match}</div>' if platform_match else ''
                items_html += f'''<div class="ai-item">
  {platform_html}
  <div class="ai-content">{content}</div>
  {source_html}
</div>'''
        else:
            items_html = '<div class="ai-item"><div class="ai-content no-data">本周暂无相关动态</div></div>'

        result += f'''<div class="ai-category">
  <div class="ai-cat-title">{cat_icon} {cat_name}</div>
  <div class="ai-items">{items_html}</div>
</div>'''

    if not result:
        return f'<div class="prose">{md_to_html(text)}</div>'
    return result


def render_section4(text):
    if not text:
        return '<p style="color:#bbb">暂无内容</p>'

    feature_icons = ['💡', '🚀', '🎯', '⚡', '🔥']
    items = []
    current = []
    for line in text.split('\n'):
        line = line.strip()
        if not line:
            if current:
                items.append('\n'.join(current))
                current = []
        elif re.match(r'^[\*\-\d\.]', line) and current:
            items.append('\n'.join(current))
            current = [line]
        else:
            current.append(line)
    if current:
        items.append('\n'.join(current))

    result = '<div class="feature-list">'
    for i, item in enumerate(items[:6]):
        if not item.strip():
            continue
        icon = feature_icons[i % len(feature_icons)]
        platform_match = None
        for p in ALL_PLATFORMS:
            if p in item:
                platform_match = p
                break
        content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', item)
        content = re.sub(r'^[\*\-\d\.\s]+', '', content).strip()
        platform_html = f'<div class="feature-platform">{platform_match}</div>' if platform_match else ''
        result += f'''<div class="feature-item">
  <div class="feature-icon">{icon}</div>
  <div class="feature-body">
    {platform_html}
    <div class="feature-desc">{content}</div>
  </div>
</div>'''
    result += '</div>'
    return result if items else f'<div class="prose">{md_to_html(text)}</div>'


def render_section5(text):
    if not text:
        return '<p style="color:#bbb">暂无内容</p>'

    items = []
    for line in text.split('\n'):
        line = line.strip()
        if line and len(line) > 5:
            line = re.sub(r'^[\*\-\d\.\s]+', '', line).strip()
            if line:
                items.append(line)

    if not items:
        return f'<div class="prose">{md_to_html(text)}</div>'

    result = '<div class="forecast-list">'
    for item in items[:6]:
        item_html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', item)
        result += f'''<div class="forecast-item">
  <div class="forecast-dot"></div>
  <div class="forecast-text">{item_html}</div>
</div>'''
    result += '</div>'
    return result


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
        :root{{--p:#6c63ff;--ps:#764ba2;--bg:#f4f5f9;--text:#2d2d2d;--light:#999;--accent:#f0eeff}}
        *{{margin:0;padding:0;box-sizing:border-box}}
        body{{font-family:-apple-system,BlinkMacSystemFont,'PingFang SC','Microsoft YaHei',sans-serif;background:var(--bg);color:var(--text)}}
        .header{{background:linear-gradient(135deg,var(--p),var(--ps));color:#fff;padding:52px 24px 44px;text-align:center}}
        .header h1{{font-size:28px;font-weight:700;margin-bottom:10px}}
        .header p{{font-size:14px;opacity:.85;margin-bottom:16px}}
        .header-stats{{display:flex;justify-content:center;gap:12px;flex-wrap:wrap}}
        .stat{{background:rgba(255,255,255,.15);padding:5px 16px;border-radius:20px;font-size:13px;border:1px solid rgba(255,255,255,.2)}}
        .container{{max-width:820px;margin:32px auto;padding:0 18px 72px}}
        .section-title{{font-size:15px;font-weight:600;color:#666;margin-bottom:16px}}
        .report-item{{background:#fff;border-radius:14px;padding:20px 24px;margin-bottom:12px;box-shadow:0 2px 10px rgba(0,0,0,.05);display:flex;align-items:center;justify-content:space-between;gap:16px;transition:all .2s}}
        .report-item:hover{{box-shadow:0 6px 20px rgba(108,99,255,.12);transform:translateY(-1px)}}
        .report-item.latest{{border-left:4px solid var(--p);background:linear-gradient(to right,#faf9ff,#fff)}}
        .report-info{{flex:1;min-width:0}}
        .report-title{{font-size:15px;font-weight:600;margin-bottom:5px;display:flex;align-items:center;gap:8px;flex-wrap:wrap}}
        .report-meta{{font-size:12px;color:var(--light)}}
        .latest-badge{{background:var(--p);color:#fff;font-size:11px;padding:2px 9px;border-radius:10px}}
        .issue-num{{background:var(--accent);color:var(--p);font-size:11px;padding:2px 9px;border-radius:10px}}
        .view-btn{{background:linear-gradient(135deg,var(--p),var(--ps));color:#fff;padding:8px 20px;border-radius:20px;font-size:13px;text-decoration:none;white-space:nowrap;flex-shrink:0}}
        .view-btn:hover{{opacity:.88}}
        .footer{{text-align:center;color:var(--light);font-size:12px;margin-top:32px}}
        @media(max-width:600px){{.report-item{{flex-direction:column;align-items:flex-start}}.view-btn{{align-self:flex-end}}}}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎙️ 娱乐直播竞品周报</h1>
        <p>娱乐直播 · 语音直播 · AI进展 · 每周自动更新</p>
        <div class="header-stats">
            <span class="stat">📚 共 {len(history)} 期报告</span>
            <span class="stat">🤖 Claude Sonnet 4.6</span>
            <span class="stat">🔄 每周一自动更新</span>
        </div>
    </div>
    <div class="container">
        <div class="section-title">📋 历史报告归档</div>
        {history_items}
        <div class="footer">由 Claude Sonnet 4.6 + Web Search 自动生成 · 每周一北京时间 09:00 更新</div>
    </div>
</body>
</html>"""

    index_path.write_text(index_html, encoding='utf-8')
    print(f"✅ 历史首页已更新，共 {len(history)} 期")


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
⚠️ 搜索与筛选策略（严格执行）：
1. 搜索查询词格式：'平台名' + '直播' + '{month_str}' 或 'after:{date_start}'
2. 优先采用 {last_week.strftime('%Y年%m月%d日')}～{today.strftime('%Y年%m月%d日')} 的信息；本周无动态时采用本月最新信息并加注【补录】
3. 财报数据可采用最近一期，注明财报期间
4. 每条信息注明来源，格式：【来源：XXX，日期】，无法确认日期标注"日期待核实"
5. 严格剔除电商带货、购物直播、商品推广等电商变现内容

---
娱乐直播平台：{video_str}
语音直播平台：{voice_str}

---
请严格按以下5个章节输出，每章节前必须输出对应的章节标记行：

SECTION_INSIGHTS
输出3-5条本周最重要的行业洞察，每条单独一行，以"-"开头，内容精炼有洞见，不超过80字

SECTION_REVENUE
按平台逐一分析，每个平台按以下7个维度 + 公会政策输出：
**平台名**（标注：娱乐直播/语音直播）
- 礼物打赏系统：xxx【来源：XXX，日期】
- 会员订阅体系：xxx【来源：XXX，日期】
- 虚拟商品：xxx【来源：XXX，日期】
- 付费内容：xxx【来源：XXX，日期】
- 社交变现：xxx【来源：XXX，日期】
- 广告变现：xxx【来源：XXX，日期】
- 电商联动：xxx（仅保留与娱乐直播强相关的，否则填"不适用"）
- 主播扶持政策：xxx【来源：XXX，日期】
- 公会分成政策：xxx【来源：XXX，日期】
无数据填"暂无公开数据"，无动态填"本周暂无动态"

SECTION_AI
按以下5个功能类型分类汇总所有平台的AI动态：
AI主播/数字人
- **平台名**：具体进展【来源：XXX，日期】
AI互动玩法
- **平台名**：具体进展【来源：XXX，日期】
AI内容生成
- **平台名**：具体进展【来源：XXX，日期】
AI运营优化
- **平台名**：具体进展【来源：XXX，日期】
AI数据分析
- **平台名**：具体进展【来源：XXX，日期】

SECTION_FEATURES
列出3-6个本周值得借鉴的功能点，优先从娱乐直播场景选取：
- **平台名**：功能描述（为什么值得借鉴）【来源：XXX，日期】

SECTION_FORECAST
列出3-5条下周趋势预测，每条以"-"开头，基于本周动态推断，有理有据

---
输出要求：语言专业简洁，重要数据加粗，适合企业内部阅读。"""

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=8000,
        tools=[{"type": "web_search_20250305", "name": "web_search"}],
        messages=[{"role": "user", "content": prompt}]
    )

    report_text = ""
    for block in response.content:
        if hasattr(block, 'text'):
            report_text += block.text

    report_text = clean_text(report_text)
    print(f"✅ 报告生成完成，共 {len(report_text)} 字")

    # 提取来源链接
    sources = []
    for title, uri in re.findall(r'\[([^\]]+)\]\((https?://[^\)]+)\)', report_text):
        if len(title) > 5:
            sources.append((title, uri))
    seen = set()
    unique_sources = []
    for t, u in sources:
        if t not in seen:
            seen.add(t)
            unique_sources.append((t, u))
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

    lines = [l.strip() for l in summary.split('\n') if l.strip() and 'SECTION' not in l]
    preview_lines = [l for l in lines if len(l) > 10][:5]
    preview_text = '\n'.join(
        re.sub(r'\*\*(.+?)\*\*', r'\1', l) for l in preview_lines
    ) if preview_lines else summary[:300]

    elements = [
        {
            "tag": "markdown",
            "content": f"**统计周期：{week_range}**\n\n**💡 本周核心发现**\n\n{preview_text}"
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
