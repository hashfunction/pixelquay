"""Author original fictional demo content; never processes captured app screenshots.
Copyright 2026 Trieflow LLC. MIT. Requires Pillow only to author this committed PNG.
Fonts are rendered from the author's local installation, not redistributed.
"""
import argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def make(serif, sans):
    im=Image.new('RGB',(1800,1200),'#efe9d8');d=ImageDraw.Draw(im)
    ink='#183d40';sea='#2d6f78';light='#9cc9ba';coral='#e77b55';cream='#f8f2e1'
    font=lambda size:ImageFont.truetype(str(serif),size)
    clean=lambda size:ImageFont.truetype(str(sans),size)
    d.text((90,65),'FIELD NOTES  /  VOL. 06',font=clean(26),fill=ink)
    d.text((1380,65),'A SLOWER WEEKEND',font=clean(23),fill=ink)
    d.line((90,118,1710,118),fill=ink,width=2)
    d.text((80,140),'Cedar Coast',font=font(172),fill=ink)
    d.text((95,350),'FIND YOUR WAY TO THE WATER.',font=clean(31),fill=ink)
    d.text((1278,293),'Salt air. Open skies.\nRoom to wander.',font=clean(29),fill=ink,spacing=10)
    # Original layered coastal illustration, composed as a campaign poster.
    d.rounded_rectangle((90,422,1710,1000),radius=28,fill=light)
    d.ellipse((1290,455,1500,665),fill='#f3c879')
    d.polygon([(90,717),(288,638),(427,684),(572,580),(785,644),(996,541),(1161,625),(1350,661),(1551,604),(1710,672),(1710,1000),(90,1000)],fill='#607f76')
    d.polygon([(90,762),(259,694),(463,747),(655,662),(850,715),(1039,657),(1277,727),(1464,687),(1710,722),(1710,1000),(90,1000)],fill='#345b55')
    d.polygon([(90,815),(330,804),(560,825),(832,785),(1071,803),(1328,765),(1710,805),(1710,1000),(90,1000)],fill=sea)
    d.polygon([(90,940),(402,945),(642,865),(920,853),(1142,892),(1427,901),(1710,950),(1710,1000),(90,1000)],fill='#e5c798')
    d.line([(180,848),(450,855),(715,826),(992,842),(1256,820),(1600,846)],fill='#b9dcd0',width=6)
    d.line([(669,908),(832,887),(986,890),(1131,912)],fill=cream,width=5)
    # Small sunlit house and pine silhouette create a focal point in the landscape.
    d.rectangle((424,721,496,771),fill=cream);d.polygon([(411,725),(460,683),(510,725)],fill=coral)
    d.rectangle((451,743,467,771),fill=ink)
    for x,y,h in [(1190,693,105),(1236,708,85),(1295,702,111)]:
        d.rectangle((x-3,y-h//2,x+3,y+22),fill=ink)
        d.polygon([(x,y-h),(x-32,y-28),(x+32,y-28)],fill=ink)
        d.polygon([(x,y-h+25),(x-40,y),(x+40,y)],fill=ink)
    d.ellipse((138,463,321,646),fill=cream)
    d.text((165,494),'TAKE',font=clean(25),fill=ink);d.text((153,532),'THE LONG',font=clean(22),fill=ink);d.text((166,568),'WAY',font=clean(27),fill=ink)
    d.text((90,1050),'WALK THE HEADLANDS',font=clean(28),fill=ink)
    d.text((90,1094),'Small trails. Good company. A fresh perspective.',font=clean(25),fill=ink)
    d.text((1265,1049),'WEEKEND EDITION',font=clean(25),fill=ink)
    d.text((1310,1090),'EXPLORE / UNWIND',font=clean(24),fill=ink)
    d.line((90,1160,1710,1160),fill=ink,width=2)
    return im

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--serif',type=Path,required=True);p.add_argument('--sans',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    with a.output.open('xb') as out:make(a.serif,a.sans).save(out,'PNG',optimize=True)
