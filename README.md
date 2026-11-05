# Transcribe AI

Una página privada para subir audio/vídeo o pegar un enlace de YouTube, transcribir en el servidor y descargar un Word editable. Castellano, catalán y detección automática. Sin APIs comerciales de transcripción, sin escritorio gráfico.

## Instalación en tu Ubuntu Server desde PuTTY

Repositorio privado: autentica Git con una clave SSH de GitHub o un token mediante el gestor de credenciales. **No pongas tokens en la URL ni en comandos compartidos.** Una sesión de ChatGPT/GitHub no autentica automáticamente el servidor.

```bash
sudo apt-get update
sudo apt-get install -y git
# Requiere tu clave SSH de GitHub configurada en el servidor:
git clone git@github.com:christian810/transcribe-ai.git
cd transcribe-ai
sudo bash install.sh
sudo cat .env
```

Alternativa HTTPS: `git clone https://github.com/christian810/transcribe-ai.git` y autenticación interactiva (GitHub exige token, no la contraseña de la cuenta). Usa una clave de despliegue de solo lectura para este repositorio si el servidor solo necesita descargar actualizaciones.

`install.sh` admite Ubuntu 24.04 y 26.04, instala Docker desde el repositorio APT oficial con clave y `Signed-By`, comprueba Docker Compose v2, espacio libre, genera contraseña aleatoria y despliega. No ejecuta scripts remotos mediante curl|sh, no quita motores existentes ni añade usuarios al grupo docker. Si hay una instalación de Docker incompleta/conflictiva, se detiene explicándolo. No se ha probado aquí sobre una VM Ubuntu 26.04.1 real; consulta el informe de pruebas.

Recursos iniciales recomendados: 4 vCPU, 8 GB RAM de VM y 25–30 GB de disco ampliable. El contenedor limita CPU a 4 y RAM a 6 GB. `small`/int8 es el punto inicial para CPU; `medium` o `large-v3` pueden mejorar el catalán con más recursos y mucho más tiempo. No hay ajuste específico del dialecto de Formentera ni garantía de precisión bilingüe.

### Abrir la web de forma segura con PuTTY

El puerto solo escucha en `127.0.0.1` del servidor. En PuTTY:

1. Connection → SSH → Tunnels.
2. Source port: `8000`. Destination: `127.0.0.1:8000`.
3. Selecciona **Local**, pulsa **Add**, guarda la sesión y conéctate.
4. Abre `http://127.0.0.1:8000` en el navegador de Windows.
5. Introduce `APP_USER` y `APP_PASSWORD` de `.env`.

La conexión viaja cifrada dentro de SSH; no requiere entorno gráfico en Ubuntu. Copiar texto usa el portapapeles del navegador; si está restringido, selecciona el texto y usa Ctrl+C.

**Para otros equipos/móviles:** prepara un proxy HTTPS con certificado de confianza delante de la aplicación. Configura `PUBLIC_ORIGIN=https://tu-dominio` y añade ese hostname a `ALLOWED_HOSTS` (sin esquema ni puerto); el proxy debe conservar Host. Conectar a `http://IP:8000` directamente no cifra la autenticación Basic. No cambies `BIND_IP` a `0.0.0.0` ni abras puertos en el router. Para una red cerrada de confianza puedes enlazar a una IP privada concreta, pero habilita HTTPS antes de introducir credenciales por LAN. Docker puede evitar las reglas UFW de puertos publicados; no confíes únicamente en UFW.

## Uso

1. Arrastra o selecciona un MP3, WAV, M4A, FLAC, OGG, MP4, MKV, MOV o WEBM, **o** pega un enlace HTTPS de un vídeo de YouTube.
2. Elige automático, castellano o catalán y pulsa **Transcribir**.
3. Espera al procesamiento en segundo plano. El progreso de la transcripción es aproximado; subida/preparación/modelo se muestran por etapas.
4. Revisa y edita el texto. Pulsa **Descargar Word (.docx)** o **Copiar texto**.

