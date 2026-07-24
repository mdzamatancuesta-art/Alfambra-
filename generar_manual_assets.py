#!/usr/bin/env python3
"""
MADEX — Generador de Manual de Marca + Assets
==============================================
Uso:  python3 generar_manual_assets.py <archivo.html> [carpeta_salida]

Genera automáticamente desde un HTML auto-contenido (con imágenes base64):
  1. manual/MADEX_Manual_de_Marca.html  — manual de marca visual
  2. assets/img/                        — imágenes extraídas (jpeg/webp/png)
  3. assets/img/galeria/                — galería si existe .sceno-img
  4. assets/img/proyectos/              — tarjetas de proyectos
  5. assets/iconos/                     — iconos embebidos
  6. assets/fuentes/FUENTES.txt        — referencia de fuentes
  7. assets/INDICE_ASSETS.html         — índice visual con miniaturas
  8. MADEX_imagenes.zip                — ZIP con todas las imágenes
"""

import sys, re, os, base64, hashlib, zipfile, json
from pathlib import Path
from collections import OrderedDict

# ─────────────────────────────────────────────────────────────────
# 0. ARGUMENTOS
# ─────────────────────────────────────────────────────────────────
if len(sys.argv) < 2:
    print(__doc__)
    sys.exit(1)

html_path = Path(sys.argv[1]).resolve()
out_dir   = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else html_path.parent

print(f"\n{'='*60}")
print(f"  Procesando: {html_path.name}")
print(f"  Salida:     {out_dir}")
print(f"{'='*60}\n")

with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

# Nombre de marca (del <title>) para rotular el manual
_title_m = re.search(r'<title>([^<]+)</title>', html, re.I)
BRAND = _title_m.group(1).strip() if _title_m else html_path.stem

# ─────────────────────────────────────────────────────────────────
# 1. EXTRAER VARIABLES CSS (colores, fuentes)
# ─────────────────────────────────────────────────────────────────
def extract_css_vars(html):
    root_match = re.search(r':root\s*\{([^}]+)\}', html, re.DOTALL)
    if not root_match:
        return {}
    vars_ = {}
    for m in re.finditer(r'--([\w-]+)\s*:\s*([^;]+);', root_match.group(1)):
        vars_[f'--{m.group(1)}'] = m.group(2).strip()
    return vars_

css_vars = extract_css_vars(html)
print(f"[CSS] Variables encontradas: {len(css_vars)}")

# Clasificar colores y fuentes
colors = {k: v for k, v in css_vars.items() if v.startswith('#') or v.startswith('rgb')}
fonts  = {k: v for k, v in css_vars.items() if 'font' in k or 'family' in k.lower()}
print(f"  Colores: {list(colors.items())}")
print(f"  Fuentes: {list(fonts.items())}")

# Alias para que el PROPIO manual use la paleta de Alfambra (no aparecen como swatches)
_alias = {
    '--primary':   css_vars.get('--gold', '#f5b728'),
    '--primary-d': '#d9990f',
    '--primary-l': '#f5d488',
    '--d1':        css_vars.get('--black', '#0D0D0D'),
    '--d2':        '#0A3A20',
    '--g1':        '#6b6b66',
    '--g2':        '#d9d6cf',
    '--g3':        '#efece5',
    '--white':     '#ffffff',
    '--off-white': css_vars.get('--ivory', '#F8F6F2'),
    '--font-head': "'Instrument Serif'",
    '--font-body': "'Instrument Serif'",
}
for _k, _v in _alias.items():
    css_vars.setdefault(_k, _v)

# ─────────────────────────────────────────────────────────────────
# 2. EXTRAER FUENTES GOOGLE
# ─────────────────────────────────────────────────────────────────
gf_links = re.findall(r'href="(https://fonts\.googleapis\.com/css2[^"]+)"', html)
gf_families = []
for link in gf_links:
    for fam in re.findall(r'family=([A-Za-z+]+)', link):
        gf_families.append(fam.replace('+', ' '))
gf_families = list(OrderedDict.fromkeys(gf_families))
print(f"[Fonts] Google Fonts: {gf_families}")

# ─────────────────────────────────────────────────────────────────
# 3. EXTRAER IMÁGENES BASE64
# ─────────────────────────────────────────────────────────────────
img_pattern = re.compile(r'data:image/([a-zA-Z+]+);base64,([A-Za-z0-9+/=]+)')
all_matches = list(img_pattern.finditer(html))
print(f"\n[Imgs] Total data URIs: {len(all_matches)}")

ext_map = {'jpeg': 'jpg', 'jpg': 'jpg', 'webp': 'webp', 'png': 'png', 'gif': 'gif', 'svg+xml': 'svg'}

