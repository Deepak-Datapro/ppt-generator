const $ = (id) => document.getElementById(id);
let latestStory = null;
let latestSvg = '';
const esc = (s='') => String(s).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&apos;'}[c]));
const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, Number.isFinite(Number(v)) ? Number(v) : (lo+hi)/2));

async function checkHealth(){
  try { const r=await fetch('/api/health'); const d=await r.json(); const el=$('connection');
    if(d.ok){el.textContent=`Ollama connected · ${d.configured_model}`;el.className='status ok';}
    else {el.textContent='Ollama not reachable';el.className='status bad';}
  } catch { $('connection').textContent='Ollama status unavailable';$('connection').className='status bad'; }
}
function wrapWords(text, maxChars){const words=String(text||'').split(/\s+/);const lines=[];let line='';for(const word of words){if((line+' '+word).trim().length>maxChars&&line){lines.push(line);line=word;}else line=(line+' '+word).trim();}if(line)lines.push(line);return lines;}
function textLines(text,x,y,maxChars,lineHeight,cls,anchor='start'){return wrapWords(text,maxChars).slice(0,3).map((line,i)=>`<text class="${cls}" x="${x}" y="${y+i*lineHeight}" text-anchor="${anchor}">${esc(line)}</text>`).join('');}
// A character's visual identity is derived from their name, so it stays
// consistent from panel to panel and differs from the other named characters.
function characterProfile(char){
  const key=String(char.character_id||char.name||'Character').trim().toLowerCase();
  let hash=2166136261;
  for(let i=0;i<key.length;i++){hash^=key.charCodeAt(i);hash=Math.imul(hash,16777619);}
  const pick=(arr,n)=>arr[(n>>>0)%arr.length];
  const n=hash>>>0;
  return {
    skin:pick(['#f3c9a5','#d99b72','#a96f50','#f0d2b5','#8d5a43','#c98762'],n),
    hair:pick(['#30251f','#5a3827','#17191e','#8a542e','#4b3b32','#b77a42'],n>>>3),
    shirt:pick(['#5879c8','#d96d62','#3e9b87','#e1a83f','#9067b5','#e07d42','#477caa'],n>>>6),
    pants:pick(['#34445f','#46536a','#526b72','#65536f','#39434d'],n>>>9),
    hairStyle:(n>>>12)%4,
    accessory:(n>>>15)%4
  };
}
function personSvg(char, x, y, scale=1){
  const pose=String(char.pose||'standing').toLowerCase();
  const p=characterProfile(char);
  let leftArm='M -8 34 Q -20 40 -23 54',rightArm='M 8 34 Q 20 40 23 54';
  let leftLeg='M -7 65 L -13 84',rightLeg='M 7 65 L 13 84';
  if(pose==='thinking'){rightArm='M 8 34 Q 20 31 17 18 L 12 12';}
  if(pose==='talking'){leftArm='M -8 34 Q -22 25 -28 32';rightArm='M 8 34 Q 23 25 29 32';}
  if(pose==='walking'){leftArm='M -8 34 Q -22 28 -25 20';rightArm='M 8 34 Q 22 43 26 52';leftLeg='M -7 65 L -23 79';rightLeg='M 7 65 L 22 82';}
  if(pose==='surprised'){leftArm='M -8 34 Q -23 22 -27 13';rightArm='M 8 34 Q 23 22 27 13';}
  const hairTop = [
    `<path d="M -17 -5 Q -19 -25 0 -25 Q 19 -25 18 -5 L 14 -11 Q 2 -18 -12 -9 Z" fill="${p.hair}" stroke="#292d38" stroke-width="1.5"/>`,
    `<path d="M -18 -3 Q -23 -24 -3 -26 Q 17 -28 19 -8 L 14 -13 Q 5 -5 -12 -12 Z" fill="${p.hair}" stroke="#292d38" stroke-width="1.5"/><path d="M -17 -2 Q -24 9 -17 17" fill="none" stroke="${p.hair}" stroke-width="5"/>`,
    `<path d="M -19 -4 Q -20 -25 0 -25 Q 20 -25 19 -4 L 17 12 Q 10 19 13 1 Q 2 -8 -12 1 Q -15 13 -18 9 Z" fill="${p.hair}" stroke="#292d38" stroke-width="1.5"/>`,
    `<path d="M -18 -5 Q -18 -26 0 -25 Q 18 -24 18 -5 L 14 -12 Q 4 -17 -3 -10 Q -10 -5 -18 -5 Z" fill="${p.hair}" stroke="#292d38" stroke-width="1.5"/><path d="M -18 1 Q -24 12 -17 20 M 18 1 Q 24 12 17 20" fill="none" stroke="${p.hair}" stroke-width="4"/>`
  ][p.hairStyle];
  const accessory = [
    `<path d="M -14 -4 Q 0 -9 14 -4" stroke="${p.hair}" stroke-width="2" fill="none"/>`,
    `<circle cx="0" cy="-1" r="2.2" fill="#f0c34e"/>`,
    `<path d="M -17 -7 L -12 -13 L -7 -7 L -2 -13 L 3 -7 L 8 -13 L 14 -6" fill="none" stroke="${p.hair}" stroke-width="2.5"/>`,
    `<rect x="-17" y="-5" width="34" height="5" rx="2.5" fill="${p.shirt}" stroke="#293244" stroke-width="1"/>`
  ][p.accessory];
  const face = pose==='surprised'
    ? `<circle cx="-6" cy="-1" r="2" fill="#252936"/><circle cx="6" cy="-1" r="2" fill="#252936"/><ellipse cx="0" cy="8" rx="3.2" ry="4" fill="#9b4d45"/>`
    : `<ellipse cx="-6" cy="0" rx="1.8" ry="2.3" fill="#252936"/><ellipse cx="6" cy="0" rx="1.8" ry="2.3" fill="#252936"/><path d="M -5 8 Q 0 13 5 8" fill="none" stroke="#8f4e45" stroke-width="1.6" stroke-linecap="round"/>`;
  const body = pose==='walking'
    ? `<path d="M -11 22 Q 0 17 11 22 L 13 59 Q 0 64 -13 59 Z" fill="${p.shirt}" stroke="#293244" stroke-width="1.8"/>`
    : `<path d="M -11 22 Q 0 17 11 22 L 13 60 Q 0 64 -13 60 Z" fill="${p.shirt}" stroke="#293244" stroke-width="1.8"/>`;
  return `<g transform="translate(${x} ${y}) scale(${scale})" class="person">
    <path d="${leftLeg}" fill="none" stroke="${p.pants}" stroke-width="6" stroke-linecap="round"/>
    <path d="${rightLeg}" fill="none" stroke="${p.pants}" stroke-width="6" stroke-linecap="round"/>
    <path d="M -16 85 Q -13 81 -5 84 L -4 88 L -19 88 Z M 5 84 Q 13 81 18 85 L 20 88 L 5 88 Z" fill="#303744"/>
    ${body}
    <path d="${leftArm}" fill="none" stroke="${p.skin}" stroke-width="7" stroke-linecap="round"/>
    <path d="${rightArm}" fill="none" stroke="${p.skin}" stroke-width="7" stroke-linecap="round"/>
    <path d="M -8 27 Q 0 32 8 27" fill="none" stroke="#ffffff" stroke-width="1.5" opacity=".7"/>
    <rect x="-4" y="16" width="8" height="9" rx="3" fill="${p.skin}"/>
    <circle cx="-18" cy="-1" r="4" fill="${p.skin}" stroke="#293244" stroke-width="1"/>
    <circle cx="18" cy="-1" r="4" fill="${p.skin}" stroke="#293244" stroke-width="1"/>
    <ellipse cx="0" cy="0" rx="17" ry="21" fill="${p.skin}" stroke="#293244" stroke-width="1.8"/>
    ${hairTop}
    ${accessory}
    ${face}
    <text x="0" y="104" text-anchor="middle" font-size="9" stroke="none" fill="#3c4659">${esc(char.name||'Character')}</text>
  </g>`;
}
function cloudBubble(x,y,w,h,text,thought=true){
  let shape='';
  if(thought){
    shape=`<path class="bubble" d="M ${x+w*.18} ${y+h*.77} C ${x+w*.04} ${y+h*.78},${x} ${y+h*.58},${x+w*.05} ${y+h*.4} C ${x-w*.02} ${y+h*.19},${x+w*.17} ${y+h*.02},${x+w*.34} ${y+h*.13} C ${x+w*.46} ${y-h*.04},${x+w*.67} ${y+h*.03},${x+w*.7} ${y+h*.13} C ${x+w*.92} ${y+h*.02},${x+w*1.04} ${y+h*.2},${x+w*.97} ${y+h*.39} C ${x+w*1.02} ${y+h*.6},${x+w*.87} ${y+h*.76},${x+w*.7} ${y+h*.74} Q ${x+w*.43} ${y+h*.88},${x+w*.18} ${y+h*.77} Z"/><circle class="bubble" cx="${x+w*.18}" cy="${y+h*.92}" r="3.5"/><circle class="bubble" cx="${x+w*.12}" cy="${y+h+5}" r="2"/>`;
  }else{
    shape=`<path class="bubble" d="M ${x+5} ${y+5} Q ${x} ${y+5} ${x} ${y+12} L ${x} ${y+h-12} Q ${x} ${y+h-5} ${x+7} ${y+h-5} L ${x+w*.32} ${y+h-5} L ${x+w*.25} ${y+h+7} L ${x+w*.43} ${y+h-5} L ${x+w-7} ${y+h-5} Q ${x+w} ${y+h-5} ${x+w} ${y+h-12} L ${x+w} ${y+12} Q ${x+w} ${y+5} ${x+w-7} ${y+5} Z"/>`;
  }
  const lines=wrapWords(text,thought?18:24).slice(0,3);const startY=y+h/2-(lines.length-1)*5;
  return `<g>${shape}${lines.map((line,i)=>`<text class="bubble-text" x="${x+w/2}" y="${startY+i*11}">${esc(line)}</text>`).join('')}</g>`;
}
function drawComic(story, count){
  const cols=count<=2?2:count<=4?2:count<=6?3:4; const rows=Math.ceil(count/cols);
  const pw=300,ph=230,gap=12,margin=14,top=52;const width=margin*2+cols*pw+(cols-1)*gap;const height=top+margin+rows*ph+(rows-1)*gap;
  let out=`<svg xmlns="http://www.w3.org/2000/svg" class="comic-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="${esc(story.title||'Generated comic')}">
  <title>${esc(story.title||'Generated comic')}</title>
  <style>
    .comic-svg { background:#ffffff; font-family:Inter,Arial,sans-serif; }
    .comic-svg text { font-family:Inter,Arial,sans-serif; }
    .comic-svg .panel-border { fill:#ffffff; stroke:#222938; stroke-width:2.5; }
    .comic-svg .caption { font-size:15px; font-weight:700; fill:#20242c; }
    .comic-svg .action { font-size:10px; fill:#626a78; }
    .comic-svg .bubble { fill:#ffffff; stroke:#273043; stroke-width:1.8; }
    .comic-svg .bubble-text { font-size:10px; fill:#20242c; text-anchor:middle; }
    .comic-svg .person { stroke:#263044; stroke-linecap:round; stroke-linejoin:round; }
    .comic-svg .person text { font-family:Inter,Arial,sans-serif; }
    .comic-svg .ground { stroke:#d8deea; stroke-width:1.2; }
  </style>
  <rect x="0" y="0" width="${width}" height="${height}" fill="#ffffff"/>
  <text x="${margin}" y="32" font-size="22" font-weight="800" fill="#20242c">${esc(story.title||'My Comic')}</text>`;
  (story.panels||[]).slice(0,count).forEach((panel,i)=>{
    const col=i%cols,row=Math.floor(i/cols),x=margin+col*(pw+gap),y=top+row*(ph+gap);
    out+=`<g transform="translate(${x} ${y})"><rect class="panel-border" x="0" y="0" width="${pw}" height="${ph}" rx="5"/><rect x="0" y="0" width="${pw}" height="28" fill="#f0f2fa"/><text class="caption" x="10" y="19">${i+1}. ${esc(panel.caption||'Scene')}</text><line class="ground" x1="12" y1="${ph-26}" x2="${pw-12}" y2="${ph-26}"/>`;
    const chars=(panel.characters||[]).slice(0,3);const positions=[.31,.70,.51];
    chars.forEach((c,j)=>{
      const cx=clamp(c.x,0.12,0.88)*pw,cy=clamp(c.y,0.40,0.72)*ph;
      out+=personSvg(c,cx,cy,.72);
      if(c.thought){const bx=clamp(cx-45,4,pw-108),by=Math.max(34,cy-77);out+=cloudBubble(bx,by,98,42,c.thought,true);}
      if(c.speech){const bx=clamp(cx-48,4,pw-116),by=Math.max(33,cy-105);out+=cloudBubble(bx,by,108,42,c.speech,false);}
    });
    if(!chars.length) out+=personSvg({name:'A',pose:'thinking'},pw*.5,ph*.58,.72);
    out+=textLines(panel.action||panel.setting||'',10,ph-9,46,11,'action');out+='</g>';
  });
  out+='</svg>';return out;
}
function downloadBlob(data,type,name){
  const blob=data instanceof Blob?data:new Blob([data],{type});
  const url=URL.createObjectURL(blob);const a=document.createElement('a');
  a.href=url;a.download=name;document.body.appendChild(a);a.click();a.remove();
  // Do not revoke immediately; some browsers need the URL after the click event.
  setTimeout(()=>URL.revokeObjectURL(url),1500);
}
function setDownloadsEnabled(enabled){['downloadSvg','downloadPng','downloadJpg','downloadWebp','downloadJson'].forEach(id=>$(id).disabled=!enabled);}
async function downloadRaster(format){
  if(!latestSvg)return;
  const svgBlob=new Blob([latestSvg],{type:'image/svg+xml;charset=utf-8'});
  const svgUrl=URL.createObjectURL(svgBlob);
  try{
    const img=new Image();
    await new Promise((resolve,reject)=>{img.onload=resolve;img.onerror=()=>reject(new Error('Could not render the comic for image export. Try SVG instead.'));img.src=svgUrl;});
    const svgRoot=new DOMParser().parseFromString(latestSvg,'image/svg+xml').documentElement;
    const vb=(svgRoot.getAttribute('viewBox')||'0 0 1200 800').trim().split(/[ ,]+/).map(Number);
    const width=Math.max(1,Math.round(vb[2]||1200)),height=Math.max(1,Math.round(vb[3]||800));
    const scale=Math.min(3,Math.max(1,2400/Math.max(width,height)));
    const canvas=document.createElement('canvas');canvas.width=Math.round(width*scale);canvas.height=Math.round(height*scale);
    const ctx=canvas.getContext('2d');
    // JPEG has no transparency; fill all formats white for predictable output.
    ctx.fillStyle='#ffffff';ctx.fillRect(0,0,canvas.width,canvas.height);ctx.drawImage(img,0,0,canvas.width,canvas.height);
    const mime={png:'image/png',jpg:'image/jpeg',webp:'image/webp'}[format];
    const blob=await new Promise(resolve=>canvas.toBlob(resolve,mime,0.94));
    if(!blob)throw new Error('Image conversion failed in this browser.');
    downloadBlob(blob,mime,`comic.${format}`);
    $('message').textContent=`Comic downloaded as ${format.toUpperCase()} image.`;
  }finally{URL.revokeObjectURL(svgUrl);}
}


