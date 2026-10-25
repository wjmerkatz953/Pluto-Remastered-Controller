"""Draw app icon from simple vector geometry; no third-party font or game art."""
from pathlib import Path
from PIL import Image, ImageDraw

here=Path(__file__).resolve().parent
size=512
im=Image.new("RGBA",(size,size),(0,0,0,0))
d=ImageDraw.Draw(im)
d.rounded_rectangle((22,22,490,490),radius=112,fill="#0F1F2C",outline="#56DFC0",width=14)
d.ellipse((91,91,421,421),outline="#274D54",width=28)
d.arc((91,91,421,421),38,141,fill="#56DFC0",width=31)
d.arc((91,91,421,421),215,317,fill="#56DFC0",width=31)
# Head-to-head chevrons to evoke player competition.
d.polygon([(142,197),(234,256),(142,315)],fill="#D3FAF0")
d.polygon([(370,197),(278,256),(370,315)],fill="#56DFC0")
d.ellipse((242,242,270,270),fill="#F3D287")
outfile=here/"pluto_arena.ico"
im.save(outfile,format="ICO",sizes=[(256,256),(128,128),(64,64),(48,48),(32,32),(16,16)])
print("PASS:",outfile,outfile.stat().st_size,flush=True)
