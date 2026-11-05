'use strict';
const $ = id => document.getElementById(id);
let jobId = null;
let polling = false;
const names = {es:'Castellano',ca:'Catalán'};
function error(message) { $('error').textContent = message; $('error').hidden = false; }
async function api(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    let body; try { body = await response.json(); } catch { /* proxy response */ }
    throw new Error(typeof body?.detail === 'string' ? body.detail : `No se pudo completar la solicitud (${response.status}).`);
  }
  return response;
}
function selected() { $('filename').textContent = $('file').files[0]?.name || 'Arrastra tu audio o vídeo aquí'; }
$('file').addEventListener('change', () => { if ($('file').files.length) $('url').value = ''; selected(); });
$('url').addEventListener('input', () => { if ($('url').value) { $('file').value=''; selected(); } });
$('clear').onclick = () => { $('file').value=''; $('url').value=''; selected(); };
for (const event of ['dragenter','dragover']) $('drop').addEventListener(event, e => {e.preventDefault(); $('drop').classList.add('over');});
$('drop').addEventListener('dragleave', () => $('drop').classList.remove('over'));
$('drop').addEventListener('drop', e => { e.preventDefault(); $('drop').classList.remove('over'); if(e.dataTransfer.files.length !== 1) return error('Selecciona un único archivo.'); $('file').files=e.dataTransfer.files; $('url').value=''; selected(); });
async function poll(id) {
  if (polling) return;
  polling=true;
  $('submit').disabled=true;
  $('statusbox').hidden=false;
  try {
    while (true) {
      const row = await (await api('/api/jobs/'+id)).json();
      $('progress').value=row.progress;
      $('status').textContent = row.status==='queued' ? 'En cola. Tu transcripción comenzará en cuanto haya un hueco.' : row.progress<15 ? 'Preparando el archivo o descargando YouTube…' : row.progress<25 ? 'Extrayendo el audio…' : 'Transcribiendo… El primer uso puede tardar mientras se descarga el modelo.';
      if(row.status==='done') {
        $('status').textContent=row.text ? 'Transcripción terminada.' : 'No se ha detectado voz en el audio.';
        $('text').value=row.text;
        $('detected').textContent=names[row.detected] || row.detected;
        $('result').hidden=false;
        $('word').disabled=false;
        $('copy').disabled=false;
        break;
      }
      if(row.status==='error') throw new Error(row.error);
      await new Promise(resolve => setTimeout(resolve, 2000));
    }
  } catch (e) { error(e.message + ' Si hubo un corte de conexión, recarga para consultar el trabajo.'); }
  finally { polling=false; $('submit').disabled=false; }
}
$('form').addEventListener('submit', async e => {
  e.preventDefault(); $('error').hidden=true;
  if (!$('file').files.length && !$('url').value.trim()) return error('Selecciona un archivo o pega un enlace de YouTube.');
  $('submit').disabled=true; $('result').hidden=true;
  $('statusbox').hidden=false; $('status').textContent='Subiendo el archivo…'; $('progress').value=0;
  try {
    const data = new FormData($('form'));
    if (!$('file').files.length) data.delete('file');
    const row=await (await api('/api/jobs',{method:'POST',body:data})).json();
    jobId=row.id; sessionStorage.setItem('transcribe-job',jobId);
    await poll(jobId);
  } catch(e) {error(e.message); $('submit').disabled=false;}
});
$('word').onclick=async () => {
  $('word').disabled=true; $('error').hidden=true;
  try {
    const response=await api('/api/jobs/'+jobId+'/word',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:$('text').value})});
    const url=URL.createObjectURL(await response.blob());
    const a=document.createElement('a'); a.href=url; a.download='transcripcion.docx'; a.click();
    setTimeout(()=>URL.revokeObjectURL(url),1000);
  } catch(e) {error(e.message);} finally {$('word').disabled=false;}
};
$('copy').onclick=async () => {
  try { await navigator.clipboard.writeText($('text').value); $('copy').textContent='Copiado'; setTimeout(()=>$('copy').textContent='Copiar texto',1500); }
  catch { $('text').focus(); $('text').select(); error('Pulsa Ctrl+C (o mantén pulsado y elige Copiar).'); }
};
api('/api/config').then(r=>r.json()).then(c=>$('limits').textContent+=` · Hasta ${c.max_upload_mb} MB / ${c.max_minutes} min`).catch(e=>error(e.message));
jobId=sessionStorage.getItem('transcribe-job'); if(jobId) poll(jobId);
