#!/usr/bin/env python3
"""Render the first sales demo video and teaser from live bitcoinsapi.com surfaces."""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import textwrap
import wave
from dataclasses import dataclass
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFilter, ImageFont


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "output" / "sales-demo-video"
BASE_URL = "https://bitcoinsapi.com"
SIZE = (1280, 720)
FPS = 30

COLORS = {
    "bg": "#0c1117",
    "surface": "#131a23",
    "surface_alt": "#182130",
    "border": "#263446",
    "text": "#f5f7fa",
    "muted": "#9fb0c0",
    "accent": "#f7931a",
    "green": "#37c978",
    "red": "#ff7676",
    "blue": "#79b7ff",
    "yellow": "#ffd166",
    "code_bg": "#0b1220",
}

FONT_PATHS = {
    "regular": Path("C:/Windows/Fonts/segoeui.ttf"),
    "bold": Path("C:/Windows/Fonts/segoeuib.ttf"),
    "mono": Path("C:/Windows/Fonts/consola.ttf"),
}

LOGO_PATH = REPO_ROOT / "static" / "logo-128.png"


@dataclass
class Scene:
    slug: str
    title: str
    caption: str
    voiceover: str


FULL_SCENES = [
    Scene(
        slug="problem",
        title="Problem",
        caption="Problem: fee rate is not the decision",
        voiceover=(
            "If you run a Bitcoin payout or withdrawal flow, the expensive question is not "
            '"what is the fee rate?" It is "should we send now or wait?"'
        ),
    ),
    Scene(
        slug="proof",
        title="Proof Case",
        caption="Proof: 14,563 sats vs 3,451 sats",
        voiceover=(
            "Here is the fixed proof case I use in every demo. On March 19, 2026 at 1:54 PM Eastern, "
            "this merchant payout batch would have cost 14,563 sats to send. Waiting until the next "
            "morning fee window dropped that to 3,451 sats. That is 11,112 sats saved, or 76.3 percent, "
            "from one timing decision."
        ),
    ),
    Scene(
        slug="planner",
        title="Live Planner",
        caption="Live path: /api/v1/fees/plan",
        voiceover=(
            "This is the hosted response shape a product would call right now. It gives a recommendation, "
            "the reasoning, fee tiers, and the savings from waiting. This is the default free demo path."
        ),
    ),
    Scene(
        slug="integration",
        title="Integration",
        caption="Pilot path: one curl request",
        voiceover=(
            "And this is the exact curl request your engineer would paste into a service today."
        ),
    ),
    Scene(
        slug="mcp",
        title="Agent Path",
        caption='Agent path: plan_transaction(profile="merchant_payout_batch")',
        voiceover=(
            "If your team prefers agent workflows, the MCP setup page leads with the same planner call "
            "through plan_transaction."
        ),
    ),
    Scene(
        slug="x402",
        title="Premium Finish",
        caption="Optional premium: x402",
        voiceover=(
            "If you want deeper one-shot analysis later, that is where x402 fits. But the first touch is "
            "the free planner."
        ),
    ),
    Scene(
        slug="close",
        title="Pilot Ask",
        caption="Pilot ask: one real send flow",
        voiceover=(
            "If this fits your send or payout flow, the next step is simple: let's wire it into one real "
            "path and review usage after a week."
        ),
    ),
]

