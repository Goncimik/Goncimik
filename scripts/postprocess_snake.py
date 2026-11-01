
#!/usr/bin/env python3
from pathlib import Path
import argparse
import xml.etree.ElementTree as ET

FONT = {
    "G": ("01110", "10001", "10000", "10111",
          "10001", "10001", "01110"),
    "O": ("01110", "10001", "10001", "10001",
          "10001", "10001", "01110"),
}

NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", NS)

def el(parent, tag, **attrs):
    return ET.SubElement(
        parent, f"{{{NS}}}{tag}",
        {k.replace("_", "-"): str(v) for k, v in attrs.items()}
    )

PITCH, SIZE, X0, Y0 = 17, 13, 35, 43
COLS, ROWS = 53, 7

def xy(cell):
    c, r = cell
    return X0 + c * PITCH + SIZE / 2, Y0 + r * PITCH + SIZE / 2

def targets():
    result = []
    for letter_idx, ch in enumerate("GOGO"):
        glyph = FONT[ch]
        for c in range(5):
            rows = [r for r in range(7) if glyph[r][c] == "1"]
            if c % 2:
                rows.reverse()
            for r in rows:
                result.append((14 + letter_idx * 7 + c, r, letter_idx))
    return result

def snake_path(items):
    p = (2, 3)
    steps = [p] * 15
    arrived = []

    for c, r, _ in items:
        q = (c, r)
        while p[0] != q[0]:
            p = (p[0] + (1 if q[0] > p[0] else -1), p[1])
            steps.append(p)
        while p[1] != q[1]:
            p = (p[0], p[1] + (1 if q[1] > p[1] else -1))
            steps.append(p)
        arrived.append(len(steps) - 1)

    steps += [steps[-1]] * 35
    return steps, arrived

def make_svg(dark, filename):
    items = targets()
    steps, arrived = snake_path(items)
    n = len(steps)
    duration = n * 0.11

    root = ET.Element(f"{{{NS}}}svg", {
        "viewBox": "0 0 970 205",
        "width": "970",
        "height": "205",
        "role": "img",
        "aria-label": "Snake eating GOGO letters"
    })

    bg = "#081526" if dark else "#edf4ff"
    grid = "#132b49" if dark else "#d6e7f5"
    colors = ["#2dd4bf", "#56dbe8", "#8b7bfa", "#c084fc"]

    el(root, "rect", x=0, y=0, width=970,
       height=205, fill=bg, rx=12)

    for r in range(ROWS):
        for c in range(COLS):
            el(root, "rect",
               x=X0 + c * PITCH,
               y=Y0 + r * PITCH,
               width=SIZE, height=SIZE,
               rx=3, fill=grid)

    # Harflerin her karesi, yılan ulaştığında kaybolur.
    for (c, r, letter), step in zip(items, arrived):
        sq = el(root, "rect",
                x=X0 + c * PITCH,
                y=Y0 + r * PITCH,
                width=SIZE, height=SIZE,
                rx=3, fill=colors[letter])

        t = step / (n - 1)
        el(sq, "animate",
           attributeName="opacity",
           calcMode="discrete",
           values="1;0;1",
           keyTimes=f"0;{t:.7f};1",
           dur=f"{duration:.3f}s",
           repeatCount="indefinite")

    # Yılanın başı ve gövdesi aynı yolu takip eder.
    times = ";".join(f"{i/(n-1):.7f}" for i in range(n))

    for j in reversed(range(6)):
        coords = [xy(steps[max(0, i-j)]) for i in range(n)]

        node = el(root, "circle",
                  cx=coords[0][0],
                  cy=coords[0][1],
                  r=6.5 - j * 0.55,
                  fill="#2dd4bf" if j == 0 else "#7c83f5",
                  opacity=1 - j * 0.13)

        for attr, index in [("cx", 0), ("cy", 1)]:
            values = ";".join(f"{p[index]:.2f}" for p in coords)
            el(node, "animate",
               attributeName=attr,
               values=values,
               keyTimes=times,
               calcMode="linear",
               dur=f"{duration:.3f}s",
               repeatCount="indefinite")

    Path(filename).parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(root).write(
        filename, encoding="utf-8", xml_declaration=True
    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", default="out")
    args = parser.parse_args()

    make_svg(False, Path(args.outdir) / "gogo-snake.svg")
    make_svg(True, Path(args.outdir) / "gogo-snake-dark.svg")
    print("GOGO Snake: SVG files generated successfully.")