El Word real, generado con python-docx, contiene título, archivo/título del vídeo, fecha de procesamiento en Europe/Madrid, idioma seleccionado/detectado y párrafos sin marcas de tiempo. La descarga envía el contenido actual del editor al servidor. Las ediciones no se autoguardan: al recargar se recupera el texto original; el último Word sí se conserva hasta su limpieza.

El primer trabajo necesita Internet para descargar el modelo abierto desde Hugging Face. Después se reutiliza el volumen de modelos. Para impedir nuevas descargas: precarga el modelo y fija `MODEL_OFFLINE=true`. La transcripción de archivos locales no envía audio a servicios externos; YouTube, por su naturaleza, necesita conectarse a YouTube/Google y puede denegar la descarga. No se saltan DRM, login, restricciones de edad, permisos ni bloqueos. yt-dlp incorpora componentes EJS con el extra `[default]` y usa Node 22 incluido en la imagen; no se habilita descarga de scripts remotos.

## Configuración (solo administrador, archivo .env)

| Variable | Valor inicial | Función |
|---|---|---|
| APP_USER / APP_PASSWORD | admin / generada | Cuenta compartida inicial, contraseña mínima 16 caracteres |
| BIND_IP / PORT | 127.0.0.1 / 8000 | Escucha solo por loopback |
| WHISPER_MODEL | small | Modelo Faster-Whisper o ruta local de modelo CTranslate2 |
| WHISPER_DEVICE / WHISPER_COMPUTE_TYPE | cpu / int8 | Motor inicial CPU |
| WHISPER_CPU_THREADS | 4 | Hilos de inferencia |
| MODEL_OFFLINE | false | No descargar modelos cuando es true |
| MAX_UPLOAD_MB | 500 | Máximo por subida y descarga YouTube |
| MAX_AUDIO_SECONDS | 14400 | Máximo 4 horas de audio |
| MAX_QUEUED_JOBS | 8 | En cola y procesándose, juntos |
| JOB_TIMEOUT_SECONDS | 21600 | Watchdog del trabajo completo (6 horas) |
| RETENTION_HOURS | 24 | Retención de resultados/Word desde la última actualización del trabajo |
| MEMORY_LIMIT / CPU_LIMIT | 6g / 4 | Límites Docker |

Recrea después de cambiar `.env`: `sudo docker compose up -d`. No uses `source .env`: es configuración, no un script. El tamaño de /tmp en Compose debe ser mayor que MAX_UPLOAD_MB (multipart crea un archivo temporal); ampliar el límite puede requerir más RAM/tmpfs y espacio de volumen. La extracción WAV usa unos 32 KB por segundo, además del original. Los valores deben ser positivos y razonables.

## Arquitectura y privacidad

- FastAPI sirve HTML/CSS/JS locales, sin CDN, y una API autenticada.
- SQLite en `/data` guarda cola, estado y transcripciones; un único supervisor procesa un trabajo cada vez en un proceso separado con Faster-Whisper. **Ejecutar siempre un solo worker Uvicorn y una sola réplica.**
- FFprobe valida el contenido real y la duración; FFmpeg extrae la primera pista de audio a WAV mono 16 kHz con protocolos limitados a archivos locales/pipe.
- VAD, umbral de ausencia de voz y desactivación de contexto previo reducen alucinaciones. No son una garantía absoluta: revisa el resultado, especialmente ruido, música, silencios y cambios de idioma.
- YouTube acepta solo IDs canónicos. Las descargas HTTPS usan un proxy local con dominios permitidos y conexión a una IP pública validada, para bloquear redirecciones/SSRF a IPs privadas, loopback o metadatos cloud. No se aceptan URLs arbitrarias ni opciones del usuario para yt-dlp.
- Sin `shell=True`, nombres internos UUID, límite de bytes de cuerpo y archivo, límite de cola, duración, subprocess timeout y watchdog. El contenedor ejecuta como UID 10001, sin capabilities, sin escalado de privilegios y sistema de archivos raíz de solo lectura. No es un antivirus ni una sandbox invulnerable: mantén FFmpeg y dependencias actualizados.
- Autenticación antes de analizar subidas, límite de intentos fallidos, comprobación de origen de escrituras, CSP, sin CORS público y sin logs de acceso con contenido. Una sola cuenta implica que sus usuarios pueden acceder a los trabajos de esa cuenta; no es multiusuario con separación de datos.
- Originales y audio extraído se eliminan al terminar, también tras error. Resultados y documentos se borran al caducar. Las subidas abandonadas se limpian tras una hora. Reinicios recuperan los trabajos en cola; un cierre forzado durante la inferencia puede requerir volver a subir el archivo si ya no existe. No elimina físicamente sectores del disco ni copias de seguridad.
- `/healthz` y recursos estáticos no contienen datos privados; resto de endpoints requiere autenticación. El estado web recuerda solo el ID de trabajo en sessionStorage, no credenciales ni texto.

