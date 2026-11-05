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
- Flujo HTTP real con Uvicorn y proceso de trabajo real: subir WAV de silencio → cola SQLite → Faster-Whisper tiny CPU/VAD → resultado vacío → editar texto → descargar y reabrir DOCX: **aprobado**. Servidor y procesos cerrados correctamente después de la prueba.
- Se detectó que PyAV 19 elimina `metadata_errors`, requerido por Faster-Whisper 1.2.1. Se fijó **av==16.1.0** y se repitió satisfactoriamente la inferencia de silencio.
- `ruff check .`, `bash -n install.sh update.sh` y `node --check app.js`: aprobados.
- Se intentó descargar un vídeo de prueba mediante la función YouTube real; no fue posible desde este entorno. El flujo devolvió el error controlado al cliente. **Descarga y transcripción YouTube completa pendientes.**

## Ejecutado en GitHub Actions

[Checks #2](https://github.com/christian810/transcribe-ai/actions/runs/42028819537), commit `d0651c465f88df83ffd0ad5230dccc0aee3ff8cf`: **completado correctamente**.

- 25 pruebas automáticas, Ruff, sintaxis Bash y validación de configuración Docker Compose.
- Construcción real de imagen Docker CPU.
- Arranque real del contenedor: HTTP y autenticación.
- SQLite/volumen conserva un resultado preparado tras reiniciar realmente el contenedor; descarga DOCX desde ese resultado.
- El primer intento del test asumía que un puerto aleatorio publicado no cambiaría al reiniciar. Se corrigió el test para volver a consultar el puerto; la segunda ejecución completa pasó.

La prueba Docker usa un resultado preparado: no cuenta como inferencia de voz ni descarga YouTube dentro de Docker. La inferencia real de silencio descrita arriba se ejecutó fuera de Docker. La configuración endurecida completa de Compose fue validada sintácticamente; el test de ejecución usa `docker run`.

## Pendiente en el servidor

No hay acceso SSH autorizado al servidor ni muestras habladas autorizadas aquí. No se ha ejecutado:

1. Instalador y actualizador en una VM Ubuntu 26.04.1 LTS real; despliegue de producción con los límites completos de Compose.
2. Construcción/arranque de imagen GPU NVIDIA.
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

Ejecutar `docker_smoke.py` con un usuario autorizado para Docker o `sudo python3 docker_smoke.py`. Usa solo biblioteca estándar y comprueba HTTP, auth, Word y persistencia tras reinicio; no descarga modelos ni valida precisión. El script `docker_smoke.py` pasó en GitHub Actions. Los escenarios de voz hablada de `real_smoke.py` siguen pendientes.


## Actualización LAN sin cuentas — 05/11/2026

- Petición actual: acceso directo por IP privada desde equipos del Consell, sin usuarios ni túneles SSH.
- Valores iniciales: `BIND_IP=192.168.5.6`, `PORT=80`, `AUTH_REQUIRED=false`; instalador acepta otra IP privada ya asignada al servidor.
- Suite local actual: **27 pruebas aprobadas**. Se añaden acceso a página/API, subida, consulta y Word sin credenciales; rechazo de escrituras desde otro origen y de cliente con IP pública, incluso con `X-Forwarded-For` privado falsificado.
- Las pruebas anteriores de autenticación siguen comprobando el modo opcional con `AUTH_REQUIRED=true`.
- `bash -n install.sh update.sh` y `ruff check .`: aprobados.
- El informe de GitHub Actions anterior corresponde al commit anterior. La configuración LAN y la nueva prueba Docker deben validarse de nuevo en CI y en el servidor real; no se ha conectado a 192.168.5.6 desde este entorno.