TEASER_SCENES = [
    Scene(
        slug="teaser-proof",
        title="Proof",
        caption="14,563 sats -> 3,451 sats",
        voiceover=(
            "One Bitcoin payout batch. Same transaction shape. Send on March 19, 2026: 14,563 sats. "
            "Wait until the next morning: 3,451 sats."
        ),
    ),
    Scene(
        slug="teaser-planner",
        title="Planner",
        caption="Live path: /api/v1/fees/plan",
        voiceover=(
            "That is what fee intelligence is supposed to do. Show the proof case, then give you a live "
            "send now or wait path."
        ),
    ),
    Scene(
        slug="teaser-close",
        title="Close",
        caption="See if you should send now or wait",
        voiceover="Use the hosted planner to check your own send now or wait decision.",
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for generated slides, audio, and final videos.",
    )
    parser.add_argument(
        "--voice",
        default="Microsoft Zira Desktop",
        help="Installed Windows voice to use for narration.",
    )
    parser.add_argument(
        "--base-url",
        default=BASE_URL,
        help="Base URL to capture and query.",
    )
    parser.add_argument(
        "--keep-captures",
        action="store_true",
        help="Keep existing screenshots instead of recapturing them.",
    )
    return parser.parse_args()


def load_font(name: str, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    path = FONT_PATHS[name]
    if path.exists():
        return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def ensure_dirs(root: Path) -> dict[str, Path]:
    parts = {
        "captures": root / "captures",
        "slides": root / "slides",
        "audio": root / "audio",
        "segments": root / "segments",
        "meta": root / "meta",
    }
    root.mkdir(parents=True, exist_ok=True)
    for path in parts.values():
        path.mkdir(parents=True, exist_ok=True)
    return parts


def run(cmd: list[str], cwd: Path | None = None) -> None:
    executable = shutil.which(cmd[0]) or shutil.which(f"{cmd[0]}.cmd") or cmd[0]
    subprocess.run([executable, *cmd[1:]], check=True, cwd=cwd)


def capture_page(url: str, out_path: Path, *, viewport: str = "1440,900", full_page: bool = False, wait_ms: int = 3000) -> None:
    cmd = [
        "npx",
        "playwright",
        "screenshot",
        "--browser",
        "chromium",
        "--viewport-size",
        viewport,
        "--wait-for-timeout",
        str(wait_ms),
        "--block-service-workers",
    ]
    if full_page:
        cmd.append("--full-page")
    cmd.extend([url, str(out_path)])
    run(cmd, cwd=REPO_ROOT)


def get_json(url: str, *, allow_error_json: bool = False) -> dict:
    resp = requests.get(url, timeout=30)
    if not allow_error_json:
        resp.raise_for_status()
    return resp.json()


def pretty_json_snippet(data: dict, limit_lines: int = 16) -> str:
    text = json.dumps(data, indent=2)
    lines = text.splitlines()
    if len(lines) > limit_lines:
        lines = lines[: limit_lines - 1] + ["  ..."]
    return "\n".join(lines)


def create_canvas() -> Image.Image:
    return Image.new("RGB", SIZE, COLORS["bg"])


def draw_logo(draw: ImageDraw.ImageDraw, canvas: Image.Image) -> None:
    if LOGO_PATH.exists():
        logo = Image.open(LOGO_PATH).convert("RGBA").resize((54, 54))
        canvas.alpha_composite(logo, (54, 36))
    font = load_font("bold", 24)
    draw.text((120, 46), "Satoshi API", fill=COLORS["text"], font=font)


def fit_cover(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    target_w, target_h = size
    src_w, src_h = image.size
    scale = max(target_w / src_w, target_h / src_h)
    new_size = (int(src_w * scale), int(src_h * scale))
    resized = image.resize(new_size, Image.Resampling.LANCZOS)
    left = (resized.width - target_w) // 2
    top = (resized.height - target_h) // 2
    return resized.crop((left, top, left + target_w, top + target_h))


def fit_contain(image: Image.Image, size: tuple[int, int], background: str) -> Image.Image:
    target_w, target_h = size
    src_w, src_h = image.size
    scale = min(target_w / src_w, target_h / src_h)
    new_size = (max(1, int(src_w * scale)), max(1, int(src_h * scale)))
    resized = image.resize(new_size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, background)
    left = (target_w - resized.width) // 2
    top = (target_h - resized.height) // 2
    canvas.paste(resized, (left, top))
    return canvas


def rounded_panel(draw: ImageDraw.ImageDraw, xy: tuple[int, int, int, int], fill: str, outline: str | None = None, radius: int = 28) -> None:
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=2 if outline else 1)


def wrap_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        test = word if not current else f"{current} {word}"
        if draw.textbbox((0, 0), test, font=font)[2] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_wrapped(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, fill: str, box: tuple[int, int, int, int], line_spacing: int = 8) -> int:
    x0, y0, x1, _ = box
    lines = wrap_text(draw, text, font, x1 - x0)
    y = y0
    for line in lines:
        draw.text((x0, y), line, fill=fill, font=font)
        y += font.size + line_spacing
    return y


def draw_code_block(draw: ImageDraw.ImageDraw, code: str, *, x: int, y: int, w: int, h: int) -> None:
    rounded_panel(draw, (x, y, x + w, y + h), fill=COLORS["code_bg"], outline=COLORS["border"], radius=24)
    mono = load_font("mono", 24)
    line_y = y + 26
    for raw_line in code.splitlines():
        line = raw_line.rstrip()
        if line_y + mono.size > y + h - 20:
            break
        fill = COLORS["text"]
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("#"):
            fill = COLORS["muted"]
        elif '"recommendation"' in line or '"reasoning"' in line or "curl " in line:
            fill = COLORS["accent"]
        elif '"paymentRequirements"' in line or "402" in line:
            fill = COLORS["yellow"]
        draw.text((x + 24, line_y), line, fill=fill, font=mono)
        line_y += mono.size + 8


def add_caption_pill(draw: ImageDraw.ImageDraw, text: str) -> None:
    font = load_font("bold", 22)
    width = draw.textbbox((0, 0), text, font=font)[2] + 44
    height = 52
    x = SIZE[0] - width - 54
    y = SIZE[1] - height - 42
    rounded_panel(draw, (x, y, x + width, y + height), fill=COLORS["surface_alt"], outline=COLORS["accent"], radius=20)
    draw.text((x + 22, y + 12), text, fill=COLORS["text"], font=font)


def build_problem_slide(out_path: Path, screenshot: Path, scene: Scene) -> None:
    base = Image.open(screenshot).convert("RGB")
    hero = fit_cover(base, SIZE).filter(ImageFilter.GaussianBlur(radius=1.2))
    overlay = Image.new("RGBA", SIZE, (6, 9, 13, 165))
    canvas = Image.alpha_composite(hero.convert("RGBA"), overlay)
    draw = ImageDraw.Draw(canvas)
    draw_logo(draw, canvas)
    tag_font = load_font("bold", 22)
    rounded_panel(draw, (86, 120, 316, 168), fill=COLORS["surface_alt"], outline=COLORS["border"], radius=18)
    draw.text((112, 132), "Buyer: payout CTO", fill=COLORS["accent"], font=tag_font)
    title_font = load_font("bold", 64)
    body_font = load_font("regular", 30)
    draw_wrapped(
        draw,
        "The fee rate is data. The real product question is whether to send the batch now or wait.",
        title_font,
        COLORS["text"],
        (86, 212, 1120, 440),
        line_spacing=12,
    )
    draw_wrapped(
        draw,
        "The live proof page is the opener. The story is a merchant payout operator who wants the cheapest safe send window.",
        body_font,
        COLORS["muted"],
        (92, 470, 1080, 610),
        line_spacing=10,
    )
    add_caption_pill(draw, scene.caption)
    canvas.convert("RGB").save(out_path, quality=95)


def build_proof_slide(out_path: Path, scenario: dict, scene: Scene) -> None:
    canvas = create_canvas().convert("RGBA")
    draw = ImageDraw.Draw(canvas)
    draw_logo(draw, canvas)
    title_font = load_font("bold", 54)
    body_font = load_font("regular", 24)
    card_label = load_font("bold", 18)
    card_value = load_font("bold", 38)
    draw.text((86, 120), "Fixed Proof Story", fill=COLORS["accent"], font=title_font)
    draw_wrapped(
        draw,
        "One merchant payout batch. Same transaction shape. Two fee windows. One clear answer.",
        body_font,
        COLORS["muted"],
        (90, 190, 1140, 270),
    )

    cards = [
        ("Send on March 19, 2026", "14,563 sats", COLORS["red"]),
        ("Wait until March 20, 2026", "3,451 sats", COLORS["green"]),
        ("Savings", "11,112 sats", COLORS["accent"]),
        ("Percent saved", "76.3%", COLORS["blue"]),
    ]
    positions = [(86, 300), (676, 300), (86, 470), (676, 470)]
    for (label, value, color), (x, y) in zip(cards, positions, strict=True):
        rounded_panel(draw, (x, y, x + 518, y + 132), fill=COLORS["surface"], outline=color, radius=28)
        draw.text((x + 28, y + 26), label, fill=COLORS["muted"], font=card_label)
        draw.text((x + 28, y + 58), value, fill=color, font=card_value)

    tx = scenario["transaction"]
    detail = (
        f'Profile: {tx["profile"]} | {tx["inputs"]} inputs | {tx["outputs"]} outputs | '
        f'{tx["estimated_vsize"]:,} vB | {tx["address_type"]}'
    )
    draw_wrapped(draw, detail, body_font, COLORS["text"], (90, 642, 1160, 700))
    add_caption_pill(draw, scene.caption)
    canvas.convert("RGB").save(out_path, quality=95)


def build_planner_slide(out_path: Path, planner: dict, scene: Scene) -> None:
    canvas = create_canvas().convert("RGBA")
    draw = ImageDraw.Draw(canvas)
    draw_logo(draw, canvas)
    title_font = load_font("bold", 52)
    body_font = load_font("regular", 24)
    draw.text((86, 112), "Live Planner Response", fill=COLORS["accent"], font=title_font)
    subtitle = "This uses the live hosted endpoint from production right now."
    draw.text((90, 178), subtitle, fill=COLORS["muted"], font=body_font)
    callout = {
        "profile": planner["profile"],
        "recommendation": planner["recommendation"],
        "reasoning": planner["reasoning"],
        "delay_savings_pct": planner["delay_savings_pct"],
        "btc_price_usd": planner.get("btc_price_usd"),
        "estimated_vsize": planner["transaction"]["estimated_vsize"],
        "immediate_fee_sats": planner["cost_tiers"]["immediate"]["total_fee_sats"],
    }
    draw_code_block(draw, pretty_json_snippet(callout, limit_lines=12), x=86, y=236, w=1110, h=348)
    summary = (
        f'Current verdict: {planner["recommendation"].upper()} | '
        f'Immediate fee: {planner["cost_tiers"]["immediate"]["total_fee_sats"]:,} sats | '
        f'Current fee rate: {planner["cost_tiers"]["immediate"]["fee_rate_sat_vb"]} sat/vB'
    )
    draw_wrapped(draw, summary, body_font, COLORS["text"], (90, 616, 1160, 678))
    add_caption_pill(draw, scene.caption)
    canvas.convert("RGB").save(out_path, quality=95)


def build_integration_slide(out_path: Path, curl_command: str, scene: Scene) -> None:
    canvas = create_canvas().convert("RGBA")
    draw = ImageDraw.Draw(canvas)
    draw_logo(draw, canvas)
    title_font = load_font("bold", 52)
    body_font = load_font("regular", 24)
    draw.text((86, 112), "Engineer Copy/Paste Path", fill=COLORS["accent"], font=title_font)
    draw_wrapped(
        draw,
        "The guide endpoint hands the team the exact production curl call. No product-specific SDK work is required for a first pilot.",
        body_font,
        COLORS["muted"],
        (90, 178, 1160, 272),
    )
    draw_code_block(draw, curl_command, x=86, y=286, w=1110, h=220)
    bullets = [
        "Paste into a service, job runner, or payout worker",
        "Swap the transaction shape later if the pilot needs it",
        "Keep the first trial focused on one real send path",
    ]
    bullet_font = load_font("regular", 24)
    y = 546
    for bullet in bullets:
        draw.text((102, y), f"• {bullet}", fill=COLORS["text"], font=bullet_font)
        y += 44
    add_caption_pill(draw, scene.caption)
    canvas.convert("RGB").save(out_path, quality=95)


def build_mcp_slide(out_path: Path, screenshot: Path, scene: Scene) -> None:
    canvas = create_canvas().convert("RGBA")
    draw = ImageDraw.Draw(canvas)
    draw_logo(draw, canvas)
    title_font = load_font("bold", 50)
    body_font = load_font("regular", 24)
    draw.text((86, 104), "MCP and Agent Path", fill=COLORS["accent"], font=title_font)
    draw_wrapped(
        draw,
        "The hosted planner story carries through to agents. The same flow is exposed as plan_transaction(profile=\"merchant_payout_batch\").",
        body_font,
        COLORS["muted"],
        (90, 170, 1180, 250),
    )

    full = Image.open(screenshot).convert("RGB")
    focus = full.crop((0, 0, full.width, min(full.height, 3600)))
    panel = fit_contain(focus, (470, 400), COLORS["code_bg"])
    canvas.alpha_composite(panel.convert("RGBA"), (86, 276))
    rounded_panel(draw, (86, 276, 556, 676), fill=(0, 0, 0, 0), outline=COLORS["border"], radius=28)
    draw_code_block(
        draw,
        '\n'.join(
            [
                '# agent prompt',
                '"Should I send this merchant payout batch now or wait?"',
                "",
                '# tool call',
                'plan_transaction(profile="merchant_payout_batch")',
                "",
                "# output",
                '"Wait when the urgency premium is high,',
                'send when the spread is tight."',
            ]
        ),
        x=612,
        y=286,
        w=584,
        h=308,
    )
    draw_wrapped(
        draw,
        "This is the cleanest handoff for AI tools, Claude, or internal agents that need a Bitcoin send-now-or-wait tool without building the logic from scratch.",
        body_font,
        COLORS["text"],
        (612, 620, 1180, 692),
    )
    add_caption_pill(draw, scene.caption)
    canvas.convert("RGB").save(out_path, quality=95)


def build_x402_slide(out_path: Path, x402_body: dict, scene: Scene) -> None:
    canvas = create_canvas().convert("RGBA")
    draw = ImageDraw.Draw(canvas)
    draw_logo(draw, canvas)
    title_font = load_font("bold", 50)
    body_font = load_font("regular", 24)
    draw.text((86, 112), "Premium Lane After the Free Planner", fill=COLORS["accent"], font=title_font)
    draw_wrapped(
        draw,
        "The x402 finish is there when a prospect wants deeper one-shot analysis without a signup step. It is a premium lane, not the first touch.",
        body_font,
        COLORS["muted"],
        (90, 178, 1180, 250),
    )
    snippet = {
        "status": x402_body.get("error", {}).get("status"),
        "title": x402_body.get("error", {}).get("title"),
        "resource": x402_body.get("paymentRequirements", {}).get("resource"),
        "maxAmountRequired": x402_body.get("paymentRequirements", {}).get("maxAmountRequired"),
        "network": x402_body.get("paymentRequirements", {}).get("network"),
    }
    draw_code_block(draw, pretty_json_snippet(snippet, limit_lines=10), x=86, y=286, w=1110, h=258)
    draw_wrapped(
        draw,
        "That lets the sales call stay grounded in a free proof flow while still ending with a credible premium monetization story.",
        body_font,
        COLORS["text"],
        (90, 580, 1160, 660),
    )
    add_caption_pill(draw, scene.caption)
    canvas.convert("RGB").save(out_path, quality=95)


def build_close_slide(out_path: Path, scene: Scene) -> None:
    canvas = create_canvas().convert("RGBA")
    draw = ImageDraw.Draw(canvas)
    draw_logo(draw, canvas)
    title_font = load_font("bold", 58)
    body_font = load_font("regular", 28)
    draw.text((86, 150), "One Real Pilot Ask", fill=COLORS["accent"], font=title_font)
    draw_wrapped(
        draw,
        "If this matches a send or payout flow, wire it into one real path, watch the verdict for a week, and decide from usage instead of guesses.",
        body_font,
        COLORS["text"],
        (90, 236, 1120, 340),
        line_spacing=10,
    )
    steps = [
        "1. Pick one send, withdrawal, or payout job.",
        "2. Call the hosted planner before broadcast.",
        "3. Review savings, operator trust, and repeat usage after one week.",
    ]
    y = 404
    for step in steps:
        rounded_panel(draw, (86, y, 1100, y + 74), fill=COLORS["surface"], outline=COLORS["border"], radius=20)
        draw.text((112, y + 20), step, fill=COLORS["text"], font=body_font)
        y += 92
    add_caption_pill(draw, scene.caption)
    canvas.convert("RGB").save(out_path, quality=95)


def build_teaser_proof_slide(out_path: Path, scenario: dict, scene: Scene) -> None:
    canvas = create_canvas().convert("RGBA")
    draw = ImageDraw.Draw(canvas)
    draw_logo(draw, canvas)
    title_font = load_font("bold", 58)
    value_font = load_font("bold", 60)
    body_font = load_font("regular", 24)
    draw.text((86, 120), "Same payout batch. Different fee window.", fill=COLORS["text"], font=title_font)
    rounded_panel(draw, (86, 290, 556, 470), fill=COLORS["surface"], outline=COLORS["red"], radius=28)
    rounded_panel(draw, (632, 290, 1102, 470), fill=COLORS["surface"], outline=COLORS["green"], radius=28)
    draw.text((118, 326), "March 19, 2026", fill=COLORS["muted"], font=body_font)
    draw.text((118, 366), "14,563 sats", fill=COLORS["red"], font=value_font)
    draw.text((664, 326), "March 20, 2026", fill=COLORS["muted"], font=body_font)
    draw.text((664, 366), "3,451 sats", fill=COLORS["green"], font=value_font)
    draw.text((86, 552), "76.3% saved by waiting for the next fee window.", fill=COLORS["accent"], font=load_font("bold", 34))
    add_caption_pill(draw, scene.caption)
    canvas.convert("RGB").save(out_path, quality=95)


def build_teaser_planner_slide(out_path: Path, planner: dict, scene: Scene) -> None:
    canvas = create_canvas().convert("RGBA")
    draw = ImageDraw.Draw(canvas)
    draw_logo(draw, canvas)
    draw.text((86, 116), "Hosted live path", fill=COLORS["accent"], font=load_font("bold", 54))
    draw_code_block(
        draw,
        '\n'.join(
            [
                'GET /api/v1/fees/plan?profile=merchant_payout_batch&currency=usd',
                "",
                f'recommendation: "{planner["recommendation"]}"',
                f'profile: "{planner["profile"]}"',
                f'immediate_fee_sats: {planner["cost_tiers"]["immediate"]["total_fee_sats"]}',
            ]
        ),
        x=86,
        y=250,
        w=1110,
        h=260,
    )
    draw_wrapped(
        draw,
        "Show the proof story, then give teams one live endpoint they can test immediately.",
        load_font("regular", 28),
        COLORS["text"],
        (90, 560, 1150, 640),
    )
    add_caption_pill(draw, scene.caption)
    canvas.convert("RGB").save(out_path, quality=95)


def build_teaser_close_slide(out_path: Path, scene: Scene) -> None:
    canvas = create_canvas().convert("RGBA")
    draw = ImageDraw.Draw(canvas)
    draw_logo(draw, canvas)
    draw.text((86, 178), "See if you should send now or wait.", fill=COLORS["text"], font=load_font("bold", 62))
    draw.text((90, 292), "bitcoinsapi.com/best-time-to-send-bitcoin", fill=COLORS["accent"], font=load_font("bold", 34))
    draw.text((90, 350), "bitcoinsapi.com/fees", fill=COLORS["text"], font=load_font("regular", 30))
    add_caption_pill(draw, scene.caption)
    canvas.convert("RGB").save(out_path, quality=95)


def save_voice_text(audio_dir: Path, slug: str, voiceover: str) -> Path:
    path = audio_dir / f"{slug}.txt"
    path.write_text(voiceover, encoding="utf-8")
    return path


def synthesize_voice(text_path: Path, wav_path: Path, voice: str) -> None:
    command = f"""
Add-Type -AssemblyName System.Speech
$text = Get-Content -Raw '{text_path.as_posix()}'
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.SelectVoice('{voice}')
$synth.Rate = -1
$synth.Volume = 100
$synth.SetOutputToWaveFile('{wav_path.as_posix()}')
$synth.Speak($text)
$synth.Dispose()
"""
    run(["powershell", "-NoProfile", "-Command", command])


def wav_duration_seconds(path: Path) -> float:
    with wave.open(str(path), "rb") as handle:
        return handle.getnframes() / float(handle.getframerate())


def render_segment(image_path: Path, audio_path: Path, out_path: Path) -> float:
    duration = wav_duration_seconds(audio_path) + 0.4
    fade_out = max(duration - 0.35, 0.1)
    filter_complex = (
        "[0:v]format=yuv420p,"
        f"fade=t=in:st=0:d=0.25,fade=t=out:st={fade_out:.2f}:d=0.25[v];"
        f"[1:a]afade=t=in:st=0:d=0.15,afade=t=out:st={fade_out:.2f}:d=0.25[a]"
    )
    run(
        [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            str(image_path),
            "-i",
            str(audio_path),
            "-filter_complex",
            filter_complex,
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-t",
            f"{duration:.2f}",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(FPS),
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            str(out_path),
        ]
    )
    return duration


def concat_segments(segment_paths: list[Path], out_path: Path) -> None:
    concat_file = out_path.with_suffix(".concat.txt")
    concat_file.write_text("\n".join(f"file '{p.as_posix()}'" for p in segment_paths), encoding="utf-8")
    run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-c",
            "copy",
            str(out_path),
        ]
    )


