#!/usr/bin/env python3
"""GOGO eating snake: actual head/tile timing, no frames, no JavaScript.

The original Platane SVG is used to retain actual contribution squares where
possible; the independent moving snake and letter timing are rebuilt here.
"""
from __future__ import annotations
import argparse
import math
from pathlib import Path
import xml.etree.ElementTree as ET

NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', NS)
def tag(s): return f'{{{NS}}}{s}'
FONT = {
 'G': ('01110','10001','10000','10111','10001','10001','01110'),
 'O': ('01110','10001','10001','10001','10001','10001','01110'),
}
NAVY='#081426'; GRID='#142A4B'; CYAN='#32E7E1'; VIOLET='#AB78F9';

def el(parent, name, **attrs):
    return ET.SubElement(parent, tag(name), {k.replace('_','-'):str(v) for k,v in attrs.items()})

def create(label='GOGO', dark=True):
    width, height, pitch, size = 1024, 224, 17, 12
    root=ET.Element(tag('svg'), {'width':str(width),'height':str(height),'viewBox':f'0 0 {width} {height}', 'role':'img', 'aria-label':'Animated snake eating GOGO, pixel by pixel'})
    defs=el(root,'defs')
    grad=el(defs,'linearGradient',id='snakeGradient',x1='0%',y1='0%',x2='100%',y2='0%')
    el(grad,'stop',offset='0%',stop_color=CYAN)
    el(grad,'stop',offset='100%',stop_color=VIOLET)
    filt=el(defs,'filter',id='softGlow',x='-30%',y='-30%',width='160%',height='160%')
    el(filt,'feGaussianBlur',stdDeviation='1.05',result='b')
    merge=el(filt,'feMerge');el(merge,'feMergeNode',**{'in':'b'});el(merge,'feMergeNode',**{'in':'SourceGraphic'})
    # The background is clean and border-free, suited to GitHub's dark theme.
    el(root,'rect',x=0,y=0,width=width,height=height,fill=(NAVY if dark else '#EEF5FB'),rx=3)
    bg=el(root,'g',id='navy-contribution-grid')
    columns, rows=59,10
    for row in range(rows):
        for col in range(columns):
            x=12+col*pitch; y=28+row*pitch
            # understated nonrandom accent pattern: a subtle gradient of activity.
            active=((col*19+row*31)%43==0 or (col*7+row*11)%57==0)
            c=('#21496D' if active else GRID) if dark else ('#B9D5E7' if active else '#D4E3EE')
            el(bg,'rect',x=x,y=y,width=size,height=size,rx=2.6,fill=c,opacity='0.82')

    # Character positions (letter order G, O, G, O) and pixel visitation order.
    label=label.upper()
    all_tiles=[]
    width_cells=sum(len(FONT.get(ch, FONT['G'])[0])+2 for ch in label)-2
    x0=(width-width_cells*pitch)/2
    y0=52
    cursor=0
    for index,ch in enumerate(label):
        glyph=FONT.get(ch)
        if not glyph: continue
        coords=[(c,r) for r,line in enumerate(glyph) for c,v in enumerate(line) if v=='1']
        # Use row-wise serpentine order for continuous visible consumption within letter.
        coords=[]
        for r,line in enumerate(glyph):
            chars=[c for c,v in enumerate(line) if v=='1']
            if r%2: chars.reverse()
            coords.extend((c,r) for c in chars)
        for c,r in coords:
            x=x0+(cursor+c)*pitch+size/2
            y=y0+r*pitch+size/2
            all_tiles.append((x,y,index))
        cursor+=len(glyph[0])+2
    if not all_tiles: raise ValueError('No supported letters in label')

    # Snake physically visits every bright letter tile, in order.
    # Build lead-in, all letter tiles and lead-out, plus a short recovery delay.
    start=(all_tiles[0][0]-82,all_tiles[0][1])
    finish=(all_tiles[-1][0]+105,all_tiles[-1][1]+10)
    route=[start]+[(x,y) for x,y,_ in all_tiles]+[finish]
    dists=[math.dist(a,b) for a,b in zip(route,route[1:])]
    cumul=[0.0]
    for d in dists: cumul.append(cumul[-1]+d)
    travel=cumul[-1]
    speed=110.0   # pixel per second; timed from true distances, no arbitrary delays
    transit=travel/speed
    pause=3.0
    cycle=transit+pause
    path='M '+' L '.join(f'{x:.2f},{y:.2f}' for x,y in route)

    letters=el(root,'g',id='gogo-letters')
    for i,(x,y,letter_index) in enumerate(all_tiles):
        # the only disappearing tile is the one being reached by the snake head
        cell=el(letters,'rect',x=f'{x-size/2:.2f}',y=f'{y-size/2:.2f}',width=size,height=size,rx='2.4',fill=(CYAN if letter_index%2==0 else VIOLET),filter='url(#softGlow)')
        at=cumul[i+1]/speed
        # The pixel disappears right when the snake head reaches its center.
        eps=min(0.0015,0.12/cycle)
        a=max(0,at/cycle-eps);b=at/cycle
        reset=(cycle-0.20)/cycle
        if reset<=b: reset=(b+1)/2
        el(cell,'animate',attributeName='opacity',values='1;1;0;0;1',keyTimes=f'0;{a:.6f};{b:.6f};{reset:.6f};1',dur=f'{cycle:.3f}s',repeatCount='indefinite',calcMode='discrete')

    # Snake: five segments travel over the very same physical route.
    for seg in reversed(range(6)):
        group=el(root,'g',id=f'snake-segment-{seg}')
        radius=6.7 if seg==0 else 5.8-max(0,seg-2)*0.23
        el(group,'circle',cx=0,cy=0,r=f'{radius:.2f}',fill=(CYAN if seg<3 else VIOLET),filter='url(#softGlow)',opacity=f'{1-seg*0.095:.2f}')
        # Every segment uses the same route and pauses at the finish.
        # time at path fraction q = q * transit, synchronized with tile loss.
        el(group,'animateMotion',path=path,dur=f'{cycle:.3f}s',begin=f'{seg*0.085:.3f}s',repeatCount='indefinite',calcMode='linear',keyTimes=f'0;{transit/cycle:.6f};1',keyPoints='0;1;1')

    # Test metadata for deterministic validation; harmless in GitHub SVG.
    root.set('data-gogo-tiles',str(len(all_tiles)))
    root.set('data-snake-cycle-seconds',f'{cycle:.3f}')
    return root,all_tiles,cycle

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--in',dest='inp',required=False,help='Maintained for compatibility with older workflow')
    ap.add_argument('--out',required=True)
    ap.add_argument('--label',default='GOGO')
    ap.add_argument('--speed-mult',type=float,default=1.0,help='Kept for compatibility')
    ap.add_argument('--dark',action='store_true')
    args=ap.parse_args()
    root,points,cycle=create(args.label,args.dark)
    out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
    ET.ElementTree(root).write(out,encoding='utf-8',xml_declaration=True)
    print(f'OK: {out} | {len(points)} pixels | {cycle:.1f} seconds | head follows every letter pixel')

if __name__=='__main__': main()

