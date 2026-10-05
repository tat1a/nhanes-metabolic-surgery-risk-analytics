"""Create static Power BI reference previews from processed NHANES tables."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
PROCESSED_DIR = ROOT / "data" / "processed"
ASSETS_DIR = ROOT / "assets"

W, H = 1600, 900
BG = "#F6F7FB"
INK = "#111827"
MUTED = "#667085"
NAVY = "#152238"
TEAL = "#008C8C"
BLUE = "#2F64D6"
ROSE = "#C2416B"
AMBER = "#D97706"
VIOLET = "#6D5BD0"
GREEN = "#2E7D5B"
PANEL = "#FFFFFF"
LINE = "#E5E7EB"


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        "C:/Windows/Fonts/aptos-bold.ttf" if bold else "C:/Windows/Fonts/aptos.ttf",
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


F_TITLE = font(36, True)
F_SUB = font(16)
F_CARD_LABEL = font(15, True)
F_CARD_VALUE = font(34, True)
F_SMALL = font(13)
F_AXIS = font(12)
F_CHART = font(18, True)


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def read(name: str) -> pd.DataFrame:
    return pd.read_csv(PROCESSED_DIR / name)


def panel(draw: ImageDraw.ImageDraw, xy: tuple[int, int, int, int], title: str | None = None) -> None:
    draw.rounded_rectangle(xy, radius=18, fill=PANEL, outline=LINE, width=1)
    if title:
        draw.text((xy[0] + 22, xy[1] + 18), title, fill=INK, font=F_CHART)


def card(draw: ImageDraw.ImageDraw, xy: tuple[int, int, int, int], label: str, value: str, color: str) -> None:
    x0, y0, x1, y1 = xy
    draw.rounded_rectangle(xy, radius=16, fill=PANEL, outline=LINE, width=1)
    draw.rounded_rectangle((x0, y0, x0 + 8, y1), radius=6, fill=color)
    draw.text((x0 + 24, y0 + 22), label, fill=MUTED, font=F_CARD_LABEL)
    draw.text((x0 + 24, y0 + 54), value, fill=INK, font=F_CARD_VALUE)


def header(draw: ImageDraw.ImageDraw, title: str, subtitle: str, active: str) -> None:
    draw.rectangle((0, 0, W, 86), fill=NAVY)
    draw.text((48, 23), title, fill="#FFFFFF", font=F_TITLE)
    draw.text((50, 64), subtitle, fill="#C9D4E5", font=F_SUB)
    tabs = ["Eligibility", "Risk Profile", "Equity Lens"]
    x = 1030
    for tab in tabs:
        color = "#FFFFFF" if tab == active else "#94A3B8"
        draw.text((x, 33), tab, fill=color, font=font(15, tab == active))
        if tab == active:
            draw.line((x, 58, x + 84, 58), fill=TEAL, width=4)
        x += 150


def horizontal_bars(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int, int, int],
    labels: list[str],
    values: list[float],
    colors: list[str],
    value_fmt=pct,
) -> None:
    x0, y0, x1, y1 = xy
    max_value = max(values) if values else 1
    label_x = x0
    bar_x = x0 + 210
    bar_w = x1 - bar_x - 76
    row_h = (y1 - y0) // max(len(values), 1)
    for i, (label, value) in enumerate(zip(labels, values)):
        y = y0 + i * row_h + 8
        draw.text((label_x, y + 7), label, fill=INK, font=F_AXIS)
        draw.rounded_rectangle((bar_x, y, bar_x + bar_w, y + 30), radius=8, fill="#EEF2F7")
        w = int(bar_w * (value / max_value))
        draw.rounded_rectangle((bar_x, y, bar_x + w, y + 30), radius=8, fill=colors[i % len(colors)])
        draw.text((bar_x + w + 10, y + 6), value_fmt(value), fill=INK, font=F_AXIS)


def vertical_bars(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int, int, int],
    labels: list[str],
    values: list[float],
    colors: list[str],
    value_fmt=pct,
) -> None:
    x0, y0, x1, y1 = xy
    max_value = max(values) if values else 1
    plot_h = y1 - y0 - 44
    slot = (x1 - x0) // max(len(values), 1)
    for i, (label, value) in enumerate(zip(labels, values)):
        bar_h = int(plot_h * value / max_value)
        bx0 = x0 + i * slot + 28
        bx1 = bx0 + min(74, slot - 42)
        by1 = y1 - 42
        by0 = by1 - bar_h
        draw.rounded_rectangle((bx0, by0, bx1, by1), radius=8, fill=colors[i % len(colors)])
        draw.text((bx0, by0 - 24), value_fmt(value), fill=INK, font=F_AXIS)
        draw.text((bx0 - 10, y1 - 28), label, fill=MUTED, font=F_AXIS)


def draw_table(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int, int, int],
    frame: pd.DataFrame,
    columns: list[tuple[str, str, int]],
) -> None:
    x0, y0, _, _ = xy
    y = y0
    for label, _, width in columns:
        draw.text((x0, y), label, fill=MUTED, font=font(12, True))
        x0 += width
    draw.line((xy[0], y + 24, xy[2] - 20, y + 24), fill=LINE, width=1)
    y += 34
    for _, row in frame.iterrows():
        x = xy[0]
        for _, col, width in columns:
            val = row[col]
            if isinstance(val, float):
                text = pct(val) if "rate" in col or "share" in col else f"{val:.1f}"
            else:
                text = str(val)
            draw.text((x, y), text[:42], fill=INK, font=F_AXIS)
            x += width
        y += 28


def page_1() -> Image.Image:
    kpis = read("dashboard_kpis.csv").set_index("metric")["value"]
    eligibility = read("eligibility_summary.csv")
    by_bmi = read("eligibility_by_bmi_category.csv")
    eligibility_labels = {
        "Not guideline-like eligible": "Not guideline-like eligible",
        "BMI >=35: guideline-recommended": "BMI >=35: recommended",
        "BMI 30-34.9 + metabolic disease: consider": "BMI 30-34.9 + metabolic disease",
    }
    bmi_order = [
        "Normal or underweight",
        "Overweight",
        "Obesity class I",
        "Obesity class II",
        "Obesity class III",
    ]
    by_bmi["bmi_category"] = pd.Categorical(by_bmi["bmi_category"], categories=bmi_order, ordered=True)
    by_bmi = by_bmi.sort_values("bmi_category")

    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    header(draw, "Metabolic Surgery Eligibility Analytics", "NHANES 2017-March 2020 adult cohort phenotype view", "Eligibility")
    card(draw, (64, 126, 360, 236), "Analytic cohort", f"{int(kpis['Analytic cohort adults']):,}", BLUE)
    card(draw, (392, 126, 688, 236), "Weighted eligible", pct(kpis["Weighted eligibility rate"]), TEAL)
    card(draw, (720, 126, 1016, 236), "BMI >=35", pct(kpis["BMI >=35 recommended rate"]), ROSE)
    card(draw, (1048, 126, 1536, 236), "BMI 30-34.9 + metabolic disease", pct(kpis["BMI 30-34.9 + metabolic disease rate"]), AMBER)

    panel(draw, (64, 280, 822, 662), "Eligibility phenotype")
    labels = eligibility["eligibility_group"].map(eligibility_labels).tolist()
    values = eligibility["weighted_share"].tolist()
    horizontal_bars(draw, (92, 340, 792, 620), labels, values, [BLUE, ROSE, AMBER])

    panel(draw, (856, 280, 1536, 662), "Eligibility rate by BMI category")
    labels = [
        "Normal/\nunderweight",
        "Overweight",
        "Obesity I",
        "Obesity II",
        "Obesity III",
    ]
    values = by_bmi["guideline_like_eligible_rate"].fillna(0).tolist()
    vertical_bars(draw, (900, 350, 1500, 620), labels, values, [TEAL, BLUE, ROSE, AMBER, VIOLET])

    draw.text(
        (64, 722),
        "Interpretation: eligibility is guideline-like population phenotyping, not individual clinical candidacy.",
        fill=MUTED,
        font=F_SUB,
    )
    draw.text(
        (64, 760),
        "Data basis: public-use NHANES 2017-March 2020 pre-pandemic files; weighted estimates use MEC exam weights.",
        fill=MUTED,
        font=F_SMALL,
    )
    return img


def page_2() -> Image.Image:
    risk = read("cardiometabolic_risk_summary.csv")
    eligibility = read("eligibility_summary.csv")

    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    header(draw, "Cardiometabolic Risk Profile", "Risk clustering among guideline-like eligible and non-eligible adults", "Risk Profile")

    eligible = eligibility[eligibility["eligibility_group"] != "Not guideline-like eligible"]
    card(draw, (64, 126, 420, 236), "Eligible mean BMI", f"{eligible['mean_bmi'].mean():.1f}", ROSE)
    card(draw, (454, 126, 810, 236), "Eligible diabetes signal", pct(risk.loc[risk["risk_signal"].str.startswith("Diabetes"), "eligible_rate"].iloc[0]), BLUE)
    card(draw, (844, 126, 1200, 236), "Eligible hypertension signal", pct(risk.loc[risk["risk_signal"].str.startswith("Hypertension"), "eligible_rate"].iloc[0]), TEAL)
    card(draw, (1234, 126, 1536, 236), "Eligible 2+ risk signals", pct(risk.loc[risk["risk_signal"].str.startswith("Two"), "eligible_rate"].iloc[0]), AMBER)

    panel(draw, (64, 280, 780, 680), "Risk signal prevalence")
    labels = risk["risk_signal"].tolist()
    values = risk["eligible_rate"].tolist()
    horizontal_bars(draw, (92, 340, 740, 640), labels, values, [ROSE, TEAL, BLUE, AMBER, VIOLET])

    panel(draw, (814, 280, 1536, 680), "Eligible vs non-eligible contrast")
    draw_table(
        draw,
        (850, 340, 1510, 640),
        risk,
        [
            ("Risk signal", "risk_signal", 310),
            ("Eligible", "eligible_rate", 130),
            ("Not eligible", "not_eligible_rate", 150),
        ],
    )

    draw.text(
        (64, 742),
        "Clinical framing: surgery eligibility is evaluated alongside metabolic burden, not BMI alone.",
        fill=MUTED,
        font=F_SUB,
    )
    return img


def page_3() -> Image.Image:
    by_age = read("eligibility_by_age_group.csv")
    by_race = read("eligibility_by_race_ethnicity.csv").sort_values("guideline_like_eligible_rate", ascending=False)
    missing = read("missingness_summary.csv")

    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    header(draw, "Equity Lens and Cohort Audit", "Demographic variation, denominator checks, and missingness review", "Equity Lens")

    panel(draw, (64, 126, 754, 454), "Eligibility by age group")
    vertical_bars(
        draw,
        (110, 190, 720, 420),
        by_age["age_group"].tolist(),
        by_age["guideline_like_eligible_rate"].tolist(),
        [BLUE, TEAL, AMBER, ROSE],
    )

    panel(draw, (788, 126, 1536, 454), "Eligibility by race/ethnicity")
    horizontal_bars(
        draw,
        (820, 188, 1500, 420),
        by_race["race_ethnicity"].tolist(),
        by_race["guideline_like_eligible_rate"].tolist(),
        [VIOLET, BLUE, TEAL, AMBER, ROSE, GREEN],
    )

    panel(draw, (64, 500, 754, 784), "Missingness audit")
    draw_table(
        draw,
        (98, 560, 724, 744),
        missing.head(6),
        [("Field", "field", 250), ("Missing n", "missing_n", 130), ("Missing rate", "missing_rate", 140)],
    )

    panel(draw, (788, 500, 1536, 784), "Dashboard note")
    note = [
        "Use slicers for age group, sex, race/ethnicity, BMI category,",
        "and eligibility group. Keep weighted estimates in KPI cards and",
        "label unweighted sample counts clearly in tables.",
        "",
        "Avoid causal language: NHANES is cross-sectional.",
        "Use 'associated with' and 'risk profile', not 'predicts' or 'causes'.",
    ]
    y = 560
    for line in note:
        draw.text((824, y), line, fill=INK if line else MUTED, font=F_SUB)
        y += 30
    return img


def main() -> None:
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    pages = [
        ("powerbi-page-1-eligibility-overview.png", page_1()),
        ("powerbi-page-2-risk-profile.png", page_2()),
        ("powerbi-page-3-equity-audit.png", page_3()),
    ]
    for filename, image in pages:
        image.save(ASSETS_DIR / filename)
    page_1().save(ASSETS_DIR / "dashboard-preview.png")


if __name__ == "__main__":
    main()