def get_context(html, match, chars=300):
    start = max(0, match.start() - chars)
    return html[start:match.start()].replace('\n', ' ').strip()

def classify_image(ctx, mime):
    """Clasifica una imagen según su contexto HTML."""
    if '.hero-bg' in ctx or 'hero-bg' in ctx:
        return 'portada', 'portada_hero', 'img', 'Fondo hero/portada principal'
    if 'intro-sierra' in ctx or 'sierra' in ctx.lower():
        return 'icono', 'icono_sierra', 'iconos', 'Icono sierra (animación intro)'
    if 'nav-logo' in ctx or 'footer' in ctx and mime == 'webp':
        return 'logo', 'logo_madex', 'img', 'Logo MADEX (nav + footer)'
    if 'intro-logo' in ctx:
        return 'logo', 'logo_madex', 'img', 'Logo MADEX (intro)'
    if 'sceno-img' in ctx or 'openLightbox' in ctx:
        idx = ctx.count('openLightbox') if 'openLightbox' in ctx else 0
        lb = re.search(r'openLightbox\((\d+)\)', ctx)
        n = lb.group(1) if lb else '0'
        tall = 'tall' in ctx
        wide = 'wide' in ctx
        suffix = '_tall' if tall else ('_wide' if wide else '')
        return 'galeria', f'galeria_{int(n)+1:02d}{suffix}', 'img/galeria', f'Escenografía galería #{n}'
    if 'project-card' in ctx or 'project-bg' in ctx:
        cat_m = re.search(r'data-cat="([^"]+)"', ctx)
        cat = cat_m.group(1) if cat_m else 'proyecto'
        return 'proyecto', None, 'img/proyectos', f'Tarjeta de proyecto ({cat})'
    if mime == 'svg+xml':
        return 'icono', None, 'iconos', 'Icono SVG'
    return 'otro', None, 'img', 'Imagen sin clasificar'

# Deduplicar por MD5 y clasificar
seen_md5   = {}   # md5 -> filename
cat_counts = {}   # category -> count (for naming)
images_info = []  # [{filename, rel_path, desc, usage, size_kb, ctx_preview}]

for idx, m in enumerate(all_matches):
    mime = m.group(1)
    data_b64 = m.group(2)
    md5 = hashlib.md5(data_b64.encode()).hexdigest()

    if md5 in seen_md5:
        continue  # duplicado

    ctx = get_context(html, m)
    cat, suggested_name, folder, desc = classify_image(ctx, mime)
    ext = ext_map.get(mime, mime.split('/')[-1])

    # Generar nombre si no hay sugerido
    if not suggested_name:
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
        n = cat_counts[cat]
        if cat == 'proyecto':
            cat_m = re.search(r'data-cat="([^"]+)"', ctx)
            cat_slug = cat_m.group(1) if cat_m else 'proy'
            suggested_name = f'proy_{cat_slug}_{n:02d}'
        elif cat == 'galeria':
            suggested_name = f'galeria_{n:02d}'
        else:
            suggested_name = f'{cat}_{n:02d}'
    else:
        # Evitar duplicar nombre base (logo aparece varias veces)
        if suggested_name in [i['base_name'] for i in images_info]:
            continue

    filename = f'{suggested_name}.{ext}'
    rel_path = f'assets/{folder}/{filename}'
    size_kb  = len(data_b64) * 3 // 4 // 1024

    images_info.append({
        'md5': md5,
        'mime': mime,
        'ext': ext,
        'base_name': suggested_name,
        'filename': filename,
        'folder': folder,
        'rel_path': rel_path,
        'cat': cat,
        'desc': desc,
        'size_kb': size_kb,
        'data_b64': data_b64,
        'ctx_preview': ctx[-120:],
    })
    seen_md5[md5] = filename

print(f"  Únicas: {len(images_info)}")
for img in images_info:
    print(f"    [{img['cat']:12s}] {img['filename']:45s} {img['size_kb']:4d} KB")

