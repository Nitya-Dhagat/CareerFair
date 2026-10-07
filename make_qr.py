"""Usage: python make_qr.py https://your-domain.com [campaign]
Generates qr_<campaign>.png and card_<campaign>.png (printable 3.5x2in @300dpi)."""
import sys, qrcode
from PIL import Image, ImageDraw, ImageFont

base = sys.argv[1].rstrip("/")
campaign = sys.argv[2] if len(sys.argv) > 2 else "careerfair"
url = f"{base}/{campaign}"

qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=20, border=2)
qr.add_data(url); qr.make(fit=True)
qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
qr_img.save(f"qr_{campaign}.png")


def font(size, bold=False):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans%s.ttf" % ("-Bold" if bold else ""),
              "/usr/share/fonts/truetype/liberation/LiberationSans-%s.ttf" % ("Bold" if bold else "Regular")):
        try: return ImageFont.truetype(p, size)
        except OSError: pass
    return ImageFont.load_default()


W, H = 1050, 600  # 3.5 x 2 in @ 300 dpi
card = Image.new("RGB", (W, H), "white")
d = ImageDraw.Draw(card)
d.text((60, 70), "NITYA DHAGAT", font=font(52, True), fill="black")
d.text((60, 140), "AI / ML · DATA SCIENCE · SOFTWARE", font=font(24), fill="#555")
d.text((60, 300), "Scan to see\nwhat I build.", font=font(40, True), fill="black", spacing=10)
d.text((60, 520), "MS Data Science @ UC San Diego", font=font(24), fill="#555")
q = qr_img.resize((380, 380))
card.paste(q, (W - 380 - 60, 110))
d.text((W - 380 - 60, 510), url.replace("https://", "").replace("http://", ""), font=font(22), fill="#555")
card.save(f"card_{campaign}.png", dpi=(300, 300))
print("URL:", url, "\nSaved: qr_%s.png, card_%s.png" % (campaign, campaign))
