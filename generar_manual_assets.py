#!/usr/bin/env python3
"""
generar_manual_assets.py — Inventario / manual de assets de la web.

Uso:
    python3 generar_manual_assets.py [archivo.html]

Analiza el HTML (por defecto index.html), lista todas las imágenes/iconos
que usa, las clasifica en locales / Google Drive / stock / CDN, comprueba
cuáles existen en disco y genera un manual en MANUAL_ASSETS.md.
"""
import os
import re
import sys
from collections import defaultdict

try:
    from PIL import Image
    HAS_PIL = True
except Exception:
    HAS_PIL = False

EXT = r"(?:png|jpe?g|webp|gif|svg|ico|avif)"
# Hosts de imagen cuyas URLs NO terminan en extensión (Drive, stock)
IMG_HOSTS = r"(?:lh3\.googleusercontent\.com|drive\.google\.com|images\.pexels\.com|[a-z0-9.-]*pexels[a-z0-9.-]*|images\.unsplash\.com)"
# src="...", href="...", url(...), literales en plantillas JS, y URLs de hosts de imagen
PATTERNS = [
    re.compile(r"""(?:src|href)\s*=\s*["']([^"']+\.""" + EXT + r""")["']""", re.I),
    re.compile(r"""url\(\s*['"]?([^'")]+\.""" + EXT + r""")['"]?\s*\)""", re.I),
    re.compile(r"""['"]([^'"]+\.""" + EXT + r""")['"]""", re.I),
    # URLs de Google Drive / stock (sin extensión limpia al final)
    re.compile(r"""['"](https?://""" + IMG_HOSTS + r"""/[^'"]+)['"]""", re.I),
]


def classify(u: str) -> str:
    ul = u.lower()
    if u.startswith("assets/") or (not u.startswith("http") and not u.startswith("//") and not u.startswith("data:")):
        return "LOCAL"
    if "googleusercontent" in ul or "drive.google" in ul:
        return "GOOGLE_DRIVE"
    if "pexels" in ul or "unsplash" in ul or "images." in ul:
        return "STOCK"
    if "data:" in ul:
        return "INLINE"
    return "CDN/EXTERNO"


def human(n: int) -> str:
    for unit in ("B", "KB", "MB"):
        if n < 1024:
            return f"{n:.0f} {unit}"
        n /= 1024
    return f"{n:.1f} GB"


def main():
    html = sys.argv[1] if len(sys.argv) > 1 else "index.html"
    if not os.path.isfile(html):
        alt = "index.html"
        print(f"[aviso] '{html}' no existe; uso '{alt}' en su lugar.")
        html = alt
    if not os.path.isfile(html):
        sys.exit(f"[error] no encuentro el HTML ({html}).")

    text = open(html, encoding="utf-8").read()

    found = {}  # url -> nº apariciones
    for pat in PATTERNS:
        for m in pat.finditer(text):
            u = m.group(1).strip()
            if u.startswith("data:"):
                continue
            found[u] = found.get(u, 0) + 1

    groups = defaultdict(list)
    for u, n in sorted(found.items()):
        groups[classify(u)].append((u, n))

    base = os.path.dirname(os.path.abspath(html))
    lines = []
    lines.append("# Manual de assets — Tabacalera Alfambra\n")
    lines.append(f"Generado a partir de `{html}`.\n")
    total = len(found)
    lines.append(f"**Total de assets referenciados:** {total}\n")

    # Resumen
    lines.append("## Resumen por tipo\n")
    lines.append("| Tipo | Nº |")
    lines.append("| --- | --- |")
    for k in ("LOCAL", "GOOGLE_DRIVE", "STOCK", "CDN/EXTERNO", "INLINE"):
        if groups.get(k):
            lines.append(f"| {k} | {len(groups[k])} |")
    lines.append("")

    # Locales
    lines.append("## Imágenes locales (`assets/`)\n")
    lines.append("| Archivo | ¿Existe? | Tamaño | Dimensiones | Usos |")
    lines.append("| --- | --- | --- | --- | --- |")
    missing = []
    for u, n in groups.get("LOCAL", []):
        path = os.path.join(base, u)
        exists = os.path.isfile(path)
        size = human(os.path.getsize(path)) if exists else "—"
        dims = "—"
        if exists and HAS_PIL:
            try:
                with Image.open(path) as im:
                    dims = f"{im.size[0]}×{im.size[1]}"
            except Exception:
                dims = "?"
        if not exists:
            missing.append(u)
        lines.append(f"| `{u}` | {'✅' if exists else '❌ FALTA'} | {size} | {dims} | {n} |")
    lines.append("")

    # Externas (a migrar)
    for key, title, note in [
        ("GOOGLE_DRIVE", "Google Drive (poco fiables — migrar a local)",
         "Estos enlaces pueden devolver recortes/miniaturas. Recomendado: descargarlos a `assets/img/`."),
        ("STOCK", "Fotos de stock / externas", "Considerar sustituir por fotos propias en `assets/img/`."),
        ("CDN/EXTERNO", "Otros externos / CDN", "Librerías o recursos servidos por CDN."),
    ]:
        if groups.get(key):
            lines.append(f"## {title}\n")
            lines.append(f"> {note}\n")
            for u, n in groups[key]:
                lines.append(f"- `{u}`  _(usos: {n})_")
            lines.append("")

    # Assets en disco NO referenciados (huérfanos)
    ref_local = {u for u, _ in groups.get("LOCAL", [])}
    on_disk = []
    assets_dir = os.path.join(base, "assets")
    if os.path.isdir(assets_dir):
        for root, _dirs, files in os.walk(assets_dir):
            for fn in files:
                rel = os.path.relpath(os.path.join(root, fn), base).replace("\\", "/")
                if re.search(r"\." + EXT + r"$", fn, re.I):
                    on_disk.append(rel)
    orphans = sorted(set(on_disk) - ref_local)
    if orphans:
        lines.append("## Assets en disco no usados en el HTML\n")
        for o in orphans:
            lines.append(f"- `{o}`")
        lines.append("")

    out = os.path.join(base, "MANUAL_ASSETS.md")
    open(out, "w", encoding="utf-8").write("\n".join(lines))

    # Salida por consola
    print(f"Assets referenciados : {total}")
    for k in ("LOCAL", "GOOGLE_DRIVE", "STOCK", "CDN/EXTERNO"):
        if groups.get(k):
            print(f"  {k:14}: {len(groups[k])}")
    print(f"Locales que FALTAN   : {len(missing)}" + (f" -> {missing}" if missing else ""))
    print(f"Assets huérfanos     : {len(orphans)}")
    print(f"Manual escrito en    : {out}")


if __name__ == "__main__":
    main()
