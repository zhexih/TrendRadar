# coding=utf-8
"""
ljg-card 集成模块

将 TrendRadar 热点数据转化为 ljg-card 长图（-l 模具），输出 1 张 PNG。
所有热点从上到下排列，一张图看完。包含 AI 分析摘要。

输出文件命名规范：{基础名}_{YYYYMMDD_HHMMSS}.png
输出目录：reports/
绝不覆盖已存在文件。
"""

import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

SKILL_ROOT = Path(__file__).resolve().parent.parent.parent.parent / ".trae" / "skills" / "ljg-card"
CAPTURE_JS = SKILL_ROOT / "assets" / "capture.js"
LONG_TEMPLATE = SKILL_ROOT / "assets" / "long_template.html"

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent.parent.parent
REPORTS_DIR = WORKSPACE_ROOT / "reports"


def _timestamp_name(base_name: str, now: datetime, ext: str = "png") -> str:
    ts = now.strftime("%Y%m%d_%H%M%S")
    return f"{base_name}_{ts}.{ext}"


def _safe_output_path(directory: Path, filename: str) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / filename
    if not target.exists():
        return target
    stem = target.stem
    suffix = target.suffix
    counter = 1
    while target.exists():
        target = directory / f"{stem}_{counter}{suffix}"
        counter += 1
    return target


def generate_card_images(
    report_data: Dict,
    total_titles: int,
    mode: str = "current",
    *,
    get_time_func: Optional[Callable[[], datetime]] = None,
    output_dir: str = "output",
    card_config: Optional[Dict] = None,
    ai_analysis: Optional[Any] = None,
) -> List[str]:
    if card_config is None:
        card_config = {}

    now = get_time_func() if get_time_func else datetime.now()

    stats = report_data.get("stats", [])
    if not stats:
        return []

    generated_files = []

    try:
        long_path = _generate_long_card(stats, total_titles, mode, now, ai_analysis)
        if long_path:
            generated_files.append(long_path)
    except Exception as e:
        print(f"[卡片] 长图生成失败: {e}")

    return generated_files


def _extract_ai_summary(ai_analysis: Any) -> str:
    if ai_analysis is None:
        return ""
    if hasattr(ai_analysis, "core_trends") and ai_analysis.core_trends:
        return ai_analysis.core_trends.strip()
    if isinstance(ai_analysis, dict):
        return ai_analysis.get("core_trends", "").strip()
    return ""


def _extract_ai_outlook(ai_analysis: Any) -> str:
    if ai_analysis is None:
        return ""
    if hasattr(ai_analysis, "outlook_strategy") and ai_analysis.outlook_strategy:
        return ai_analysis.outlook_strategy.strip()
    if isinstance(ai_analysis, dict):
        return ai_analysis.get("outlook_strategy", "").strip()
    return ""


def _format_ai_text(text: str, max_chars: int = 300) -> str:
    if not text:
        return ""
    cleaned = text.replace("```", "").strip()
    if len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars].rstrip() + "…"
    return cleaned


def _generate_long_card(
    stats: List[Dict],
    total_titles: int,
    mode: str,
    now: datetime,
    ai_analysis: Optional[Any] = None,
) -> Optional[str]:
    template = LONG_TEMPLATE.read_text(encoding="utf-8")

    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M")
    mode_display = {"current": "实时", "incremental": "增量", "daily": "全天"}.get(mode, "")

    bg_color = "#F5F7FA"
    accent_color = "#3D5A80"

    title_block = '<div class="title-area"><h1>热点播报</h1></div>'

    body_parts = []

    body_parts.append(
        f'<p class="subtitle">{date_str} · {mode_display}模式 · {time_str} 更新 · 共 {total_titles} 条</p>'
    )
    body_parts.append('<div class="divider"></div>')

    ai_summary = _extract_ai_summary(ai_analysis)
    if ai_summary:
        formatted = _format_ai_text(ai_summary, 400)
        body_parts.append(f'<p class="highlight">{_esc(formatted)}</p>')
        body_parts.append('<div class="divider"></div>')

    for stat in stats[:10]:
        word = stat.get("word", "")
        count = stat.get("count", 0)
        titles = stat.get("titles", [])

        min_rank = 999
        for t in titles:
            ranks = t.get("ranks", [])
            if ranks:
                r = min(ranks)
                if r < min_rank:
                    min_rank = r

        rank_str = f"#{min_rank}" if min_rank < 999 else ""
        label_text = " ".join([rank_str, _esc(word)]).strip()

        body_parts.append('<div class="item">')
        body_parts.append(f'<p class="label">{label_text} · {count}条</p>')

        for t in titles[:3]:
            title_text = _esc(t.get("title", ""))
            source = _esc(t.get("source_name", ""))
            t_ranks = t.get("ranks", [])
            t_rank = f"#{min(t_ranks)}" if t_ranks else ""
            time_display = _esc(t.get("time_display", ""))

            meta_parts = [t_rank, source, time_display]
            meta_text = " · ".join(p for p in meta_parts if p)

            body_parts.append(f'<p>{title_text}<br><strong>{meta_text}</strong></p>')

        body_parts.append('</div>')

        if stat != stats[-1]:
            body_parts.append('<div class="divider"></div>')

    ai_outlook = _extract_ai_outlook(ai_analysis)
    if ai_outlook:
        formatted = _format_ai_text(ai_outlook, 300)
        body_parts.append('<div class="divider"></div>')
        body_parts.append(f'<h2>研判与策略</h2>')
        body_parts.append(f'<p>{_esc(formatted)}</p>')

    body_html = "\n".join(body_parts)

    source_line = '<span class="info-source">TrendRadar</span>'

    html = template.replace("{{BG_COLOR}}", bg_color)
    html = html.replace("{{ACCENT_COLOR}}", accent_color)
    html = html.replace("{{TITLE_BLOCK}}", title_block)
    html = html.replace("{{BODY_HTML}}", body_html)
    html = html.replace("{{SOURCE_LINE}}", source_line)
    html = html.replace('<span class="author-name"></span>', '<span class="author-name">TrendRadar</span>')

    tmp_dir = tempfile.mkdtemp(prefix="trendradar_card_")
    html_path = Path(tmp_dir) / "long_card.html"
    html_path.write_text(html, encoding="utf-8")

    png_filename = _timestamp_name("热点播报", now)
    png_path = _safe_output_path(REPORTS_DIR, png_filename)
    _capture(str(html_path), str(png_path), 1080, 800, fullpage=True)

    if png_path.exists():
        print(f"[卡片] 长图: {png_path}")
        return str(png_path)
    return None


def _capture(html_path: str, png_path: str, width: int, height: int, fullpage: bool = False) -> bool:
    if not CAPTURE_JS.exists():
        print(f"[卡片] capture.js 不存在: {CAPTURE_JS}")
        return False

    cmd = ["node", str(CAPTURE_JS), html_path, png_path, str(width), str(height)]
    if fullpage:
        cmd.append("fullpage")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            cwd=str(SKILL_ROOT),
        )
        if result.returncode == 0:
            return True
        print(f"[卡片] 截图失败: {result.stderr}")
        return False
    except FileNotFoundError:
        print("[卡片] Node.js 未安装，无法截图")
        return False
    except subprocess.TimeoutExpired:
        print("[卡片] 截图超时")
        return False


def _esc(text: str) -> str:
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))
