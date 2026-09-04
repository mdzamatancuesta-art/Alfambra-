# Tabacalera Alfambra — Notas para desarrollo

Sitio web de **Alfambra Boutique Cigars**. Explicación técnica para quien continúe el proyecto.

- **Producción:** https://mdzamatancuesta-art.github.io/Alfambra-/
- **Repo / rama de trabajo:** `claude/alfambra-dropbox-integration-3n7mk5` (es la rama por defecto; GitHub Pages despliega desde ella).
- Si no ves un cambio: espera ~1 min al despliegue y refresca con **Ctrl+F5** o añade `?v=N`.

---

## 1. Stack y estructura

Todo el sitio es **una sola página**: `index.html` (HTML + CSS + JS embebidos). No hay build.

Dependencias por CDN (se cargan en `<head>`):
- **Tailwind CSS** (`cdn.tailwindcss.com/3.4.17`) — utilidades. Usa arbitrary values (`w-[560px]`, `aspect-[4/3]`) → requiere el CDN JIT, no un CSS precompilado.
- **Instrument Serif** (Google Fonts) — tipografía principal (clase `.font-serif`).
- **Lucide** icons (`lucide.createIcons()` genera los `<i data-lucide="...">`).

Assets locales en `assets/img/` (todo local, **0 dependencias de imágenes externas**):
- `logos/` — logos **SVG** de marca en 3 variantes: color/dorado (`marca.svg`), blanco (`marca-white.svg`, para banners oscuros) y negro (`marca-black.svg`). Marcas: `boutique, seleccion, clasico, brujito, jg, mata, diamante, ediciones, tabacalera`. También quedan logos generales antiguos (`company-gold.webp`, `footer-tabacalera.webp`, `alfambra-gold.png`, `trama-*`).
- `vitolas/` — 62 PNG cuadrados por vitola, `{marca}__{slug}.png`.
- `bodegones/` — bodegones (fotos de producto) por línea: `bodegon-{boutique,seleccion,clasico,brujito,mata,diamante,col1964}.webp`. J·G usa el genérico `assets/img/bodegon.webp`.
- `hero/`, `news/`, `vida/` — fotos de campo / estilo de vida.
- `humidor-*.webp`, `catalog-header.webp`, `gate-panel-*.webp`, `favicon.png`, etc.

Catálogo descargable en `assets/pdf/Catalogo_Alfambra_Tabacalera_2026.pdf` (ver §7b).

## 2. Navegación (SPA)

Cada "página" es una `<section class="page" id="page-XXX">`. `showPage('xxx')` quita `.active` de todas y se la pone a la elegida (CSS: `.page{display:none}` / `.page.active{display:block}`). No hay router ni URLs; todo es JS.

- **Menú escritorio:** `.nav-desktop` (visible en `md:` en adelante) — no tocar para no romper el diseño.
- **Menú móvil:** `.nav-mobile` + hamburguesa `#nav-burger` → despliega `#mobile-menu` (`toggleMobileNav()`, `mobileGo(id)`).
- **Desplegable "Productos":** `.nav-prod` (CSS hover), enlaza a marcas con `gotoLinea(id)`.

## 3. Datos de producto (lo más importante)

Dos estructuras JS al final del `<script>`:

- **`brandLines[]`** — **9 líneas**, en el orden oficial del catálogo:
  `boutique, seleccion, clasico, brujito, jg, carmelita, maduro, diamante, col1964`.
  Cada una:
  `{ id, name, group?, procedencia, fortaleza, envase, capa, capote, tripa, img{main}, bodegon, cigarImg, bannerLogo, logo?, coleccion?, lema?, vitolas[{name, cepo, formato, largo, uds, fuerza, capa, capote, tripa, img}] }`.
  - **`group`** — agrupa líneas bajo un encabezado de sección en Productos: `carmelita` y `maduro` → `"Alejandro Mata"`; `diamante` y `col1964` → `"Ediciones Especiales"`. `renderLines()` pinta el encabezado cuando cambia el `group`.
  - **`img.main`** y **`bodegon`** apuntan al bodegón de la línea (foto de producto). `bannerLogo` = logo blanco (SVG) sobre el banner oscuro; `logo` = logo dorado que aparece en el bloque `coleccion` sobre marfil.
  - `cigarImg` = foto por defecto del puro; `vitola.img` la sobreescribe.
  - **`col1964`** = "Alejandro Mata – Colección 1964", edición especial (Ediciones Especiales): humidor con las 8 vitolas (Carmelita + Maduro) + botella Arzuaga. Se **excluye del buscador** en `finderVitolas()` para no duplicar vitolas.
