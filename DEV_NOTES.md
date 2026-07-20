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

Assets locales en `assets/img/`:
- `logos/` — logos (company-gold, footer-tabacalera, marcas, brujito, mata, tramas).
- `hero/` — fotos del carrusel de inicio.
- `products/` — fotos de puros/cajas por marca.
- `news/`, `vida/` — fotos de estilo de vida.
- `humidor-*.webp`, `catalog-header.webp`, `clasica-lineup.webp`, `gate-panel-*.webp`, `trama-box.webp`, etc.

## 2. Navegación (SPA)

Cada "página" es una `<section class="page" id="page-XXX">`. `showPage('xxx')` quita `.active` de todas y se la pone a la elegida (CSS: `.page{display:none}` / `.page.active{display:block}`). No hay router ni URLs; todo es JS.

- **Menú escritorio:** `.nav-desktop` (visible en `md:` en adelante) — no tocar para no romper el diseño.
- **Menú móvil:** `.nav-mobile` + hamburguesa `#nav-burger` → despliega `#mobile-menu` (`toggleMobileNav()`, `mobileGo(id)`).
- **Desplegable "Productos":** `.nav-prod` (CSS hover), enlaza a marcas con `gotoLinea(id)`.

## 3. Datos de producto (lo más importante)

Dos estructuras JS al final del `<script>`:

- **`brandLines[]`** — 6 marcas (`brujito, verde, naranja, seleccion, gener, mata`). Cada una:
  `{ id, name, procedencia, fortaleza, envase, img{main}, cigarImg, gallery[], bannerLogo, logo, coleccion, lema, vitolas[{name, cepo, formato, largo, uds, img}] }`.
  - `cigarImg` = foto por defecto del puro de esa marca; `vitola.img` la sobreescribe.
  - `naranja` se muestra como **"Alfambra Serie Clásica"** (el `id` sigue siendo `naranja` para no romper anclas).
- **`cigars{}`** — textos por marca (`flavor_desc`, `tasting`, `intensity`, `pairing`, `sizes`, `tobacco`).

Renderizado:
- `renderLines()` pinta la página **Productos** (banner por marca + rejilla de vitolas). Marca con `coleccion` (Alejandro Mata) muestra logo + "Colección 1964" + lema.
- `showVitola(brandId, index)` genera la **página individual** del puro (imagen, ficha, barra de fortaleza, cepo, galería, maridaje, botón compartir).
- **Finder** (`page-finder`): `finderVitolas()` aplana todas las vitolas; `updateFinderResults()` filtra por marca / fortaleza (slider) / cepo / tamaño y pinta tarjetas con `showVitola`.

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

## 8. Imágenes de Google Drive (aviso)

Algunas fotos aún se enlazan por `lh3.googleusercontent.com/d/<ID>=w1920` con fallback a un asset local. Son **poco fiables** (pueden devolver recortes/miniaturas). **Recomendación:** descargar y servir todas las imágenes desde `assets/img/` como el resto.

## 9. Despliegue

GitHub Pages vía workflow `.github/workflows/static.yml`, que publica la rama por defecto. Push a la rama = nuevo despliegue automático.
