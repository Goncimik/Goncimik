#!/usr/bin/env python3
"""Post-process Platane/snk SVGs into a GOGO-branded, cyan–violet snake."""
from __future__ import annotations
import argparse
import re
from pathlib import Path
import xml.etree.ElementTree as ET

SVG_NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', SVG_NS)
def tag(name): return f'{{{SVG_NS}}}{name}'

FONT = {
    'G': ['01110','10001','10000','10111','10001','10001','01110'],
    'O': ['01110','10001','10001','10001','10001','10001','01110'],
}

def parse_len(value, fallback):
    match = re.match(r'^\s*([0-9]*\.?[0-9]+)', value or '')
    return float(match.group(1)) if match else fallback


def gradient(defs, identifier, colors):
    grad = ET.SubElement(defs, tag('linearGradient'), {
        'id': identifier, 'x1': '0%', 'y1': '0%', 'x2': '100%', 'y2': '0%'
    })
    for offset, color in colors:
        ET.SubElement(grad, tag('stop'), {'offset': offset, 'stop-color': color})


def setup_style(root):
    defs = root.find(tag('defs'))
    if defs is None:
        defs = ET.Element(tag('defs'))
        root.insert(0, defs)
    gradient(defs, 'gogoSnakeGradient', [('0%', '#2DD4BF'), ('38%', '#22D3EE'), ('72%', '#8B5CF6'), ('100%', '#C084FC')])
    gradient(defs, 'gogoLabelGradient', [('0%', '#5EEAD4'), ('45%', '#67E8F9'), ('100%', '#C084FC')])
    gradient(defs, 'gogoBarGradient', [('0%', '#2DD4BF'), ('50%', '#38BDF8'), ('100%', '#A855F7')])
    glow = ET.SubElement(defs, tag('filter'), {
        'id': 'gogoSoftGlow', 'x': '-30%', 'y': '-30%', 'width': '160%', 'height': '160%'
    })
    ET.SubElement(glow, tag('feGaussianBlur'), {'stdDeviation': '0.65', 'result': 'blur'})
    merger = ET.SubElement(glow, tag('feMerge'))
    ET.SubElement(merger, tag('feMergeNode'), {'in': 'blur'})
    ET.SubElement(merger, tag('feMergeNode'), {'in': 'SourceGraphic'})


def normalize_hex(value):
    return (value or '').strip().lower()


def recolor_snake(root):
    # Input snake color is fixed in snake.yml and is unique among contribution tiles.
    for el in root.iter():
        if normalize_hex(el.get('fill')) == '#2dd4bf':
            el.set('fill', 'url(#gogoSnakeGradient)')
            el.set('filter', 'url(#gogoSoftGlow)')


def style_long_bar(root):
    for el in root.iter(tag('rect')):
        width = parse_len(el.get('width'), 0)
        height = parse_len(el.get('height'), 0)
        if width > 200 and height <= 14:
            el.set('fill', 'url(#gogoBarGradient)')
            el.set('opacity', '0.88')


def add_pixel_label(root, label):
    # A translucent navy plate gives the word consistent contrast in light and dark GitHub themes.
    cell, size, corner = 11, 8, 2
    letters = [FONT.get(ch.upper()) for ch in label]
    letter_cols = sum(6 if glyph else 3 for glyph in letters) - 1
    svg_width = parse_len(root.get('width'), 960)
    label_width = letter_cols * cell + 26
    center = svg_width / 2
    left = max(4, center - label_width / 2)
    top = 7
    grp = ET.SubElement(root, tag('g'), {'id': 'gogoBrandMark'})
    ET.SubElement(grp, tag('rect'), {
        'x': f'{left:.1f}', 'y': str(top), 'width': f'{label_width:.1f}',
        'height': '94', 'rx': '12', 'fill': '#09152D', 'fill-opacity': '0.86',
        'stroke': '#38BDF8', 'stroke-opacity': '0.45', 'stroke-width': '1'
    })
    col = 0
    for glyph in letters:
        if glyph is None:
            col += 3
            continue
        for r, line in enumerate(glyph):
            for c, enabled in enumerate(line):
                if enabled == '1':
                    ET.SubElement(grp, tag('rect'), {
                        'x': f'{left + 15 + (col+c)*cell:.1f}',
                        'y': str(top + 9 + r*cell),
                        'width': str(size), 'height': str(size),
                        'rx': str(corner),
                        'fill': 'url(#gogoLabelGradient)',
                    })
        col += 6
    ET.SubElement(grp, tag('rect'), {
        'x': f'{left + 14:.1f}', 'y': str(top + 85),
        'width': f'{label_width - 28:.1f}', 'height': '2', 'rx': '1',
        'fill': 'url(#gogoBarGradient)', 'opacity': '0.8'
    })


def slow_down(text, multiplier):
    return re.sub(r'dur="([0-9]*\.?[0-9]+)s"',
                  lambda m: f'dur="{float(m.group(1))*multiplier:.3f}s"', text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--in', dest='inp', required=True)
    parser.add_argument('--out', required=True)
    parser.add_argument('--label', default='GOGO')
    parser.add_argument('--speed-mult', type=float, default=2.8)
    parser.add_argument('--dark', action='store_true')
    args = parser.parse_args()
    root = ET.fromstring(Path(args.inp).read_text(encoding='utf-8'))
    setup_style(root)
    recolor_snake(root)
    style_long_bar(root)
    add_pixel_label(root, args.label)
    result = slow_down(ET.tostring(root, encoding='unicode'), args.speed_mult)
    target = Path(args.out)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(result, encoding='utf-8')

if __name__ == '__main__':
    main()
