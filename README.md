# Transcribe AI — web local del Consell

Abre **http://192.168.1.6** desde un equipo de la red del Consell, sube audio/vídeo o pega YouTube, pulsa **Transcribir**, revisa el texto y descarga **Word (.docx)**. Sin usuarios, contraseñas, cuentas ni túneles SSH para quienes usan la web.

## Instalar una vez en Ubuntu

La IP se asigna manualmente en la configuración de red de Ubuntu. El instalador no cambia la red: comprueba que la IP indicada ya está asignada y configura la aplicación para escuchar en esa IP, puerto 80.

```bash
sudo apt-get update
sudo apt-get install -y git
git clone https://github.com/christian810/transcribe-ai.git
cd transcribe-ai
sudo bash install.sh 192.168.1.6
```

Si el repositorio se configura como privado, el administrador deberá autenticar Git una vez para descargarlo. Esto no crea usuarios ni pide cuentas a quienes utilizan la web.

Después, cualquier persona con acceso de red al servidor abre **http://192.168.1.6** en su navegador. PuTTY solo sirve para instalar o mantener el servidor; no hace falta dejarlo conectado. Ubuntu funciona sin escritorio.

Para cambiar a otra IP privada asignada manualmente:

```bash
sudo bash install.sh 192.168.1.10
```

El instalador conserva los datos y modelos; ajusta IP, puerto 80 y acceso sin autenticación. Si el puerto 80 ya lo usa otro servicio, cambia `PORT` en `.env` y recrea con `sudo docker compose up -d`. No publica el servicio en el router ni instala certificados. No conectes este modo sin cuentas a Internet.

## Uso

1. Selecciona o arrastra un MP3, WAV, M4A, FLAC, OGG, MP4, MKV, MOV o WEBM, o pega un enlace HTTPS de un vídeo de YouTube.
2. Elige automático, castellano o catalán y pulsa **Transcribir**.
3. Espera al procesamiento en el servidor. El progreso es estimado.
4. Edita el resultado y pulsa **Descargar Word (.docx)**. El Word recoge el texto editado, título, archivo/título del vídeo, fecha e idioma, sin marcas de tiempo por frase.

La copia al portapapeles puede requerir seleccionar texto y Ctrl+C en navegadores que la restringen sobre HTTP. Las ediciones del texto no se autoguardan al recargar; el último Word descargado se conserva durante la retención del trabajo.

## Actualizar

```bash
cd ~/transcribe-ai
sudo bash update.sh
```

`update.sh` conserva `.env`, modelos y trabajos, crea una copia privada de `/data` antes de actualizar y usa `git pull --ff-only`. Si vienes de la versión anterior con túnel SSH, después de actualizar ejecuta **una vez** `sudo bash install.sh 192.168.5.6` para aplicar la configuración LAN. Las siguientes actualizaciones conservan esa configuración.

## Configuración del servidor

| Variable en .env | Valor inicial | Función |
|---|---|---|
| BIND_IP | 192.168.1.6 | IP privada del servidor |
| PORT | 80 | URL directa sin escribir puerto |
| AUTH_REQUIRED | false | Sin inicio de sesión |
| ALLOWED_HOSTS | localhost,127.0.0.1,192.168.1.6 | Hosts aceptados por la aplicación |
| LAN_NETWORKS | Redes privadas y loopback | Clientes permitidos por IP real de conexión |
| WHISPER_MODEL | small | Modelo abierto configurable |
| WHISPER_DEVICE / WHISPER_COMPUTE_TYPE | cpu / int8 | Ejecución CPU inicial |
| MAX_UPLOAD_MB | 500 | Tamaño máximo por archivo/descarga |
| MAX_AUDIO_SECONDS | 14400 | Hasta cuatro horas por audio |
| MAX_QUEUED_JOBS | 8 | Trabajos pendientes/procesándose |
| RETENTION_HOURS | 24 | Caducidad de resultados y Word |
| MEMORY_LIMIT / CPU_LIMIT | 6g / 4 | Recursos máximos del contenedor |

