#!/usr/bin/env python3
from __future__ import annotations

import argparse
import math
import re
from pathlib import Path
import xml.etree.ElementTree as ET

SVG_NS = "http://www.w3.org/2000/svg"


def _svg(tag: str) -> str:
    return f"{{{SVG_NS}}}{tag}"


FONT = {
    "G": [
        "011110",
        "100001",
        "100000",
        "100111",
        "100001",
        "100001",
        "011110",
    ],
    "O": [
        "011110",
        "100001",
        "100001",
        "100001",
        "100001",
        "100001",
        "011110",
    ],
}


PALETTE = {
    "bg_dark": "#08111f",
    "grid_dark": "#11284a",
    "grid_mid": "#173763",
    "snake": "#58f1e3",
    "snake_glow": "#7ff8ee",
    "text_teal": "#69f0ff",
    "text_lilac": "#d7c6ff",
    "text_purple": "#a66cff",
    "text_purple_2": "#8b5cf6",
}


def parse_len(x: str | None, default: float) -> float:
    if not x:
        return default
    m = re.match(r"^\s*([0-9]*\.?[0-9]+)", x)
    return float(m.group(1)) if m else default


def ensure_defs(root: ET.Element) -> ET.Element:
    defs = root.find(_svg("defs"))
    if defs is None:
        defs = ET.Element(_svg("defs"))
        root.insert(0, defs)
    return defs


def add_defs(defs: ET.Element) -> None:
    existing = {el.get("id") for el in defs.iter() if el.get("id")}

    if "snakeGlow" not in existing:
        flt = ET.SubElement(defs, _svg("filter"), {
            "id": "snakeGlow",
            "x": "-50%",
            "y": "-50%",
            "width": "200%",
            "height": "200%",
        })
        ET.SubElement(flt, _svg("feGaussianBlur"), {
            "in": "SourceGraphic",
            "stdDeviation": "1.4",
            "result": "blur"
        })
        merge = ET.SubElement(flt, _svg("feMerge"))
        ET.SubElement(merge, _svg("feMergeNode"), {"in": "blur"})
        ET.SubElement(merge, _svg("feMergeNode"), {"in": "SourceGraphic"})

    if "tileGlow" not in existing:
        flt = ET.SubElement(defs, _svg("filter"), {
            "id": "tileGlow",
            "x": "-50%",
            "y": "-50%",
            "width": "200%",
            "height": "200%",
        })
        ET.SubElement(flt, _svg("feGaussianBlur"), {
            "in": "SourceGraphic",
            "stdDeviation": "0.8",
            "result": "blur"
        })
        merge = ET.SubElement(flt, _svg("feMerge"))
        ET.SubElement(merge, _svg("feMergeNode"), {"in": "blur"})
        ET.SubElement(merge, _svg("feMergeNode"), {"in": "SourceGraphic"})

    if "wordGrad" not in existing:
        lg = ET.SubElement(defs, _svg("linearGradient"), {
            "id": "wordGrad",
            "x1": "0%",
            "y1": "0%",
            "x2": "100%",
            "y2": "0%",
        })
        ET.SubElement(lg, _svg("stop"), {
            "offset": "0%",
            "stop-color": PALETTE["text_teal"],
        })
        ET.SubElement(lg, _svg("stop"), {
            "offset": "45%",
            "stop-color": PALETTE["text_lilac"],
        })
        ET.SubElement(lg, _svg("stop"), {
            "offset": "100%",
            "stop-color": PALETTE["text_purple"],
        })


def recolor_svg(root: ET.Element) -> None:
    """
    Snake ve grid renklerini seçilen temaya yaklaştır.
    Platane/snk çıktısındaki rect'leri yeniden boya.
    """
    rects = list(root.iter(_svg("rect")))
    if not rects:
        return

    # En yaygın küçük dikdörtgenleri grid kabul et
    for rect in rects:
        w = parse_len(rect.get("width"), 0)
        h = parse_len(rect.get("height"), 0)
        fill = (rect.get("fill") or "").lower()

        if w <= 16 and h <= 16:
            # Snake rengi
            if fill in {"#a569bd", "#39d353", "#26a641", "#30a14e"}:
                rect.set("fill", PALETTE["snake"])
                rect.set("filter", "url(#snakeGlow)")
            else:
                # grid pikselleri
                if fill.startswith("#"):
                    # koyu lacivert tonlara çek
                    rect.set("fill", PALETTE["grid_dark"])
                    rect.set("opacity", "0.95")

    # Arka plana yakın büyük rect varsa koyulaştır
    for rect in rects:
        w = parse_len(rect.get("width"), 0)
        h = parse_len(rect.get("height"), 0)
        if w > 200 and h > 40:
            rect.set("fill", PALETTE["bg_dark"])


