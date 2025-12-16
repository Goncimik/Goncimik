#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from pathlib import Path
import xml.etree.ElementTree as ET


FONT = {
    "G": ["01110","10001","10000","10111","10001","10001","01110"],
    "O": ["01110","10001","10001","10001","10001","10001","01110"],}

def _svg_ns(tag: str) -> str:
    return f"{{http://www.w3.org/2000/svg}}{tag}"

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

def add_gradient_and_glow(defs: ET.Element) -> None:
  
    existing = {el.get("id") for el in defs.iter() if el.get("id")}
    if "lilaGrad" not in existing:
        lg = ET.SubElement(defs, _svg_ns("linearGradient"), {
            "id": "lilaGrad", "x1": "0", "y1": "0", "x2": "1", "y2": "0"})
        
        ET.SubElement(lg, _svg_ns("stop"), {"offset": "0%", "stop-color": "#a569bd"})
        ET.SubElement(lg, _svg_ns("stop"), {"offset": "50%", "stop-color": "#c084fc"})
        ET.SubElement(lg, _svg_ns("stop"), {"offset": "100%", "stop-color": "#6d28d9"})

    if "glow" not in existing:
        flt = ET.SubElement(defs, _svg_ns("filter"), {"id": "glow"})
        ET.SubElement(flt, _svg_ns("feGaussianBlur"), {"stdDeviation": "1.2", "result": "blur"})
        merge = ET.SubElement(flt, _svg_ns("feMerge"))
        ET.SubElement(merge, _svg_ns("feMergeNode"), {"in": "blur"})
        ET.SubElement(merge, _svg_ns("feMergeNode"), {"in": "SourceGraphic"})

def apply_snake_style(root: ET.Element) -> None:
    for el in root.iter():
        fill = el.get("fill")
        if fill and fill.lower() == "#a569bd":
            el.set("fill", "url(#lilaGrad)")
            el.set("filter", "url(#glow)")

def slow_down_animations(svg_text: str, speed_mult: float) -> str:
    def repl(m):
        val = float(m.group(1))
        return f'dur="{val * speed_mult:.3f}s"'
    return re.sub(r'dur="([0-9]*\.?[0-9]+)s"', repl, svg_text)



    w = parse_len(root.get("width"), 960.0)

    fill = "#c084fc" if dark else "#6d28d9"

    t = ET.SubElement(root, _svg_ns("text"), {
        "x": str(w / 2),
        "y": "24",
        "text-anchor": "middle",
        "font-size": "18",
        "font-weight": "700",
        "font-family": "ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Arial",
        "letter-spacing": "1.5",
        "fill": fill,
        "opacity": "0.95"})
    t.text = label

def add_pixel_gogo(root: ET.Element, label: str, dark: bool) -> None:
    cell = 12
    dot_size = 10
    rx = 2

    dot_fill = "#22c55e" if dark else "#16a34a"
    dot_opacity = "0.95"


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
                        "opacity": dot_opacity})
        col += 7

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", dest="out", required=True)
    ap.add_argument("--label", default="GOGO")
    ap.add_argument("--speed-mult", type=float, default=2.8)
    ap.add_argument("--dark", action="store_true")
    args = ap.parse_args()

    inp = Path(args.inp)
    out = Path(args.out)

    svg_text = inp.read_text(encoding="utf-8")


    ET.register_namespace("", "http://www.w3.org/2000/svg")
    root = ET.fromstring(svg_text)


    defs = ensure_defs(root)
    add_gradient_and_glow(defs)


    apply_snake_style(root)

    add_label_text(root, args.label, dark=args.dark)
    add_pixel_gogo(root, args.label, dark=args.dark)


    xml_out = ET.tostring(root, encoding="unicode")

    xml_out = slow_down_animations(xml_out, args.speed_mult)

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(xml_out, encoding="utf-8")

if __name__ == "__main__":
    main()

