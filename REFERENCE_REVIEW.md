# Revisión de whisper-website

Repositorio: https://github.com/Kabanosk/whisper-website
Commit revisado: 5e2387f5e6f9fd9addacf2a96bbf34f1e6d9893f
Fecha: 05/11/2026. Se leyeron README, pyproject, Dockerfile, Compose, licencia, API, servicio de transcripción, caché, exportación de subtítulos, HTML y JavaScript.

| Área | Referencia | Decisión en Transcribe AI |
|---|---|---|
| Backend | FastAPI, Jinja2, ruta de descarga síncrona | FastAPI con frontend estático y endpoints de trabajos |
| Whisper | stable-ts/stable_whisper, PyTorch | Faster-Whisper/CTranslate2 int8 en CPU |
| Modelos | Caché en memoria por tamaño, lock, expulsión tras inactividad | Un modelo por proceso de trabajo; caché de archivos persistente; se libera RAM al terminar |
| Subida | Bytes completos en memoria, UUID temporal con extensión mp3 | Streaming con límite, UUID privado y extensión permitida; FFprobe verifica contenido |
| Procesamiento | La descarga espera la inferencia | Cola SQLite durable y proceso independiente, polling de estado |
| Exportación | TXT, SRT, VTT, fragmentación/puntuación de subtítulos | DOCX real desde texto editable, sin timestamps |
| Traducción | deep_translator/Google Translate para SRT | Omitida; ningún texto se envía a traducción externa |
| Web | Bootstrap CDN, modelos/subtítulos/opciones técnicas | CSS/JS locales, una página, idioma y dos fuentes de entrada |
| YouTube | No figura en el flujo revisado | yt-dlp con URL canónica y proxy de destinos públicos permitidos |
| Docker | Python 3.13, uv frozen lock, FFmpeg, usuario no root | Python 3.12, dependencias versionadas, FFmpeg, Node EJS, no root y límites |
| Persistencia | Volumen /root/.cache/whisper aunque el proceso ejecuta appuser | /models y /data propiedad de UID 10001, rutas explícitas |
| Seguridad | En el flujo revisado no se observan auth ni límites de subida | Auth previa a multipart, límites, cleanup, loopback, SSH y SSRF |

La estructura modular FastAPI/servicios y el uso de UUID son ideas útiles. Se evita cargar toda la subida en RAM, exponer modelos técnicos al usuario, traducir mediante servicios externos y exportar TXT bajo apariencia de Word. La aplicación no es un fork y no incorpora el código de la referencia. Su MIT original se conserva en THIRD_PARTY_NOTICES.md como atribución de la referencia estudiada.
