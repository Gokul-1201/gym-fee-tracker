from io import BytesIO

import qrcode


def make_qr_png(data: str, box_size=9) -> bytes:
    img = qrcode.make(data, box_size=box_size, border=2)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