# ── Reserva: HTML que referencia ARCHIVOS locales (no base64) ──
if not images_info:
    img_ext = r'(?:png|jpe?g|webp|gif|svg)'
    file_refs = re.findall(r'(assets/[\w./-]+\.' + img_ext + r')', html, re.I)
    seen_ref = set()
    for ref in file_refs:
        if ref in seen_ref:
            continue
        seen_ref.add(ref)
        src_file = html_path.parent / ref
        if not src_file.is_file():
            continue
        raw = src_file.read_bytes()
        ext = src_file.suffix.lstrip('.').lower()
        mime = 'jpeg' if ext == 'jpg' else ext
        low = ref.lower()
        if 'logo' in low:                     cat, desc = 'logo', 'Logo / marca'
        elif 'hero' in low:                   cat, desc = 'portada', 'Cabecero / hero'
        elif 'product' in low:                cat, desc = 'producto', 'Foto de producto'
        elif 'humidor' in low:                cat, desc = 'producto', 'Humidor'
        elif 'news' in low or 'vida' in low:  cat, desc = 'estilo', 'Estilo de vida'
        elif 'gate' in low or 'trama' in low: cat, desc = 'decorativo', 'Elemento decorativo'
        elif 'bodegon' in low or 'lineup' in low or 'catalog' in low: cat, desc = 'portada', 'Bodegón / gama'
        else:                                 cat, desc = 'otro', 'Imagen'
        images_info.append({
            'md5': hashlib.md5(raw).hexdigest(), 'mime': mime, 'ext': ext,
            'base_name': src_file.stem, 'filename': src_file.name, 'folder': 'img',
            'rel_path': f'assets/img/{src_file.name}', 'cat': cat,
            'desc': f'{desc} — {ref}', 'size_kb': max(1, len(raw)//1024),
            'data_b64': None, 'bytes': raw, 'ctx_preview': ref,
        })
    print(f"  (reserva archivos) imágenes referenciadas: {len(images_info)}")

# ─────────────────────────────────────────────────────────────────
# 4. CREAR CARPETAS
# ─────────────────────────────────────────────────────────────────
folders_needed = set(img['folder'] for img in images_info)
for folder in ['assets', 'assets/img', 'assets/img/galeria', 'assets/img/proyectos',
               'assets/iconos', 'assets/fuentes', 'manual']:
    (out_dir / folder).mkdir(parents=True, exist_ok=True)
for folder in folders_needed:
    (out_dir / 'assets' / folder).mkdir(parents=True, exist_ok=True)

print("\n[Dir] Carpetas creadas.")

# ─────────────────────────────────────────────────────────────────
# 5. GUARDAR IMÁGENES
# ─────────────────────────────────────────────────────────────────
for img in images_info:
    path = out_dir / 'assets' / img['folder'] / img['filename']
    data = base64.b64decode(img['data_b64']) if img.get('data_b64') else img['bytes']
    with open(path, 'wb') as f:
        f.write(data)
print(f"[Imgs] {len(images_info)} imágenes guardadas.")

# ─────────────────────────────────────────────────────────────────
# 6. FUENTES TXT
# ─────────────────────────────────────────────────────────────────
fuentes_txt = "FUENTES TIPOGRÁFICAS\n" + "="*40 + "\n\n"
for fam in gf_families:
    fuentes_txt += f"• {fam}\n  https://fonts.google.com/specimen/{fam.replace(' ', '+')}\n\n"
fuentes_txt += "\nLink de carga HTML:\n"
for link in gf_links:
    fuentes_txt += f'<link href="{link}" rel="stylesheet">\n'
fuentes_txt += "\nNOTA RGPD: Servir localmente en WordPress para cumplir normativa europea.\n"
fuentes_txt += "Herramienta: https://gwfh.mranftl.com/fonts\n"

with open(out_dir / 'assets' / 'fuentes' / 'FUENTES.txt', 'w') as f:
    f.write(fuentes_txt)
print("[Fonts] FUENTES.txt generado.")

# ─────────────────────────────────────────────────────────────────
# 7. GENERAR MANUAL DE MARCA HTML
# ─────────────────────────────────────────────────────────────────
def color_card(var, hex_val, name, usage):
    text_color = '#ffffff' if hex_val.lower() not in ['#ffffff','#faf8f5','#eaeaea','#d1d6db'] else '#0F0F0D'
    return f"""
    <div class="swatch">
      <div class="swatch-box" style="background:{hex_val};color:{text_color}">
        <span>{hex_val}</span>
      </div>
      <div class="swatch-meta">
        <strong>{name}</strong>
        <code>{var}</code>
        <span>{usage}</span>
      </div>
    </div>"""

# Mapear variables a nombres legibles
COLOR_NAMES = {
    '--gold':  ('Dorado Alfambra', 'Acentos, botones/CTA, iconos, logos y detalles premium'),
    '--black': ('Negro',           'Texto principal, secciones oscuras, nav y footer'),
    '--ivory': ('Marfil',          'Fondo general claro de la web'),
    '--green': ('Verde Alhambra',  'Nav, franja destacada, verificación de edad y marca'),
}

color_cards_html = ''
for var, hex_val in colors.items():
    if var in COLOR_NAMES:
        name, usage = COLOR_NAMES[var]
    else:
        name = var.replace('--', '').replace('-', ' ').title()
        usage = ''
    color_cards_html += color_card(var, hex_val, name, usage)

# Font cards
font_cards_html = ''
for fam in gf_families:
    role = fonts.get('--font-head', '').replace("'","").strip().split(',')[0]
    var_label = '--font-head' if fam.replace(' ','') in role.replace(' ','') else '--font-body'
    usage_label = 'Títulos, headings H1–H3, botones, nav, logo' if 'head' in var_label else 'Párrafos, formularios, etiquetas, nav links'
    font_cards_html += f"""
    <div class="font-card">
      <div class="font-demo" style="font-family:'{fam}',sans-serif;">{fam}</div>
      <div class="font-meta">
        <code>{var_label}</code> · Google Fonts ·
        <a href="https://fonts.google.com/specimen/{fam.replace(' ','+')}" target="_blank">Ver en Google Fonts →</a>
      </div>
      <div class="font-use">{usage_label}</div>
    </div>"""

# Pages from showPage calls
pages_found = re.findall(r"showPage\('([^']+)'\)", html)
pages_unique = list(OrderedDict.fromkeys(pages_found))

pages_rows = ''
page_labels = {
    'home': ('Inicio', 'Portada. Hero con carrusel, filosofía (fondo negro) y franja destacada "Colección 1984" (verde).', 'Verde translúcido'),
    'tienda': ('Productos', 'Marcas por línea con banner + descripción y rejilla de vitolas (render dinámico).', 'Clara'),
    'productos': ('Humidor', 'Humidores Alfambra Simple y Doble con ficha técnica completa.', 'Clara'),
    'finder': ('Encuentra tu Puro', 'Buscador de vitolas por marca, fortaleza, cepo y tamaño (oculto en el menú).', 'Clara'),
    'about': ('Nosotros', 'Historia de la casa, ciclo de producción y galería.', 'Clara'),
    'catalogue': ('Catálogo', 'Catálogos descargables por línea (Completo, El Brujito, Alejandro Mata).', 'Clara'),
    'news': ('Noticias', 'Listado de novedades (masonry) con páginas de artículo dinámicas.', 'Clara'),
    'contact': ('Contacto', 'Datos reales, redes sociales y formulario.', 'Clara'),
    'vitola': ('Ficha de producto', 'Página individual de cada vitola: imagen, fortaleza, cepo, galería (2 fotos) y maridaje.', 'Clara'),
}
for pid in pages_unique:
    label, desc, nav = page_labels.get(pid, (pid.title(), '', '—'))
    pages_rows += f'<tr><td><code>page-{pid}</code></td><td><strong>{label}</strong></td><td>{desc}</td><td>{nav}</td></tr>\n'

# JS functions
js_fns = {
    'showPage(id)': 'Navega entre secciones .page añadiendo/quitando .active; dispara render de tienda/finder y los reveals.',
    'dismissAgeGate()': 'Cierra la verificación de edad: los paneles dorados se abren como puertas y revelan la web.',
    'playHero()': 'Reinicia la animación de entrada del título del hero.',
    'toggleMobileNav() / mobileGo(id)': 'Abre/cierra el menú hamburguesa móvil; mobileGo navega y lo cierra.',
    'setSiteLang("es"|"en")': 'Cambia el idioma de toda la web vía Google Translate (persiste en cookie googtrans).',
    'renderLines()': 'Pinta la página Productos (banner por marca + rejilla de vitolas) desde brandLines.',
    'showVitola(brandId, index)': 'Genera la ficha individual de una vitola (imagen, fortaleza, cepo, galería, maridaje).',
    'gotoLinea(id)': 'Va a Productos y hace scroll a la marca indicada (desde el desplegable del menú).',
    'updateFinderResults()': 'Filtra las vitolas del buscador por marca, fortaleza, cepo y tamaño.',
    'showNews(id) / renderNewsPage(id)': 'Abre la página de un artículo de noticias (render dinámico).',
    'downloadPDF(line)': 'Descarga el catálogo de la línea en el idioma elegido.',
    'setCookieConsent(bool)': 'Guarda la elección de cookies en localStorage y oculta el banner.',
}
fn_cards_html = ''.join(
    f'<div class="fn-card"><h4>{fn}</h4><p>{desc}</p></div>'
    for fn, desc in js_fns.items()
)

# i18n keys sample
i18n_sample = re.findall(r"'(nav_\w+|hero_\w+|form_\w+|btn_\w+|ck_\w+|ft_\w+)':\s*'([^']*)'", html)[:24]
i18n_rows = ''.join(
    f'<div class="key-row"><span class="key-name">{k}</span><span class="key-val">{v[:60]}</span></div>'
    for k, v in i18n_sample
)

# localStorage keys
ls_keys = [
    ('alfambra_cookies', 'localStorage', "'accepted' | 'rejected'", 'Respuesta al banner de cookies'),
    ('googtrans', 'cookie', "'/es/en' | '/es/es'", 'Idioma activo (Google Translate)'),
]
ls_rows = ''.join(
    f'<tr><td><code>{k}</code></td><td>{t}</td><td><code>{v}</code></td><td>{u}</td></tr>'
    for k, t, v, u in ls_keys
)

manual_html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Manual de Marca — {BRAND}</title>
{"".join(f'<link href="{l}" rel="stylesheet">' for l in gf_links)}
<style>
:root {{
  {''.join(f'{k}:{v};' for k,v in css_vars.items())}
}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:var(--font-body,'Roboto',sans-serif);background:var(--off-white,#FAF8F5);color:var(--d1,#0F0F0D);line-height:1.6}}
.cover{{background:var(--d1);color:#fff;padding:64px 5% 48px;border-bottom:4px solid var(--primary)}}
.cover-tag{{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--primary);font-weight:600;margin-bottom:12px}}
.cover h1{{font-family:var(--font-head,'Archivo',sans-serif);font-size:clamp(32px,6vw,72px);font-weight:900;line-height:1}}
.cover h1 em{{color:var(--primary);font-style:normal}}
.cover p{{font-size:14px;color:rgba(255,255,255,.45);font-weight:300;margin-top:12px;max-width:520px}}
.toc{{background:var(--d2,#1A1915);padding:0 5%;display:flex;flex-wrap:wrap;gap:0}}
.toc a{{font-size:11px;font-weight:600;letter-spacing:.1em;text-transform:uppercase;color:rgba(255,255,255,.35);text-decoration:none;padding:15px 18px;border-bottom:2px solid transparent;white-space:nowrap}}
.toc a:hover{{color:var(--primary);border-bottom-color:var(--primary)}}
.sec{{padding:56px 5%;max-width:1100px;margin:0 auto;border-bottom:1px solid var(--g3,#eaeaea)}}
.sec-label{{font-size:11px;letter-spacing:.16em;text-transform:uppercase;color:var(--primary);font-weight:600;margin-bottom:8px}}
.sec-h2{{font-family:var(--font-head,'Archivo',sans-serif);font-size:clamp(22px,3vw,36px);font-weight:800;margin-bottom:28px}}
.rule{{width:40px;height:2px;background:var(--primary);margin:0 0 28px}}
/* Swatches */
.swatches{{display:flex;flex-wrap:wrap;gap:20px}}
.swatch{{min-width:140px;display:flex;flex-direction:column;gap:8px}}
.swatch-box{{height:88px;border-radius:6px;display:flex;align-items:flex-end;padding:8px 10px;font-family:monospace;font-size:12px;font-weight:700;border:1px solid rgba(0,0,0,.06)}}
.swatch-meta{{display:flex;flex-direction:column;gap:2px}}
.swatch-meta strong{{font-family:var(--font-head,'Archivo',sans-serif);font-size:13px}}
.swatch-meta code{{font-size:11px;background:var(--g3,#eaeaea);padding:1px 5px;border-radius:3px;color:var(--d1);font-family:monospace;width:fit-content}}
.swatch-meta span{{font-size:11px;color:var(--g1,#6B7380);font-weight:300;line-height:1.4}}
/* Fonts */
.font-card{{background:#fff;border:1px solid var(--g3,#eaeaea);border-radius:6px;padding:28px;margin-bottom:14px}}
.font-demo{{font-size:42px;font-weight:900;margin-bottom:6px}}
.font-meta{{font-size:12px;color:var(--g1,#6B7380);margin-bottom:6px}}
.font-meta code{{background:var(--g3,#eaeaea);padding:1px 5px;border-radius:3px}}
.font-meta a{{color:var(--primary)}}
.font-use{{font-size:12px;color:var(--g1,#6B7380);font-weight:300}}
/* Pages table */
table{{width:100%;border-collapse:collapse;font-size:13px}}
th{{background:var(--d1);color:#fff;padding:10px 14px;text-align:left;font-size:11px;letter-spacing:.1em;text-transform:uppercase}}
td{{padding:10px 14px;border-bottom:1px solid var(--g3,#eaeaea);vertical-align:top}}
tr:hover td{{background:var(--off-white,#FAF8F5)}}
td code{{background:var(--g3,#eaeaea);padding:1px 5px;border-radius:3px;font-size:11px;font-family:monospace}}
/* JS fns */
.fn-grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}
@media(max-width:600px){{.fn-grid{{grid-template-columns:1fr}}}}
.fn-card{{background:var(--d2,#1A1915);border-radius:6px;padding:18px 20px;border-left:3px solid var(--primary)}}
.fn-card h4{{font-family:monospace;font-size:14px;color:var(--primary-l,#F2C4B6);margin-bottom:6px}}
.fn-card p{{font-size:12px;color:rgba(255,255,255,.5);font-weight:300;line-height:1.5}}
/* i18n */
.key-grid{{display:grid;grid-template-columns:1fr 1fr;gap:8px}}
.key-row{{display:flex;gap:10px;padding:7px 12px;background:#fff;border:1px solid var(--g3,#eaeaea);border-radius:4px;font-size:12px}}
.key-name{{font-family:monospace;color:#c03c10;font-size:11px;white-space:nowrap;min-width:120px}}
.key-val{{color:var(--g1,#6B7380);font-weight:300}}
/* Tree */
.tree{{background:var(--d2,#1A1915);border-radius:6px;padding:22px 26px;font-family:monospace;font-size:13px;color:rgba(255,255,255,.55);line-height:2;overflow-x:auto}}
.tree .d{{color:var(--primary-l,#F2C4B6);font-weight:700}}
.tree .c{{color:rgba(255,255,255,.22);font-style:italic}}
footer{{background:var(--d2,#1A1915);padding:28px 5%;text-align:center;font-size:11px;color:rgba(255,255,255,.2);letter-spacing:.08em;text-transform:uppercase;margin-top:40px}}
</style>
</head>
<body>

<div class="cover">
  <div class="cover-tag">Manual de Marca · {BRAND}</div>
  <h1>Brand<br><em>Manual</em></h1>
  <p>Referencia de diseño generada automáticamente desde <strong>{html_path.name}</strong>. Incluye colores, tipografía, componentes, páginas, traducciones y funciones JS.</p>
</div>

<nav class="toc">
  <a href="#colores">01 Colores</a>
  <a href="#tipografia">02 Tipografía</a>
  <a href="#paginas">03 Páginas</a>
  <a href="#i18n">04 Traducciones</a>
  <a href="#funciones">05 Funciones JS</a>
  <a href="#storage">06 localStorage</a>
  <a href="#archivos">07 Assets</a>
</nav>

<!-- 01 COLORES -->
<div id="colores" class="sec">
  <div class="sec-label">01</div>
  <h2 class="sec-h2">Paleta de Colores</h2>
  <div class="rule"></div>
  <p style="font-size:13px;color:var(--g1);margin-bottom:28px;font-weight:300">
    Variables CSS definidas en <code style="background:var(--g3);padding:1px 5px;border-radius:3px;">:root</code>.
    Usar siempre las variables, nunca valores hexadecimales directos.
  </p>
  <div class="swatches">{color_cards_html}</div>
</div>

<!-- 02 TIPOGRAFÍA -->
<div id="tipografia" class="sec">
  <div class="sec-label">02</div>
  <h2 class="sec-h2">Tipografía</h2>
  <div class="rule"></div>
  {font_cards_html}
  <div style="background:var(--d2);border-radius:6px;padding:18px 22px;margin-top:10px">
    <p style="font-size:12px;color:rgba(255,255,255,.4);font-weight:300;line-height:1.7">
      ⚠ <strong style="color:rgba(255,255,255,.7)">RGPD WordPress:</strong>
      Descargar fuentes en <a href="https://gwfh.mranftl.com" style="color:var(--primary)">gwfh.mranftl.com</a>
      y servirlas localmente, o usar el plugin OMGF para evitar transferencia de IPs a Google.
    </p>
  </div>
</div>

<!-- 03 PÁGINAS -->
<div id="paginas" class="sec">
  <div class="sec-label">03</div>
  <h2 class="sec-h2">Páginas (SPA)</h2>
  <div class="rule"></div>
  <p style="font-size:13px;color:var(--g1);margin-bottom:20px;font-weight:300">
    Sitio de página única. Función <code style="background:var(--g3);padding:1px 5px;border-radius:3px;">showPage(id)</code>
    activa/desactiva la clase <code style="background:var(--g3);padding:1px 5px;border-radius:3px;">.active</code>.
  </p>
  <table><thead><tr><th>ID</th><th>Página</th><th>Descripción</th><th>Nav</th></tr></thead>
  <tbody>{pages_rows}</tbody></table>
</div>

<!-- 04 IDIOMA -->
<div id="i18n" class="sec">
  <div class="sec-label">04</div>
  <h2 class="sec-h2">Idioma (Español / Inglés)</h2>
  <div class="rule"></div>
  <p style="font-size:13px;color:var(--g1);margin-bottom:20px;font-weight:300">
    Selector <strong>ES / EN</strong> a la derecha del menú. Traduce <strong>toda la web</strong>
    (incluido el contenido dinámico) mediante <strong>Google Translate</strong> con su interfaz
    nativa oculta por CSS; el idioma se recuerda en la cookie
    <code style="background:var(--g3);padding:1px 5px;border-radius:3px;">googtrans</code>.
    Función: <code style="background:var(--g3);padding:1px 5px;border-radius:3px;">setSiteLang('es'|'en')</code>.
  </p>
  <p style="font-size:12px;color:var(--g1);font-weight:300">
    Nota: solo funciona en el sitio publicado (requiere red). Para una traducción de marca con
    control total se usaría un diccionario i18n manual con <code style="background:var(--g3);padding:1px 5px;border-radius:3px;">data-i18n</code>.
  </p>
</div>

<!-- 05 FUNCIONES JS -->
<div id="funciones" class="sec">
  <div class="sec-label">05</div>
  <h2 class="sec-h2">Funciones JavaScript</h2>
  <div class="rule"></div>
  <div class="fn-grid">{fn_cards_html}</div>
</div>

<!-- 06 LOCALSTORAGE -->
<div id="storage" class="sec">
  <div class="sec-label">06</div>
  <h2 class="sec-h2">localStorage</h2>
  <div class="rule"></div>
  <table><thead><tr><th>Clave</th><th>Tipo</th><th>Valores</th><th>Uso</th></tr></thead>
  <tbody>{ls_rows}</tbody></table>
</div>

<!-- 07 ASSETS -->
<div id="archivos" class="sec">
  <div class="sec-label">07</div>
  <h2 class="sec-h2">Estructura de Assets</h2>
  <div class="rule"></div>
  <div class="tree">
    <span class="d">assets/</span><br>
    {''.join(f'├── <span class="d">{img["folder"].split("/")[-1] if "/" in img["folder"] else img["folder"]}/</span> {img["filename"]} <span class="c">← {img["desc"]} ({img["size_kb"]} KB)</span><br>' for img in images_info)}
    ├── <span class="d">fuentes/</span> FUENTES.txt<br>
    └── INDICE_ASSETS.html
  </div>
</div>

<footer>{BRAND} · Manual de Marca generado automáticamente</footer>
</body>
</html>"""

manual_path = out_dir / 'manual' / 'Alfambra_Manual_de_Marca.html'
with open(manual_path, 'w', encoding='utf-8') as f:
    f.write(manual_html)
print(f"\n[Manual] Guardado en: {manual_path}")

# ─────────────────────────────────────────────────────────────────
# 8. GENERAR ÍNDICE DE ASSETS HTML
# ─────────────────────────────────────────────────────────────────
img_cards_html = ''
for img in images_info:
    # Relative path from assets/INDICE_ASSETS.html to image
    img_rel = img['rel_path'].replace('assets/', '')
    cat_color = {
        'portada': '#E8501D', 'logo': '#333', 'galeria': '#E8501D',
        'proyecto': '#2d3a4a', 'icono': '#2d4a2d', 'otro': '#555'
    }.get(img['cat'], '#555')
    img_cards_html += f"""
    <div style="background:#fff;border:1px solid #eaeaea;border-radius:6px;overflow:hidden">
      <img src="{img_rel}" alt="{img['desc']}"
           style="width:100%;height:150px;object-fit:cover;display:block;background:#eaeaea">
      <div style="padding:12px 14px">
        <div style="font-weight:700;font-size:13px;margin-bottom:2px">{img['desc']}</div>
        <div style="font-family:monospace;font-size:11px;color:#c03c10;margin-bottom:4px">{img['rel_path']}</div>
        <div style="font-size:11px;color:#6B7380">{img['size_kb']} KB · {img['mime'].upper()}</div>
        <span style="display:inline-block;margin-top:6px;background:{cat_color};color:#fff;font-size:9px;font-weight:700;padding:2px 7px;border-radius:2px;letter-spacing:.08em;text-transform:uppercase">{img['cat']}</span>
      </div>
    </div>"""

index_html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Índice de Assets — {html_path.stem}</title>
{"".join(f'<link href="{l}" rel="stylesheet">' for l in gf_links)}
<style>
:root{{{' '.join(f'{k}:{v};' for k,v in css_vars.items())}}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:var(--font-body,'Roboto',sans-serif);background:var(--off-white,#faf8f5);color:var(--d1,#0f0f0d)}}
header{{background:var(--d1);padding:48px 5% 36px;border-bottom:3px solid var(--primary)}}
.tag{{font-size:11px;letter-spacing:.14em;text-transform:uppercase;color:var(--primary);font-weight:600;margin-bottom:10px}}
h1{{font-family:var(--font-head,'Archivo',sans-serif);font-size:clamp(28px,5vw,52px);font-weight:900;color:#fff}}
header p{{font-size:13px;color:rgba(255,255,255,.45);font-weight:300;margin-top:8px}}
.sec{{padding:48px 5%;max-width:1200px;margin:0 auto}}
.sec-title{{font-family:var(--font-head,'Archivo',sans-serif);font-size:11px;font-weight:700;letter-spacing:.16em;text-transform:uppercase;color:var(--primary);margin-bottom:8px}}
.sec-h2{{font-family:var(--font-head,'Archivo',sans-serif);font-size:clamp(20px,3vw,32px);font-weight:800;margin-bottom:28px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:18px}}
footer{{background:var(--d2,#1A1915);padding:24px 5%;text-align:center;font-size:11px;color:rgba(255,255,255,.2);letter-spacing:.08em;text-transform:uppercase;margin-top:40px}}
</style>
</head>
<body>
<header>
  <div class="tag">Índice de Assets · {BRAND}</div>
  <h1>Assets del Sitio Web</h1>
  <p>{len(images_info)} imágenes únicas extraídas de {html_path.name}</p>
</header>
<div class="sec">
  <div class="sec-title">Imágenes</div>
  <h2 class="sec-h2">Todas las Imágenes</h2>
  <div class="grid">{img_cards_html}</div>
</div>
<div class="sec" style="border-top:1px solid var(--g3)">
  <div class="sec-title">Fuentes</div>
  <h2 class="sec-h2">Tipografías</h2>
  {''.join(f'<div style="background:#fff;border:1px solid #eaeaea;border-radius:6px;padding:24px;margin-bottom:12px"><div style="font-family:\'{f}\',sans-serif;font-size:36px;font-weight:900;margin-bottom:6px">{f}</div><div style="font-size:12px;color:#6B7380">Google Fonts · <a href="https://fonts.google.com/specimen/{f.replace(chr(32),chr(43))}" style="color:#E8501D">Ver →</a></div></div>' for f in gf_families)}
</div>
<footer>{BRAND} · Índice de Assets generado automáticamente</footer>
</body>
</html>"""

index_path = out_dir / 'assets' / 'INDICE_ASSETS.html'
with open(index_path, 'w', encoding='utf-8') as f:
    f.write(index_html)
print(f"[Index] Guardado en: {index_path}")

# ─────────────────────────────────────────────────────────────────
# 9. CREAR ZIP CON TODAS LAS IMÁGENES
# ─────────────────────────────────────────────────────────────────
stem = re.sub(r'[^A-Za-z0-9]+', '_', BRAND).strip('_') or html_path.stem
zip_path = out_dir / f'{stem}_imagenes.zip'
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
    for img in images_info:
        src = out_dir / 'assets' / img['folder'] / img['filename']
        zf.write(src, img['rel_path'])
    # Añadir índice y manual también
    zf.write(index_path, 'assets/INDICE_ASSETS.html')
    zf.write(manual_path, 'manual/Alfambra_Manual_de_Marca.html')
    zf.write(out_dir / 'assets' / 'fuentes' / 'FUENTES.txt', 'assets/fuentes/FUENTES.txt')

zip_kb = zip_path.stat().st_size // 1024
print(f"[ZIP] Creado: {zip_path.name} ({zip_kb} KB)")

# ─────────────────────────────────────────────────────────────────
# 10. RESUMEN FINAL
# ─────────────────────────────────────────────────────────────────
print(f"""
{'='*60}
  COMPLETADO
{'='*60}
  HTML analizado : {html_path.name}
  Carpeta salida : {out_dir}

  Archivos generados:
    manual/Alfambra_Manual_de_Marca.html  (manual de marca)
    assets/INDICE_ASSETS.html          (índice visual)
    assets/fuentes/FUENTES.txt         (referencia tipografías)
    {len(images_info)} imágenes en assets/img/ y assets/iconos/
    {zip_path.name} ({zip_kb} KB)

  Colores: {len(colors)}  |  Fuentes: {len(gf_families)}  |  Páginas: {len(pages_unique)}
{'='*60}
""")