- **`cigars{}`** — textos por línea (`name, strength, intensity, tasting, flavor_desc, pairing`).

Renderizado:
- `renderLines()` pinta la página **Productos** (encabezado de grupo cuando aplica + banner por línea + rejilla de vitolas). Línea con `coleccion` muestra logo + eyebrow + lema.
- `showVitola(brandId, index)` genera la **página individual** del puro (imagen, ficha con Cepo/Longitud/Capa/Capote/Tripa/Origen/Envase/Uds, barra de fortaleza, galería = puro + bodegón de la línea, maridaje, compartir).
- **Finder** (`page-finder`, oculto del menú): `finderVitolas()` aplana las vitolas (menos `col1964`); `updateFinderResults()` filtra por marca / fortaleza / cepo / tamaño.

**Para añadir/editar un puro:** edita `brandLines` (datos) y, si hace falta, `cigars` (textos). Nada más.

## 4. Animaciones de entrada

- **Verificación de edad (`#age-gate`):** paneles dorados (`.gate-panel`, imágenes `gate-panel-left/right.webp`) + tarjeta central sobre verde. Al pulsar **Confirmar** → `dismissAgeGate()` añade `.gate-open`: el centro se funde, el logo escala y los paneles se abren como puertas. En móvil (`@media max-width:640px`) los paneles se hacen finos para que el aviso ocupe el ancho.
- **Cortina de inicio (`#home-intro`):** `playIntro()` — dos paneles de trama verde que se separan revelando el hero (actualmente **no** se dispara desde el gate; el gate ya hace la apertura). El elemento y su CSS siguen disponibles por si se quiere reactivar.

## 5. Idioma ES/EN

Toggle en el menú (`.lang-toggle`, botones `.lang-btn`) → `setSiteLang('es'|'en')`. Usa el widget de **Google Translate** (`#google_translate_element`, script `translate.google.com/translate_a/element.js`) con su interfaz oculta por CSS y persistencia por cookie `googtrans`. Traduce **toda** la página, incluido el contenido dinámico. Solo funciona en el sitio publicado (necesita red).
> Si se quiere una traducción "de marca" con control total, habría que montar un diccionario i18n manual (mucho más trabajo).

## 6. Responsive

Escritorio intacto; el trabajo responsive es **aditivo**:
- Tipografías con `clamp(min, vw, MÁX)` donde el **máximo = tamaño original** (en escritorio se ve igual).
- Menú hamburguesa por debajo de `md`.
- Ajustes solo-móvil con prefijos `md:` o `@media (max-width:…)`.

## 7. Contacto / legal

Datos reales en `page-contact` y footer: **C. Zamora 3, Laguna de Duero (Valladolid), tel 607 65 48 22, 24h**. Footer con redes sociales, enlaces legales UE y **banner de cookies** (`#cookie-banner`, `setCookieConsent()`, `localStorage['alfambra_cookies']`).

## 7b. Catálogo descargable

Página **Catálogo** (`page-catalogue`): tarjetas con botón "Descargar catálogo". Toda la lógica está en un único sitio:
- `CATALOG_PDF` + mapa `CATALOGS` (por `line0/line1/line3`) → ruta del PDF local.
- `downloadPDF/previewPDF/sharePDF` usan `catUrl(line)`.
- Hoy hay **un solo PDF completo** (`assets/pdf/Catalogo_Alfambra_Tabacalera_2026.pdf`, ES) y las 3 tarjetas apuntan a él. Para servir catálogos por línea, añade su ruta en `CATALOGS`.

## 8. Imágenes

**Todas las imágenes son locales** (`assets/img/`); no queda ninguna dependencia externa (se migraron las de Google Drive/pexels). Al añadir fotos nuevas, guárdalas en `assets/img/` y referencia por ruta relativa.

## 9. Despliegue

GitHub Pages vía workflow `.github/workflows/static.yml`, que publica la rama por defecto. Push a la rama = nuevo despliegue automático.