function diagramShell(title, content, width=1000, height=650) {
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" width="${width}" height="${height}" role="img" aria-label="${esc(title)}">
    <title>${esc(title)}</title>
    <style>
      text{font-family:Inter,Arial,sans-serif;fill:#20242c}
      .d-title{font-size:25px;font-weight:800}
      .d-node{stroke:#42527d;stroke-width:2}
      .d-line{stroke:#4b5875;stroke-width:2.2;fill:none;marker-end:url(#arrow)}
      .d-label{font-size:13px}
    </style>
    <defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#4b5875"/></marker></defs>
    <rect width="100%" height="100%" fill="#fff"/>
    <text class="d-title" x="35" y="45">${esc(title)}</text>${content}</svg>`;
}

function renderFlowchart(d) {
  const nodes = d.nodes || [], edges = d.edges || [];
  const width = 1000, height = Math.max(600, nodes.length * 125 + 100);
  const positions = {};
  nodes.forEach((n, i) => positions[n.id] = {x: width/2, y: 100 + i*115});
  let body = '';
  edges.forEach(e => {
    const a = positions[e.from], b = positions[e.to];
    if (!a || !b) return;
    body += `<path class="d-line" d="M${a.x} ${a.y+32} L${b.x} ${b.y-32}"/>`;
    if (e.label) body += `<text class="d-label" x="${a.x+14}" y="${(a.y+b.y)/2}">${esc(e.label)}</text>`;
  });
  nodes.forEach(n => {
    const p = positions[n.id], type = n.type || 'process';
    if (type === 'decision') {
      body += `<polygon class="d-node" fill="#fff0d8" points="${p.x},${p.y-38} ${p.x+145},${p.y} ${p.x},${p.y+38} ${p.x-145},${p.y}"/>`;
    } else {
      const fill = type === 'start' ? '#dff4e8' : type === 'end' ? '#e7e9fb' : '#eaf0ff';
      body += `<rect class="d-node" fill="${fill}" x="${p.x-135}" y="${p.y-31}" width="270" height="62" rx="${type==='start'||type==='end'?28:10}"/>`;
    }
    body += `<text class="d-label" text-anchor="middle" x="${p.x}" y="${p.y+5}">${esc(n.label || n.id)}</text>`;
  });
  return diagramShell(d.title || 'Flowchart', body, width, height);
}

function renderPie(d) {
  const segments = (d.segments || []).filter(s => Number(s.value) > 0);
  const total = segments.reduce((sum, s) => sum + Number(s.value), 0) || 1;
  const colors = ['#5476c8','#e28b54','#4aa58d','#a47ac8','#d4b34d','#d76d83','#6d9dbb'];
  const cx = 390, cy = 315, radius = 175;
  let angle = -Math.PI/2, body = '';
  segments.forEach((s, i) => {
    const span = Number(s.value)/total*Math.PI*2, mid = angle + span/2;
    const ox = Math.cos(mid)*13, oy = Math.sin(mid)*13;
    const x1 = cx+ox+radius*Math.cos(angle), y1 = cy+oy+radius*Math.sin(angle);
    const x2 = cx+ox+radius*Math.cos(angle+span), y2 = cy+oy+radius*Math.sin(angle+span);
    body += `<path d="M${cx+ox} ${cy+oy} L${x1} ${y1} A${radius} ${radius} 0 ${span>Math.PI?1:0} 1 ${x2} ${y2} Z" fill="${colors[i%colors.length]}" stroke="#fff" stroke-width="3"/>`;
    body += `<rect x="690" y="${145+i*48}" width="18" height="18" rx="3" fill="${colors[i%colors.length]}"/>`;
    body += `<text x="720" y="${160+i*48}" font-size="14">${esc(s.label)}: ${Number(s.value)} (${(Number(s.value)/total*100).toFixed(1)}%)</text>`;
    angle += span;
  });
  return diagramShell(d.title || 'Exploded pie chart', body, 1000, Math.max(600, 220+segments.length*48));
}

function renderBar(d) {
  const items = d.items || d.bars || [];
  const max = Math.max(1, ...items.map(x => Number(x.value)||0));
  const left=110, bottom=500, chartH=365, chartW=790, slot=chartW/Math.max(items.length,1), barW=Math.min(76,slot*.58);
  let body = `<line x1="${left}" y1="${bottom-chartH}" x2="${left}" y2="${bottom}" stroke="#46516a" stroke-width="2"/><line x1="${left}" y1="${bottom}" x2="${left+chartW}" y2="${bottom}" stroke="#46516a" stroke-width="2"/>`;
  for(let i=0;i<=4;i++){
    const y=bottom-i*chartH/4;
    body += `<line x1="${left}" y1="${y}" x2="${left+chartW}" y2="${y}" stroke="#e7eaf1"/>`;
    body += `<text x="${left-15}" y="${y+4}" text-anchor="end" font-size="11">${(max*i/4).toFixed(0)}</text>`;
  }
  items.forEach((item,i)=>{
    const value=Math.max(0,Number(item.value)||0), h=value/max*chartH;
    const x=left+i*slot+(slot-barW)/2, y=bottom-h, color=['#5476c8','#e28b54','#4aa58d','#a47ac8'][i%4];
    body += `<rect x="${x}" y="${y}" width="${barW}" height="${h}" rx="5" fill="${color}"/>`;
    body += `<text x="${x+barW/2}" y="${y-9}" text-anchor="middle" font-size="12">${value}</text>`;
    body += `<text x="${x+barW/2}" y="${bottom+23}" text-anchor="middle" font-size="12">${esc(item.label)}</text>`;
  });
  body += `<text x="500" y="570" text-anchor="middle" font-size="14">${esc(d.xLabel||'Category')}</text>`;
  body += `<text x="35" y="80" font-size="14">${esc(d.yLabel||'Value')}</text>`;
  return diagramShell(d.title || 'Bar chart', body, 1000, 610);
}

function renderVenn(d) {
  const sets = (d.sets || []).slice(0,3);
  const three = sets.length === 3;
  const circles = three
    ? [{x:390,y:285,c:'#5b83c8'},{x:540,y:285,c:'#e28b55'},{x:465,y:405,c:'#55a58b'}]
    : [{x:405,y:325,c:'#5b83c8'},{x:565,y:325,c:'#e28b55'}];
  let body = '';
  circles.forEach(c => body += `<circle cx="${c.x}" cy="${c.y}" r="155" fill="${c.c}" fill-opacity=".27" stroke="${c.c}" stroke-width="3"/>`);
  sets.forEach((s,i) => body += `<text x="${circles[i].x-95}" y="${circles[i].y-115}" font-size="17" font-weight="700">${esc(s.label)}</text>`);
  const membership = {};
  sets.forEach((s,i) => (s.items||[]).forEach(value => membership[value]=(membership[value]||0)|(1<<i)));
  Object.entries(membership).forEach(([value,mask]) => {
    const xy = mask===1?[320,315] : mask===2?[650,315] : mask===4?[465,505] : mask===3?[485,300] : mask===5?[410,410] : mask===6?[555,410] : [485,380];
    body += `<text x="${xy[0]}" y="${xy[1]}" text-anchor="middle" font-size="12">${esc(value)}</text>`;
  });
  return diagramShell(d.title || 'Venn diagram', body, 1000, 650);
}


function renderShapes(data) {
  const allowed = new Set(['line','arrow','point','rect','rounded_rect','circle','ellipse','triangle','polygon','spline','path','text']);
  const color = (v, fallback) => /^#[0-9a-f]{3,8}$/i.test(String(v||'')) ? v : fallback;
  const n = (v, fallback=0, lo=-2000, hi=3000) => Math.max(lo,Math.min(hi,Number.isFinite(Number(v))?Number(v):fallback));
  const points = a => Array.isArray(a) ? a.slice(0,20).map(p=>[n(p?.[0]),n(p?.[1])]) : [];
  let out = '';
  (data.shapes||[]).slice(0,40).forEach(s => {
    if (!s || !allowed.has(s.type)) return;
    const fill = s.fill==='none'?'none':color(s.fill,'#dce8f5');
    const stroke = s.stroke==='none'?'none':color(s.stroke,'#52627a');
    const sw=n(s.strokeWidth,2,0,20);
    const label=s.label?`<text x="${n(s.labelX,s.cx??s.x??100)}" y="${n(s.labelY,(s.cy??s.y??100)+24)}" text-anchor="middle" font-size="14" font-weight="600">${esc(s.label)}</text>`:'';
    if (s.type==='line'||s.type==='arrow') {
      out+=`<line x1="${n(s.x1)}" y1="${n(s.y1)}" x2="${n(s.x2)}" y2="${n(s.y2)}" stroke="${stroke}" stroke-width="${sw}" ${s.type==='arrow'||s.arrowEnd?'marker-end="url(#shapeArrow)"':''} ${s.dash?'stroke-dasharray="8 6"':''}/>`;
    } else if (s.type==='point') {
      out+=`<circle cx="${n(s.cx)}" cy="${n(s.cy)}" r="${n(s.r,6,1,40)}" fill="${fill}" stroke="${stroke}" stroke-width="${sw}"/>`;
    } else if (s.type==='rect'||s.type==='rounded_rect') {
      out+=`<rect x="${n(s.x)}" y="${n(s.y)}" width="${n(s.width,100,1,2000)}" height="${n(s.height,70,1,1500)}" rx="${s.type==='rounded_rect'?n(s.rx,14,0,100):0}" fill="${fill}" stroke="${stroke}" stroke-width="${sw}"/>${label}`;
    } else if (s.type==='circle') {
      out+=`<circle cx="${n(s.cx)}" cy="${n(s.cy)}" r="${n(s.r,40,1,500)}" fill="${fill}" stroke="${stroke}" stroke-width="${sw}"/>${label}`;
    } else if (s.type==='ellipse') {
      out+=`<ellipse cx="${n(s.cx)}" cy="${n(s.cy)}" rx="${n(s.rx,60,1,600)}" ry="${n(s.ry,35,1,500)}" fill="${fill}" stroke="${stroke}" stroke-width="${sw}"/>${label}`;
    } else if (s.type==='triangle'||s.type==='polygon') {
      const p=points(s.points);
      if(p.length>=3) out+=`<polygon points="${p.map(q=>q.join(',')).join(' ')}" fill="${fill}" stroke="${stroke}" stroke-width="${sw}"/>${label}`;
    } else if (s.type==='spline') {
      const p=points(s.points);
      if(p.length>=2) {
        let d=`M ${p[0][0]} ${p[0][1]}`;
        for(let i=1;i<p.length;i++){const a=p[i-1],b=p[i],m=[(a[0]+b[0])/2,(a[1]+b[1])/2];d+=` Q ${a[0]} ${a[1]} ${m[0]} ${m[1]}`;}
        const last=p[p.length-1];d+=` T ${last[0]} ${last[1]}`;
        out+=`<path d="${d}" fill="none" stroke="${stroke}" stroke-width="${sw}" stroke-linecap="round" stroke-linejoin="round"/>`;
      }
    } else if (s.type==='path') {
      const d=String(s.d||'').slice(0,1500);
      if(/^[MmLlHhVvCcSsQqTtAaZz0-9eE+.,\s-]+$/.test(d)) out+=`<path d="${d}" fill="${fill}" stroke="${stroke}" stroke-width="${sw}"/>`;
    } else if (s.type==='text') {
      out+=`<text x="${n(s.x)}" y="${n(s.y)}" font-size="${n(s.fontSize,20,8,64)}" font-weight="${s.bold?'700':'400'}" fill="${color(s.fill,'#263449')}">${esc(s.text||'')}</text>`;
    }
  });
  const title=data.title||'Shape-based visual explainer';
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 650" width="1000" height="650"><title>${esc(title)}</title><defs><marker id="shapeArrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0 0 L0 6 L9 3Z" fill="#52627a"/></marker></defs><rect width="1000" height="650" fill="#fff"/><text x="35" y="48" font-family="Arial,sans-serif" font-size="27" font-weight="700" fill="#20242c">${esc(title)}</text><g font-family="Arial,sans-serif">${out}</g></svg>`;
}

async function readJsonResponse(response) {
  const contentType = response.headers.get('content-type') || '';
  const raw = await response.text();
  if (!contentType.includes('application/json')) {
    const preview = raw.slice(0,180).replace(/\s+/g,' ');
    throw new Error(`Server returned HTML instead of JSON (HTTP ${response.status}). ${preview}`);
  }
  let data;
  try { data = JSON.parse(raw); }
  catch { throw new Error(`Server returned invalid JSON (HTTP ${response.status}).`); }
  if (!response.ok) throw new Error(data.error || `Request failed (HTTP ${response.status}).`);
  return data;
}

async function generateStory() {
  const prompt=$('prompt').value.trim(), panels=Number($('panelCount').value);
  if(!prompt){$('message').textContent='Enter a story idea first.';return;}
  const button=$('generate'); button.disabled=true; button.textContent='Generating…'; $('message').textContent='';
  try {
    const response=await fetch('/api/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt,panels,mode:'story'})});
    const data=await readJsonResponse(response);
    latestStory=data; latestSvg=drawComic(data,panels); $('preview').innerHTML=latestSvg;
    $('comicTitle').textContent=data.title||'Generated story'; setDownloadsEnabled(true);
    $('message').textContent=data.warning || `Story generated using ${data.model||'Ollama'}.`;
  } catch(error) { $('message').textContent=error.message; }
  finally {button.disabled=false;button.textContent='Generate story';}
}

async function generateDiagram() {
  const prompt=$('prompt').value.trim(), diagramType=$('diagramType').value;
  if(!prompt){$('message').textContent='Enter a diagram description first.';return;}
  const button=$('generateDiagram'); button.disabled=true; button.textContent='Generating…'; $('message').textContent='';
  try {
    // Use the same Flask route as story mode; mode is the selected diagram type.
    const response=await fetch('/api/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt,mode:diagramType})});
    const data=await readJsonResponse(response);
    latestStory=data;
    latestSvg=diagramType==='flowchart'?renderFlowchart(data):diagramType==='pie'?renderPie(data):diagramType==='bar'?renderBar(data):diagramType==='venn'?renderVenn(data):renderShapes(data);
    $('preview').innerHTML=latestSvg; $('comicTitle').textContent=data.title||'Generated diagram'; setDownloadsEnabled(true);
    $('message').textContent=data.warning || `Diagram generated using ${data.model||'Ollama'}.`;
  } catch(error) { $('message').textContent=error.message; }
  finally {button.disabled=false;button.textContent='Generate diagram';}
}

$('mode').addEventListener('change',()=>{
  const storyMode=$('mode').value==='story';
  $('storyOptions').hidden=!storyMode; $('diagramOptions').hidden=storyMode;
  $('generate').textContent='Generate story';
});
$('generate').addEventListener('click',generateStory);
$('generateDiagram').addEventListener('click',generateDiagram);

$('downloadSvg').addEventListener('click',()=>{if(latestSvg)downloadBlob(latestSvg,'image/svg+xml;charset=utf-8','visual.svg');});
$('downloadPng').addEventListener('click',()=>downloadRaster('png').catch(e=>$('message').textContent=e.message));
$('downloadJpg').addEventListener('click',()=>downloadRaster('jpg').catch(e=>$('message').textContent=e.message));
$('downloadWebp').addEventListener('click',()=>downloadRaster('webp').catch(e=>$('message').textContent=e.message));
$('downloadJson').addEventListener('click',()=>{if(latestStory)downloadBlob(JSON.stringify(latestStory,null,2),'application/json','visual-data.json');});
checkHealth();
