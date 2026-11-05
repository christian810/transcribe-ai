# Informe de pruebas — 05/11/2026

## Ejecutado en el entorno de desarrollo

- `python -m pytest -q`: **25 pruebas aprobadas**. FastAPI/TestClient con el supervisor desactivado para pruebas deterministas.
- Subida HTTP, nombre de ruta malicioso, archivo vacío, extensión denegada, fuente doble/ausente, idioma no permitido, límite de bytes, límite de cola y endpoints de trabajos.
- Autenticación incorrecta/correcta, límite de intentos fallidos, rechazo de origen cruzado.
- DOCX real (ZIP/OOXML) reabierto con python-docx: versión editada, acentos catalanes, metadatos y documento persistido. No se ha completado revisión visual en Microsoft Word/LibreOffice en este entorno.
- FFmpeg/FFprobe reales: WAV y conversión/extracción de MP3, M4A, FLAC, OGG, MP4, MKV, MOV, WEBM; vídeo MP4 con pista de imagen y audio. Salida comprobada mono/16 kHz. Archivo corrupto y duración excesiva rechazados.
- URLs YouTube válidas canónicas y rechazo de URLs externas, puertos, credenciales incrustadas, rutas de redirección y destinos privados. Proxy CONNECT rechaza loopback. Resoluciones privadas simuladas cubren IPv4/IPv6, red local y metadatos cloud.
- Worker probado con motor simulado: idioma catalán, VAD activo, contexto previo desactivado, texto, estado y eliminación del original. No cuenta como prueba de precisión de Whisper.
- Persistencia SQLite tras nueva inicialización/conexiones independientes y limpieza por caducidad. No equivale a reinicio de contenedor.
- Inferencia real **tiny / CPU / int8**: modelo descargado; dos segundos de silencio con VAD producen cadena vacía. No extrapolar esta comprobación a todos los tipos de ruido ni al modelo small de producción.
- Se detectó que PyAV 19 elimina `metadata_errors`, requerido por Faster-Whisper 1.2.1. Se fijó **av==16.1.0** y se repitió satisfactoriamente la inferencia de silencio.
- `ruff check .`, `bash -n install.sh update.sh` y `node --check app.js`: aprobados.
- Se intentó descargar un vídeo de prueba mediante la función YouTube real; no fue posible desde este entorno. El flujo devolvió el error controlado al cliente. **Descarga y transcripción YouTube completa pendientes.**

## Pendiente en el servidor

No hay Docker/daemon, GPU NVIDIA, acceso SSH al servidor ni muestras habladas autorizadas en este entorno. No se ha ejecutado:

1. Construcción/arranque Docker CPU o GPU; configuración Compose con Docker; reinicio real de contenedor y persistencia de volúmenes.
2. Instalador y actualizador en Ubuntu 26.04.1 LTS.
3. Inferencia de voz castellana y catalana, mezcla bilingüe o dialecto de Formentera. Modelo small real aún sin verificar aquí.
4. YouTube completo con un vídeo permitido y la red del servidor.
5. Documento abierto visualmente en Microsoft Word, acceso móvil mediante HTTPS, carga sostenida y watchdog de seis horas.

## Comandos de aceptación

Tras instalar en Ubuntu:

```bash
sudo docker compose ps
sudo docker compose logs --tail=100
# Después, prueba desde el navegador mediante túnel PuTTY:
# WAV castellano, M4A catalán, MP4, silencio, YouTube permitido,
# editar texto → Word y comprobar el archivo en Microsoft Word.
sudo docker compose restart
# Recargar la página y comprobar que sigue disponible el trabajo terminado.
```

Prueba de contenedor automatizada opcional:

```bash
sudo docker build -t transcribe-ai:test .
python3 docker_smoke.py
```

Ejecutar `docker_smoke.py` con un usuario autorizado para Docker o `sudo python3 docker_smoke.py`. Usa solo biblioteca estándar y comprueba HTTP, auth, Word y persistencia tras reinicio; no descarga modelos ni valida precisión. Los scripts `real_smoke.py` y `docker_smoke.py` se entregan, pero sus escenarios completos no se han ejecutado aquí.
