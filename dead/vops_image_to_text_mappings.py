import logging
import pdb
from PIL import Image, ImageDraw, ImageFont

def write_image_to_text_mappings(i2td):
    """Place images and text from a per-barcode img-to-txt dict into pngs"""
    freefont_root = "/usr/share/fonts/truetype/freefont"
    for k in i2td.keys():
        summary = Image.new("1",(1200,2400),color=1)
        draw = ImageDraw.Draw(summary)
        try:
            font = ImageFont.truetype(
                "%s/FreeSans.ttf" % (freefont_root,),16)
            header_font = ImageFont.truetype(
                "%s/FreeSans.ttf" % (freefont_root,),30)
        except IOError:
            font = ImageFont.load_default()
            header_font = font
            logging.warning( "Could not load FreeSans.ttf, using default font.")
        ctr = 0
        draw.text((50,50),k,font=header_font)
        for entry in i2td[k]:
            try:
                ctr += 1
                t,i = entry[0],entry[1]
                try:
                    summary.paste(Image.fromarray(i),(100,100+(ctr*30)))
                except:
                    summary.paste(i,(100,100+(ctr*30)))
                if len(t) < 30:
                    draw.text((350,100+(ctr*30)),t,font=font)
                else:
                    draw.text((350,100+(ctr*30)),t[:30],font=font)
                    draw.text((350,100+(ctr*30)+20),t[30:60],font=font)
                    ctr += 1
            except TypeError as te:
                print te
        summary.save('%s.png' % (k,))
