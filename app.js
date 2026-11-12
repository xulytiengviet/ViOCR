const el = id => document.getElementById(id);
const cdn = 'https://cdn.jsdelivr.net/npm/';
const tess = cdn + 'tesseract.js@6.0.1/dist/';
const pdfBase = cdn + 'pdfjs-dist@4.10.38/';
const scripts = new Map();
function script(url) {
  if (!scripts.has(url)) scripts.set(url, new Promise((ok, fail) => {
    const tag = document.createElement('script');
    tag.src = url;
    tag.onload = ok;
    tag.onerror = () => { scripts.delete(url); tag.remove(); fail(Error('Không tải được thư viện. Kiểm tra mạng rồi mở lại tệp.')); };
    document.head.append(tag);
  }));
  return scripts.get(url);
}
let rows = [], busy = false, sourceName = '';
const exportIds = ['word', 'txt', 'jsonl'];
const picker = typeof window.showSaveFilePicker === 'function';
el('savehelp').textContent = picker ? 'Chọn tên và thư mục khi lưu.' : 'Để chọn thư mục, bật tùy chọn hỏi nơi lưu mỗi tệp trong cài đặt tải xuống của trình duyệt.';
function lock(value) {
  busy = value;
  for (const id of ['open', 'mode', 'sample']) el(id).disabled = value;
  for (const id of exportIds) el(id).disabled = value || !rows.length;
}
async function* images(file) {
  if (/\.pdf$/i.test(file.name) || file.type === 'application/pdf') {
    const pdfjs = await import(pdfBase + 'build/pdf.min.mjs');
    pdfjs.GlobalWorkerOptions.workerSrc = pdfBase + 'build/pdf.worker.min.mjs';
    const doc = await pdfjs.getDocument({data: await file.arrayBuffer(), isEvalSupported:false,
      standardFontDataUrl:pdfBase+'standard_fonts/',cMapUrl:pdfBase+'cmaps/',cMapPacked:true}).promise;
    try {
      for (let n=1;n<=doc.numPages;n++) {
        const page = await doc.getPage(n);
        const viewport = page.getViewport({scale:150/72});
        const canvas = document.createElement('canvas');
        canvas.width = Math.ceil(viewport.width); canvas.height = Math.ceil(viewport.height);
        try {
          await page.render({canvasContext:canvas.getContext('2d'),viewport}).promise;
          yield {image:canvas,total:doc.numPages};
        } finally { canvas.width = canvas.height = 0; page.cleanup(); }
      }
    } finally { await doc.destroy(); }
  } else if (/\.tiff?$/i.test(file.name) || file.type === 'image/tiff') {
    await script(cdn+'pako@1.0.11/dist/pako.min.js');
    await script(cdn+'utif@3.1.0/UTIF.js');
    const buffer = await file.arrayBuffer();
    const frames = UTIF.decode(buffer).filter(f=>f.t256 && f.t257);
    if (!frames.length) throw Error('TIFF không có trang ảnh.');
    for (const frame of frames) {
      UTIF.decodeImage(buffer,frame);
      const canvas=document.createElement('canvas');
      canvas.width=frame.width; canvas.height=frame.height;
      const data=new ImageData(new Uint8ClampedArray(UTIF.toRGBA8(frame)),canvas.width,canvas.height);
      canvas.getContext('2d').putImageData(data,0,0);
      try { yield {image:canvas,total:frames.length}; }
      finally { canvas.width=canvas.height=0; delete frame.data; }
    }
  } else {
    const url = URL.createObjectURL(file);
    try {
      const image = new Image(); image.src = url;
      await image.decode(); yield {image,total:1};
    } finally { URL.revokeObjectURL(url); }
  }
}
function linesFromTSV(tsv, mode) {
  const groups = new Map();
  for (const row of tsv.split(/\r?\n/)) {
    const f=row.split('\t');
    if (f[0]!=='5' || !f[11]?.trim()) continue;
    const key=f.slice(2,5).join('/');
    if (!groups.has(key)) groups.set(key,[]);
    groups.get(key).push({text:f.slice(11).join('\t'),confidence:Number(f[10]),box:f.slice(6,10).map(Number)});
  }
  return [...groups.values()].map(words => ({...ViOCR.processLine(words.map(w=>w.text).join(' '),mode),words}));
}
async function readFile(file) {
  if (!file || busy) return;
  rows=[]; sourceName=file.name; lock(true);
  el('name').textContent=file.name; el('result').value=''; el('progress').hidden=false;
  el('progress').removeAttribute('value'); el('status').textContent='Đang chuẩn bị bộ nhận dạng…';
  const mode=el('mode').value;
  let worker, current=0, total=0, failure;
  try {
    await script(tess+'tesseract.min.js');
    // Tesseract.js reports some initialization failures through errorHandler only.
    const failed = new Promise((_,reject)=>{failure=reject});
    await Promise.race([failed,(async()=>{
      worker=await Tesseract.createWorker('vie',1,{workerPath:tess+'worker.min.js',
        corePath:cdn+'tesseract.js-core@6.0.0',langPath:new URL('models',location.href).href,
        gzip:false,cachePath:'viocr-vie-fast-v1',errorHandler:e=>failure(Error(String(e))),
        logger:m=>{if(m.status==='recognizing text'){el('progress').value=m.progress;}}});
      await worker.setParameters({tessedit_pageseg_mode:'3',tessedit_char_whitelist:mode==='base27'?'0123456789 ':''});
      for await (const frame of images(file)) {
        current++; total=frame.total;
        el('status').textContent='Đang đọc trang '+current+' / '+total+'…';
        const {data}=await worker.recognize(frame.image,{}, {text:true,tsv:true});
        const lines=linesFromTSV(data.tsv,mode);
        rows.push({schemaVersion:1,file:file.name,page:current,width:frame.image.naturalWidth||frame.image.width,
          height:frame.image.naturalHeight||frame.image.height,mode,lines,text:lines.map(l=>l.unicode).join('\n')});
        el('result').value=rows.map(r=>r.text).join('\n\n');
      }
    })()]);
    el('status').textContent=rows.some(r=>r.text)?'Hoàn tất · '+rows.length+' trang':'Hoàn tất · Không tìm thấy chữ trên tài liệu.';
  } catch(e) {
    rows=[]; el('result').value='';
    el('status').textContent='Chưa đọc được tài liệu. '+(e.message || e);
  } finally {
    try {if(worker) await worker.terminate();} finally {el('progress').hidden=true; lock(false);}
  }
}
const formats={word:['docx','application/vnd.openxmlformats-officedocument.wordprocessingml.document'],txt:['txt','text/plain'],jsonl:['jsonl','application/x-ndjson']};
async function save(id) {
  if (busy || !rows.length) return;
  const [ext,mime]=formats[id], name=sourceName.replace(/\.[^.]+$/,'')+'.'+ext;
  lock(true);
  try {
    const handle=picker?await showSaveFilePicker({suggestedName:name,types:[{description:ext.toUpperCase(),accept:{[mime]:['.'+ext]}}]}):null;
    let blob;
    if(id==='word'){
      await script(cdn+'docx@8.5.0/build/index.umd.js');
      const sections=rows.map(row=>({children:row.text.split('\n').map(line=>new docx.Paragraph({text:line}))}));
      blob=await docx.Packer.toBlob(new docx.Document({creator:'Long Ngo · ViOCR',sections}));
    } else {
      const data=id==='txt'?'\uFEFF'+rows.map(r=>r.text.replaceAll('\n','\r\n')).join('\r\n\f\r\n'):rows.map(r=>JSON.stringify(r)).join('\n')+'\n';
      blob=new Blob([data],{type:mime+';charset=utf-8'});
    }
    if(handle){const out=await handle.createWritable(); await out.write(blob); await out.close();}
    else {const url=URL.createObjectURL(blob),a=document.createElement('a'); a.href=url; a.download=name; a.click(); setTimeout(()=>URL.revokeObjectURL(url),60000);}
    el('status').textContent=handle?'Đã lưu '+handle.name:'Đã gửi '+name+' tới trình tải xuống.';
  } catch(e){el('status').textContent=e.name==='AbortError'?'Đã hủy lưu.':'Lưu thất bại. '+e.message;}
  finally {lock(false);}
}
el('open').onclick=()=>el('file').click();
el('file').onchange=()=>{const file=el('file').files[0];el('file').value='';readFile(file);};
const drop=el('drop');
for(const event of ['dragover','dragleave','drop']) drop.addEventListener(event,e=>{
  e.preventDefault();drop.classList.toggle('over',event==='dragover'&&!busy);
  if(event==='drop') readFile(e.dataTransfer.files[0]);
});
el('sample').onclick=async()=>{
  if(busy)return;
  lock(true);
  let file;
  try {const r=await fetch('examples/scan.pdf');if(!r.ok) throw Error(r.status);file=new File([await r.blob()],'scan.pdf',{type:'application/pdf'});}
  catch(e){el('status').textContent='Không tải được PDF mẫu. '+e.message;}
  finally{lock(false);}
  if(file)readFile(file);
};
for (const id of exportIds) el(id).onclick=()=>save(id);