## Persistencia, mantenimiento y copias

Volúmenes Docker: `models:/models` y `jobs:/data`; este último contiene SQLite, carpetas temporales de trabajos y documentos. Un reinicio normal o `docker compose down` conserva ambos. **No uses `down -v`** si quieres conservarlos.

```bash
cd ~/transcribe-ai
sudo docker compose ps
sudo docker compose logs --tail=100
sudo bash update.sh
```

Actualización: exige árbol Git limpio, detiene el servicio, copia `.env`, `/data` y commit a `backups/`, hace `git pull --ff-only`, construye y arranca. Durante la copia/actualización no se pueden procesar trabajos. Copias y modelos no se borran automáticamente. Las copias contienen información privada; guárdalas fuera de Git y bórralas según tu política. Las operaciones Git se ejecutan como el propietario del checkout, conservando el acceso SSH de ese usuario. No copies tu clave personal a root.

Para rollback: detén el servicio, conserva una copia de `/data`, revisa el commit indicado en `backups/commit-*`, cambia a ese commit con Git y reconstruye. Las futuras migraciones de base de datos pueden requerir restaurar la copia correspondiente. No se ejecuta rollback destructivo automáticamente.

## GPU NVIDIA opcional

La VM VirtualBox normal **no recibe automáticamente la RTX 3060 del host**. La V1 está pensada para CPU. Para NVIDIA usa un host Linux con GPU accesible, controlador y NVIDIA Container Toolkit instalados; comprueba primero `nvidia-smi` y el acceso desde contenedor. El overlay usa CUDA 12 + cuDNN 9, necesarios para CTranslate2 actual.

```bash
sudo docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
```

Usa los mismos `-f` para detener/recrear/actualizar la variante GPU. `update.sh` despliega CPU por defecto; para mantener GPU realiza el pull, copia y comandos equivalentes con ambos archivos. La imagen GPU no se ha construido/probado en este entorno.

## Desarrollo y pruebas

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
bash -n install.sh update.sh
# Requiere Docker:
cp .env.example .env  # solo si aún no existe; no sobrescribir credenciales
sudo docker compose config --quiet
sudo docker build -t transcribe-ai:test .
sudo .venv/bin/python docker_smoke.py
# Inferencia real, con muestras autorizadas de ambos idiomas:
.venv/bin/python real_smoke.py --es /ruta/castellano.wav --ca /ruta/catala.wav
```

`docker_smoke.py` crea un contenedor/volumen de prueba, comprueba HTTP, autenticación, Word y persistencia de un resultado preparado tras reinicio real; luego elimina solo esos recursos de prueba. No valida inferencia ni YouTube real. Consulta [TEST_REPORT.md](TEST_REPORT.md) para distinguir pruebas ejecutadas y pendientes.

## Referencias y licencia

Implementación propia inspirada en el proyecto MIT [Kabanosk/whisper-website](https://github.com/Kabanosk/whisper-website), estudiado en el commit `5e2387f5e6f9fd9addacf2a96bbf34f1e6d9893f`. Comparación detallada en [REFERENCE_REVIEW.md](REFERENCE_REVIEW.md). No se ha copiado código de ese proyecto; se incluye su licencia como atribución por prudencia. [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

Documentación primaria: [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper), [yt-dlp](https://github.com/yt-dlp/yt-dlp), [Docker en Ubuntu](https://docs.docker.com/engine/install/ubuntu/).