Recomendación inicial para la VM: 4 vCPU, 8 GB de RAM y disco ampliable de 25–30 GB. El primer audio descarga el modelo de Hugging Face; la inferencia posterior es local. Con el modelo precargado, `MODEL_OFFLINE=true` impide nuevas descargas de modelos. YouTube necesita Internet y puede denegar descargas; solo procesa contenido permitido, sin saltarse DRM, login ni restricciones.

El catalán y el castellano están soportados. No hay entrenamiento específico del dialecto de Formentera ni garantía de precisión en audios bilingües. VAD y controles de silencio reducen texto inventado, pero el resultado se debe revisar.

## Funcionamiento y límites

- FastAPI sirve una página con HTML/CSS/JS locales; Faster-Whisper transcribe; FFmpeg extrae audio; python-docx genera documentos Word reales.
- Un supervisor procesa la cola SQLite en segundo plano, de uno en uno. Ejecutar una sola réplica y un solo worker Uvicorn.
- Dos volúmenes persistentes: `models:/models` y `jobs:/data`. Este último contiene SQLite, archivos temporales y documentos. Un reinicio normal o `docker compose down` conserva ambos. `down -v` los elimina.
- Sin cuentas: el acceso depende de estar en una red privada permitida y poder alcanzar el servidor. No hay separación por usuario ni historial público/listado de trabajos; cada navegador conserva su ID de trabajo. No compartas ese enlace/ID si contiene información privada.
- La aplicación rechaza conexiones de IP pública y no confía en `X-Forwarded-For`. Esto complementa las reglas de red; un proxy o NAT puede cambiar la IP que ve el contenedor. Mantener el servicio dentro de la red del Consell, sin publicar puertos en el router. Docker puede evitar reglas UFW de puertos publicados.
- Se mantienen límites de subida/cuerpo/cola/duración, comprobaciones de formato real, origen de escrituras, CSP, archivos privados con UUID y comandos sin shell. YouTube se limita a IDs canónicos y un proxy que valida dominios e IP pública para evitar SSRF.
- Originales y WAV extraído se borran al finalizar, también tras errores; resultados/Word caducan según retención; subidas abandonadas se limpian tras una hora. Copias de seguridad y modelos no se borran automáticamente.
- Contenedor sin root, raíz de solo lectura, capabilities eliminadas, límites de memoria/CPU/procesos. No sustituye a un antivirus; mantener dependencias actualizadas.
- Autenticación Basic opcional para otro despliegue: `AUTH_REQUIRED=true`, `APP_USER`, `APP_PASSWORD` de al menos 16 caracteres y HTTPS. Desactivada por defecto. `PUBLIC_ORIGIN` permite configurar el origen exacto de un futuro proxy HTTPS que conserve Host.

## GPU opcional

La configuración inicial funciona en CPU dentro de VirtualBox. La RTX del host no pasa automáticamente a la VM. Para un host Linux con GPU NVIDIA accesible, controlador y Container Toolkit, se entrega el overlay CUDA/cuDNN:

```bash
sudo docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d --build
```

Usa ambos archivos en todas las operaciones de esa variante; el instalador/actualizador habitual despliega CPU. La variante GPU no se ha probado aquí.

## Pruebas

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
bash -n install.sh update.sh
# Con Docker:
sudo docker build -t transcribe-ai:test .
sudo python3 docker_smoke.py
# Con muestras autorizadas de voz:
.venv/bin/python real_smoke.py --es /ruta/castellano.wav --ca /ruta/catala.wav
```

[TEST_REPORT.md](TEST_REPORT.md) diferencia las comprobaciones ejecutadas de las pendientes en tu Ubuntu. Los tests Docker usan un resultado preparado para comprobar Word y persistencia; no validan precisión de voz ni YouTube real.

## Referencias

Implementación propia inspirada en el repositorio MIT [Kabanosk/whisper-website](https://github.com/Kabanosk/whisper-website), revisado en `5e2387f5e6f9fd9addacf2a96bbf34f1e6d9893f`, sin copiar su código. [Revisión](REFERENCE_REVIEW.md) · [Atribución MIT](THIRD_PARTY_NOTICES.md).

[Faster-Whisper](https://github.com/SYSTRAN/faster-whisper) · [yt-dlp](https://github.com/yt-dlp/yt-dlp) · [Docker en Ubuntu](https://docs.docker.com/engine/install/ubuntu/).