def write_srt(scene_defs: list[Scene], durations: list[float], out_path: Path) -> None:
    def fmt(seconds: float) -> str:
        millis = int(round(seconds * 1000))
        hours, rem = divmod(millis, 3_600_000)
        minutes, rem = divmod(rem, 60_000)
        secs, ms = divmod(rem, 1000)
        return f"{hours:02}:{minutes:02}:{secs:02},{ms:03}"

    start = 0.0
    chunks = []
    for idx, (scene, duration) in enumerate(zip(scene_defs, durations, strict=True), start=1):
        end = start + max(duration - 0.05, 0.1)
        chunks.append(
            "\n".join(
                [
                    str(idx),
                    f"{fmt(start)} --> {fmt(end)}",
                    textwrap.fill(scene.voiceover, width=62),
                    "",
                ]
            )
        )
        start += duration
    out_path.write_text("\n".join(chunks), encoding="utf-8")


def build_manifest(out_path: Path, planner: dict, scenario: dict) -> None:
    output_dir = out_path.parent.parent
    manifest = {
        "base_url": BASE_URL,
        "planner_profile": planner["profile"],
        "planner_recommendation": planner["recommendation"],
        "scenario_slug": scenario["slug"],
        "scenario_recommendation": scenario["decision"]["recommendation"],
        "scenario_wait_until_utc": scenario["decision"]["wait_until_utc"],
        "generated_files": sorted(p.name for p in output_dir.iterdir()),
    }
    out_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir
    paths = ensure_dirs(output_dir)

    proof_url = f"{args.base_url}/best-time-to-send-bitcoin"
    mcp_url = f"{args.base_url}/mcp-setup"
    planner_url = f"{args.base_url}/api/v1/fees/plan?profile=merchant_payout_batch&currency=usd"
    scenario_url = f"{args.base_url}/api/v1/fees/scenarios/merchant-payout-batch-march-2026"
    guide_url = f"{args.base_url}/api/v1/guide?use_case=fees&lang=curl"
    x402_url = f"{args.base_url}/api/v1/fees/landscape"

    proof_capture = paths["captures"] / "proof-page.png"
    mcp_capture = paths["captures"] / "mcp-setup-full.png"
    if not args.keep_captures or not proof_capture.exists():
        capture_page(proof_url, proof_capture, viewport="1440,900")
    if not args.keep_captures or not mcp_capture.exists():
        capture_page(mcp_url, mcp_capture, viewport="1440,1000", full_page=True)

    planner = get_json(planner_url)["data"]
    scenario = get_json(scenario_url)["data"]
    guide = get_json(guide_url)["data"]
    x402 = get_json(x402_url, allow_error_json=True)

    curl_command = guide["quickstart"][2]["examples"]["curl"]

    slide_builders = {
        "problem": lambda path, scene: build_problem_slide(path, proof_capture, scene),
        "proof": lambda path, scene: build_proof_slide(path, scenario, scene),
        "planner": lambda path, scene: build_planner_slide(path, planner, scene),
        "integration": lambda path, scene: build_integration_slide(path, curl_command, scene),
        "mcp": lambda path, scene: build_mcp_slide(path, mcp_capture, scene),
        "x402": lambda path, scene: build_x402_slide(path, x402, scene),
        "close": lambda path, scene: build_close_slide(path, scene),
        "teaser-proof": lambda path, scene: build_teaser_proof_slide(path, scenario, scene),
        "teaser-planner": lambda path, scene: build_teaser_planner_slide(path, planner, scene),
        "teaser-close": lambda path, scene: build_teaser_close_slide(path, scene),
    }

    outputs: dict[str, Path] = {}
    for variant, scenes in {"full": FULL_SCENES, "teaser": TEASER_SCENES}.items():
        segment_paths: list[Path] = []
        durations: list[float] = []
        for scene in scenes:
            slide_path = paths["slides"] / f"{variant}-{scene.slug}.png"
            audio_text = save_voice_text(paths["audio"], f"{variant}-{scene.slug}", scene.voiceover)
            audio_path = paths["audio"] / f"{variant}-{scene.slug}.wav"
            segment_path = paths["segments"] / f"{variant}-{scene.slug}.mp4"
            slide_builders[scene.slug](slide_path, scene)
            synthesize_voice(audio_text, audio_path, args.voice)
            durations.append(render_segment(slide_path, audio_path, segment_path))
            segment_paths.append(segment_path)

        video_path = output_dir / f"bitcoinsapi-sales-demo-{variant}.mp4"
        srt_path = output_dir / f"bitcoinsapi-sales-demo-{variant}.srt"
        concat_segments(segment_paths, video_path)
        write_srt(scenes, durations, srt_path)
        outputs[variant] = video_path

    build_manifest(paths["meta"] / "manifest.json", planner, scenario)
    print("Rendered assets:")
    for variant, path in outputs.items():
        print(f"- {variant}: {path}")


if __name__ == "__main__":
    main()
