#!/usr/bin/env python3
"""Generator ikon PWA untuk aplikasi Susunan Acara.
Menghasilkan PNG persegi penuh (full-bleed) dengan jam putih + titik oranye
di tengah. Ikon tunggal cocok untuk purpose "any" dan "maskable"
(konten berada dalam zona aman 80% tengah).
Menulis: icon-180.png, icon-192.png, icon-512.png
Tanpa dependensi eksternal (stdlib saja).
"""

import struct
import zlib

BG = (124, 58, 237)      # #7C3AED
WHITE = (255, 255, 255)
ORANGE = (249, 115, 22)  # #F97316


def seg_dist(px, py, ax, ay, bx, by):
    """Jarak titik ke ruas garis a-b."""
    abx, aby = bx - ax, by - ay
    apx, apy = px - ax, py - ay
    t = max(0.0, min(1.0, (apx * abx + apy * aby) / (abx * abx + aby * aby)))
    dx, dy = px - (ax + abx * t), py - (ay + aby * t)
    return (dx * dx + dy * dy) ** 0.5


def pixel(x, y):
    """Warna pada koordinat [0,1) x [0,1)."""
    cx = cy = 0.5
    R = 0.28
    dist = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5

    # Gelang jam (putih)
    ring_t = 0.045
    if abs(dist - R) <= ring_t / 2:
        return WHITE

    # Jarum menit (ke atas, ke arah angka 12)
    if seg_dist(x, y, cx, cy, cx, cy - R * 0.68) <= 0.014:
        return WHITE

    # Jarum jam (ke kanan-bawah, ke arah angka 4)
    if seg_dist(x, y, cx, cy, cx + R * 0.52, cy + R * 0.52) <= 0.018:
        return WHITE

    # Titik tengah (oranye)
    if dist <= 0.05:
        return ORANGE

    return BG


def write_png(path, size):
    SS = 4  # supersampling 4x4 untuk tepi halus
    rows = []
    for j in range(size):
        row = []
        for i in range(size):
            r = g = b = a = 0.0
            for sy in range(SS):
                for sx in range(SS):
                    x = (i + (sx + 0.5) / SS) / size
                    y = (j + (sy + 0.5) / SS) / size
                    pr, pg, pb = pixel(x, y)
                    r += pr
                    g += pg
                    b += pb
                    a += 1.0
            n = SS * SS
            row.append((int(r / n + 0.5), int(g / n + 0.5), int(b / n + 0.5), 255))
        rows.append(row)

    raw = b"".join(b"\x00" + bytes(v for px in px_row for v in px) for px_row in rows)
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0)

    def chunk(typ, data):
        return (struct.pack(">I", len(data)) + typ + data
                + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF))

    png = (b"\x89PNG\r\n\x1a\n"
           + chunk(b"IHDR", ihdr)
           + chunk(b"IDAT", zlib.compress(raw, 9))
           + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)
    print("OK  " + path + "  (" + str(size) + "x" + str(size) + ", " + str(len(png)) + " bytes)")


if __name__ == "__main__":
    for s in (180, 192, 512):
        write_png("icon-" + str(s) + ".png", s)