def extract_grid(root: ET.Element) -> tuple[float, float, float, float]:
    """
    Grid'in yaklaşık hücre boyutunu ve başlangıcını bul.
    """
    xs = []
    ys = []
    widths = []
    heights = []

    for rect in root.iter(_svg("rect")):
        w = parse_len(rect.get("width"), 0)
        h = parse_len(rect.get("height"), 0)
        x = parse_len(rect.get("x"), 0)
        y = parse_len(rect.get("y"), 0)

        if 6 <= w <= 16 and 6 <= h <= 16:
            xs.append(x)
            ys.append(y)
            widths.append(w)
            heights.append(h)

    if not xs:
        return 20.0, 20.0, 12.0, 12.0

    xs_sorted = sorted(set(round(v, 2) for v in xs))
    ys_sorted = sorted(set(round(v, 2) for v in ys))

    dxs = [b - a for a, b in zip(xs_sorted, xs_sorted[1:]) if (b - a) > 0.1]
    dys = [b - a for a, b in zip(ys_sorted, ys_sorted[1:]) if (b - a) > 0.1]

    cell_x = min(dxs) if dxs else (sum(widths) / len(widths))
    cell_y = min(dys) if dys else (sum(heights) / len(heights))
    cell = min(cell_x, cell_y)

    x0 = min(xs)
    y0 = min(ys)

    return x0, y0, cell, cell


def build_label_points(label: str):
    points = []
    cursor_x = 0

    for ch in label:
        if ch == " ":
            cursor_x += 2
            continue
        glyph = FONT.get(ch)
        if not glyph:
            cursor_x += 2
            continue

        width = len(glyph[0])
        for r, row in enumerate(glyph):
            for c, v in enumerate(row):
                if v == "1":
                    points.append((cursor_x + c, r))
        cursor_x += width + 2

    return points, cursor_x


def add_gogo_tiles(root: ET.Element, label: str, speed_mult: float) -> None:
    w = parse_len(root.get("width"), 960.0)
    h = parse_len(root.get("height"), 180.0)

    x0, y0, cell_w, cell_h = extract_grid(root)
    cell = min(cell_w, cell_h)

    points, total_cols = build_label_points(label)
    if not points:
        return

    rows = 7
    grid_cols_est = max(1, int((w - x0 * 2) / cell))
    start_col = max(1, (grid_cols_est - total_cols) // 2)
    start_row = 1

    g = ET.SubElement(root, _svg("g"), {
        "id": "gogoText",
        "opacity": "1"
    })

    # soldan sağa, yukarıdan aşağı sırayla yensin
    points_sorted = sorted(points, key=lambda p: (p[0], p[1]))

    base_duration = 6.2 * speed_mult / 2.8
    step = 0.10 * speed_mult / 2.8

    size = max(6.0, cell - 2.4)
    radius = "2"

    for i, (cx, cy) in enumerate(points_sorted):
        x = x0 + (start_col + cx) * cell + 1
        y = y0 + (start_row + cy) * cell + 1

        tile = ET.SubElement(g, _svg("rect"), {
            "x": f"{x:.2f}",
            "y": f"{y:.2f}",
            "width": f"{size:.2f}",
            "height": f"{size:.2f}",
            "rx": radius,
            "ry": radius,
            "fill": "url(#wordGrad)",
            "filter": "url(#tileGlow)",
            "opacity": "0.98",
        })

        begin = 0.6 + i * step

        # Tek tek kaybolma = yılan yiyor hissi
        ET.SubElement(tile, _svg("animate"), {
            "attributeName": "opacity",
            "values": "0.98;0.98;0",
            "keyTimes": "0;0.82;1",
            "dur": f"{base_duration:.2f}s",
            "begin": f"{begin:.2f}s",
            "fill": "freeze",
            "repeatCount": "1",
        })

        ET.SubElement(tile, _svg("animateTransform"), {
            "attributeName": "transform",
            "attributeType": "XML",
            "type": "scale",
            "values": "1 1;1 1;0.1 0.1",
            "keyTimes": "0;0.82;1",
            "dur": f"{base_duration:.2f}s",
            "begin": f"{begin:.2f}s",
            "fill": "freeze",
            "repeatCount": "1",
            "additive": "sum",
        })


def slow_down_animations(svg_text: str, speed_mult: float) -> str:
    def repl(m):
        val = float(m.group(1))
        return f'dur="{val * speed_mult:.3f}s"'
    return re.sub(r'dur="([0-9]*\.?[0-9]+)s"', repl, svg_text)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", dest="out", required=True)
    ap.add_argument("--label", default="GOGO")
    ap.add_argument("--speed-mult", type=float, default=1.8)
    args = ap.parse_args()

    svg_text = Path(args.inp).read_text(encoding="utf-8")

    ET.register_namespace("", SVG_NS)
    root = ET.fromstring(svg_text)

    defs = ensure_defs(root)
    add_defs(defs)
    recolor_svg(root)
    add_gogo_tiles(root, args.label, args.speed_mult)

    xml_out = ET.tostring(root, encoding="unicode")
    xml_out = slow_down_animations(xml_out, args.speed_mult)

    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(xml_out, encoding="utf-8")


if __name__ == "__main__":
    main()
