#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path
import xml.etree.ElementTree as ET

SVG_NS = "http://www.w3.org/2000/svg"

FONT = {
    "G": ["01110","10001","10000","10111","10001","10001","01110"],
    "O": ["01110","10001","10001","10001","10001","10001","01110"],}

PURPLE = {
    "light": {"pixel": "#a855f7"},  # violet-500
    "dark":  {"pixel": "#c084fc"},  # violet-300
}

def _svg_ns(tag: str) -> str:
    return f"{{{SVG_NS}}}{tag}"

def parse_len(x: str | None, default: float) -> float:
    if not x:
        return default
    m = re.match(r"^\s*([0-9]*\.?[0-9]+)", x)
    return float(m.group(1)) if m else default

def ensure_defs(root: ET.Element) -> ET.Element:
    defs = root.find(_svg_ns("defs"))
    if defs is None:
        defs = ET.Element(_svg_ns("defs"))
        root.insert(0, defs)
    return defs

def add_gradients_and_glow(defs: ET.Element) -> None:
    existing = {el.get("id") for el in defs.iter() if el.get("id")}


    if "lilaGrad" not in existing:
        lg = ET.SubElement(defs, _svg_ns("linearGradient"), {
            "id": "lilaGrad", "x1": "0", "y1": "0", "x2": "1", "y2": "0"
        })
        ET.SubElement(lg, _svg_ns("stop"), {"offset": "0%", "stop-color": "#e9d5ff"})
        ET.SubElement(lg, _svg_ns("stop"), {"offset": "50%", "stop-color": "#c084fc"})
        ET.SubElement(lg, _svg_ns("stop"), {"offset": "100%", "stop-color": "#6d28d9"})


    if "purpleBarGrad" not in existing:
        bg = ET.SubElement(defs, _svg_ns("linearGradient"), {
            "id": "purpleBarGrad", "x1": "0", "y1": "0", "x2": "1", "y2": "0"
        })
        ET.SubElement(bg, _svg_ns("stop"), {"offset": "0%", "stop-color": "#e9d5ff"})
        ET.SubElement(bg, _svg_ns("stop"), {"offset": "50%", "stop-color": "#a855f7"})
        ET.SubElement(bg, _svg_ns("stop"), {"offset": "100%", "stop-color": "#6d28d9"})

 
    if "glow" not in existing:
        flt = ET.SubElement(defs, _svg_ns("filter"), {"id": "glow"})
        ET.SubElement(flt, _svg_ns("feGaussianBlur"), {"stdDeviation": "1.6", "result": "blur"})
        merge = ET.SubElement(flt, _svg_ns("feMerge"))
        ET.SubElement(merge, _svg_ns("feMergeNode"), {"in": "blur"})
        ET.SubElement(merge, _svg_ns("feMergeNode"), {"in": "SourceGraphic"})

def apply_snake_gradient(root: ET.Element) -> None:

    for el in root.iter():
        fill = el.get("fill")
        if fill and fill.lower() == "#a569bd":
            el.set("fill", "url(#lilaGrad)")
            el.set("filter", "url(#glow)")

def apply_bar_gradient(root: ET.Element) -> None:

    for el in root.iter(_svg_ns("rect")):
        w = parse_len(el.get("width"), 0)
        h = parse_len(el.get("height"), 0)
        if w > 200 and h <= 18:
            el.set("fill", "url(#purpleBarGrad)")
            el.set("opacity", "0.95")
            el.set("filter", "url(#glow)")

def is_greenish(hexcol: str) -> bool:
    s = (hexcol or "").strip().lower()
    if not s.startswith("#"):
        return False
    if len(s) == 4:
        r = int(s[1]*2, 16); g = int(s[2]*2, 16); b = int(s[3]*2, 16)
    elif len(s) == 7:
        r = int(s[1:3], 16); g = int(s[3:5], 16); b = int(s[5:7], 16)
    else:
        return False
    return g > r + 20 and g > b + 20

def recolor_greenish_to_purple(root: ET.Element) -> None:

    PURPLE_SOLID = "#7c3aed"
    for el in root.iter():
        fill = el.get("fill")
        if fill and is_greenish(fill):
            el.set("fill", PURPLE_SOLID)

        stroke = el.get("stroke")
        if stroke and is_greenish(stroke):
            el.set("stroke", PURPLE_SOLID)

        style = el.get("style")
        if style and ("fill:" in style or "stroke:" in style):
   
            pass

def dim_bright_tiles(root: ET.Element) -> None:
    
    for el in root.iter(_svg_ns("rect")):
        fill = el.get("fill")
        if fill and fill.lower() in ("#ffffff", "#f8fafc", "#f1f5f9"):
            el.set("opacity", "0.35")

def slow_down_animations(svg_text: str, speed_mult: float) -> str:
    def repl(m):
        val = float(m.group(1))
        return f'dur="{val * speed_mult:.3f}s"'
    return re.sub(r'dur="([0-9]*\.?[0-9]+)s"', repl, svg_text)

def add_pixel_label(root: ET.Element, label: str, dark: bool) -> None:
    cell = 12
    dot_size = 10
    rx = 2

    dot_fill = PURPLE["dark" if dark else "light"]["pixel"]
    dot_opacity = "0.97"

    w = parse_len(root.get("width"), 960.0)
    approx_cols = len(label) * 7
    start_col = max(2, int((w / cell - approx_cols) / 2))
    start_row = 2

    g = ET.SubElement(root, _svg_ns("g"), {"id": "gogoText", "opacity": "1.0"})

    col = start_col
    for ch in label:
        if ch not in FONT:
            col += 7
            continue

        for r, line in enumerate(FONT[ch]):
            for c, v in enumerate(line):
                if v == "1":
                    x = (col + c) * cell
                    y = (start_row + r) * cell
                    ET.SubElement(g, _svg_ns("rect"), {
                        "x": str(x),
                        "y": str(y),
                        "width": str(dot_size),
                        "height": str(dot_size),
                        "rx": str(rx),
                        "ry": str(rx),
                        "fill": dot_fill,
                        "opacity": str(dot_opacity),
                        "filter": "url(#glow)",
                    })
        col += 7

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", dest="out", required=True)
    ap.add_argument("--label", default="GOGO")
    ap.add_argument("--speed-mult", type=float, default=2.8)
    ap.add_argument("--dark", action="store_true")
    args = ap.parse_args()

    svg_text = Path(args.inp).read_text(encoding="utf-8")

    ET.register_namespace("", SVG_NS)
    root = ET.fromstring(svg_text)

    defs = ensure_defs(root)
    add_gradients_and_glow(defs)

    apply_snake_gradient(root)
    apply_bar_gradient(root)
    recolor_greenish_to_purple(root)
    dim_bright_tiles(root)
    add_pixel_label(root, args.label, dark=args.dark)

    xml_out = ET.tostring(root, encoding="unicode")
    xml_out = slow_down_animations(xml_out, args.speed_mult)

    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(xml_out, encoding="utf-8")

if __name__ == "__main__":
    main()
