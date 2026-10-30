const $=id=>document.getElementById(id);
let deck=[], outline=null, selected=0, title="Presentation", themeName="midnight_blue", templates=[], themes={};
const escapeHtml=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
function toast(s){$("toast").textContent=s;$("toast").style.display="block";setTimeout(()=>$("toast").style.display="none",4500)}
async function api(url,body){const r=await fetch(url,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});const ct=r.headers.get("content-type")||"";if(!ct.includes("application/json"))throw new Error("Server returned a non-JSON response. Check the Flask console.");const d=await r.json();if(!r.ok)throw new Error(d.error||"Request failed");return d}
const needsVisual=t=>["image_only","text_image_left","text_image_right","text_image_top","image_left","image_right"].includes(t);
function defaultVisualPrompt(s){return `Create a polished educational illustration for: ${s.title}. ${s.subtitle||""} ${s.bullets?.slice(0,3).join("; ")||""}. Use a landscape 16:9 composition, clear visual hierarchy, readable concise labels, and no decorative clutter.`}
async function init(){const c=await fetch("/api/catalog").then(r=>r.json());templates=c.templates;themes=c.themes;
 $("slideTemplate").innerHTML=templates.map(t=>`<option value="${t.id}">${t.name}</option>`).join("");
 $("theme").innerHTML=Object.keys(themes).map(t=>`<option value="${t}">${t.replaceAll("_"," ")}</option>`).join("");
 $("makeOutline").onclick=makeOutline;$("rebuildOutline").onclick=makeOutline;$("approveOutline").onclick=approveOutline;
 $("redo").onclick=redoSlide;$("visualBtn").onclick=redoVisual;$("removeVisual").onclick=removeVisual;$("save").onclick=savePpt;
 $("prev").onclick=()=>selectSlide(selected-1);$("next").onclick=()=>selectSlide(selected+1);
 $("theme").onchange=()=>{themeName=$("theme").value;render()};
 $("slideTemplate").onchange=async()=>{if(deck[selected]){deck[selected].template=$("slideTemplate").value;const s=deck[selected];if(needsVisual(s.template)){s.visual_needed=true;if(!s.visual_prompt)s.visual_prompt=defaultVisualPrompt(s);render();await redoVisual()}else render()}};
 try{const h=await fetch("/api/health").then(r=>r.json());$("status").textContent=h.ollama_error?"Ollama unavailable":"Ollama connected · PPT + SVG built in"}catch{$("status").textContent="Service check unavailable"}
}
function brief(){return {topic:$("topic").value.trim(),slide_count:+$("slideCount").value,audience:$("audience").value,instructions:$("instructions").value}}
async function makeOutline(){const b=brief();if(!b.topic)return toast("Enter a presentation topic.");$("makeOutline").disabled=true;$("makeOutline").textContent="Creating outline…";
 try{outline=await api("/api/generate-outline",b);title=outline.presentation_title||b.topic;renderOutline();$("outlinePanel").classList.remove("hidden");$("editorPanel").classList.add("hidden");$("deckTitle").textContent=title;$("deckMeta").textContent=`Outline ready · ${outline.slides.length} slides · Review before approval`;toast("Outline created. Review and edit it, then approve.");}
 catch(e){toast(e.message)}finally{$("makeOutline").disabled=false;$("makeOutline").textContent="Create slide outline"}}
function renderOutline(){$("outlineList").innerHTML=outline.slides.map((s,i)=>`<article class="outline-card" data-i="${i}">
 <div class="outline-top"><b>Slide ${i+1}</b><button class="text-btn" data-remove="${i}">Remove</button></div>
 <label>Title</label><input data-field="title" value="${escapeHtml(s.title)}">
 <label>Purpose</label><textarea data-field="purpose" rows="2">${escapeHtml(s.purpose)}</textarea>
 <label>Key points (one per line)</label><textarea data-field="key_points" rows="3">${escapeHtml((s.key_points||[]).join("\n"))}</textarea>
 <div class="two"><div><label>Suggested layout</label><select data-field="suggested_layout">${templates.map(t=>`<option value="${t.id}" ${t.id===s.suggested_layout?"selected":""}>${t.name}</option>`).join("")}</select></div><div><label>Visual?</label><select data-field="visual_needed"><option value="true" ${s.visual_needed?"selected":""}>Yes, generate SVG</option><option value="false" ${!s.visual_needed?"selected":""}>No, text/layout</option></select></div></div>
 <label>Visual explanation (if needed)</label><textarea data-field="visual_prompt" rows="2">${escapeHtml(s.visual_prompt||"")}</textarea>
 </article>`).join("");
 document.querySelectorAll(".outline-card").forEach(card=>{const i=+card.dataset.i;card.querySelectorAll("[data-field]").forEach(el=>el.onchange=()=>{let k=el.dataset.field,v=el.value;if(k==="key_points")v=v.split("\n").map(x=>x.trim()).filter(Boolean);if(k==="visual_needed")v=v==="true";outline.slides[i][k]=v;if(k==="suggested_layout"&&needsVisual(v)){outline.slides[i].visual_needed=true;if(!outline.slides[i].visual_prompt)outline.slides[i].visual_prompt=defaultVisualPrompt(outline.slides[i]);renderOutline()}});card.querySelector("[data-remove]").onclick=()=>{outline.slides.splice(i,1);renderOutline()}})}
async function approveOutline(){if(!outline||!outline.slides.length)return toast("The outline has no slides.");$("approveOutline").disabled=true;$("approveOutline").textContent="Generating full slide content…";
 try{const b=brief();const d=await api("/api/generate-content",{topic:b.topic,audience:b.audience,outline});deck=d.slides.map((s,i)=>{const template=s.template||outline.slides[i].suggested_layout;const visual_needed=needsVisual(template)||!!(s.visual_needed??outline.slides[i].visual_needed);const item={...s,template,visual:null,visual_prompt:s.visual_prompt||outline.slides[i].visual_prompt,visual_needed};if(visual_needed&&!item.visual_prompt)item.visual_prompt=defaultVisualPrompt(item);return item});
 title=d.presentation_title||title;selected=0;$("editorPanel").classList.remove("hidden");$("deckTitle").textContent=title;$("deckMeta").textContent=`${deck.length} slides · Approved outline · ${d.source||"Ollama"}`;$("prev").disabled=false;$("next").disabled=false;render();toast("Slide content generated. SVG illustrations are generated by this app using Ollama.");await generateNeededVisuals();}
 catch(e){toast(e.message)}finally{$("approveOutline").disabled=false;$("approveOutline").textContent="Approve outline & generate slides"}}
async function generateNeededVisuals(){for(let i=0;i<deck.length;i++){const s=deck[i];if(!s.visual_needed&&!needsVisual(s.template))continue;if(!s.visual_prompt)s.visual_prompt=defaultVisualPrompt(s);try{const d=await api("/api/generate-visual",{prompt:s.visual_prompt});s.visual=d.visual;s.visual_error="";if(i===selected)render()}catch(e){s.visual_error=e.message;console.warn("SVG visual failed",i,e.message);if(i===selected)render()}}render()}
function selectSlide(i){if(i<0||i>=deck.length)return;selected=i;render()}
function render(){if(!deck.length)return;const s=deck[selected],t=themes[themeName],layout=s.template||"two_column";$ ("slideCounter").textContent=`${selected+1} / ${deck.length}`;$ ("prev").disabled=selected===0;$ ("next").disabled=selected===deck.length-1;$ ("slideTemplate").value=layout;$ ("visualPrompt").value=s.visual_prompt||"";
 const p=$("preview");p.className="slide-preview";p.style.background="#"+t.bg;p.style.color="#"+t.text;
 const bullets=(s.bullets||[]).map(b=>`<div>• ${escapeHtml(b)}</div>`).join("");
 const visual=s.visual?`<img class="visual" src="data:image/svg+xml;charset=utf-8,${encodeURIComponent(shapesToSvg(s.visual))}">`:`<div class="visual-placeholder" style="background:#${t.surface};border-radius:7px;display:grid;place-items:center;color:#${t.muted};font-size:12px;padding:15px;text-align:center">${s.visual_error?`SVG failed: ${escapeHtml(s.visual_error)}`:"Image is being generated or is not available"}</div>`;
 const hasVisual=!!s.visual, imageRequired=needsVisual(layout);
 let body="";
 if(layout==="image_only")body=`<div class="preview-image-only">${visual}</div>`;
 else if(layout==="text_only")body=`<div class="slide-bullets preview-text-only">${bullets}</div>`;
 else if(["text_image_left","image_left"].includes(layout))body=`<div class="preview-two-col image-first">${visual}<div class="slide-bullets">${bullets}</div></div>`;
 else if(["text_image_right","image_right"].includes(layout))body=`<div class="preview-two-col"> <div class="slide-bullets">${bullets}</div>${visual}</div>`;
 else if(layout==="text_image_top")body=`<div class="preview-image-top">${visual}<div class="slide-bullets">${bullets}</div></div>`;
 else if(layout==="title_hero")body=`<div class="preview-two-col"><div><div class="subtitle">${escapeHtml(s.subtitle||"")}</div><div class="slide-bullets">${bullets}</div></div>${hasVisual?visual:""}</div>`;
 else body=`<div class="slide-bullets preview-text-only">${bullets}</div>${hasVisual?`<div class="preview-small-visual">${visual}</div>`:""}`;
 p.innerHTML=`<h2>${escapeHtml(s.title)}</h2>${s.subtitle&&layout!=="title_hero"?`<div class="subtitle" style="color:#${t.muted}">${escapeHtml(s.subtitle)}</div>`:""}${body}<div class="slide-footer">${selected+1} / ${deck.length} · ${layout.replaceAll("_"," ")}</div>`;
 if(imageRequired&&!hasVisual)p.classList.add("needs-image");
 $("thumbs").innerHTML=deck.map((x,i)=>`<button class="thumb ${i===selected?"active":""}" data-i="${i}"><div class="mini" style="background:#${t.bg};color:#${t.text}"><b>${escapeHtml(x.title)}</b><i></i><i style="width:55%"></i></div><strong>${i+1}. ${escapeHtml(x.title)}</strong><small>${(x.template||"").replaceAll("_"," ")}${x.visual?" · SVG":needsVisual(x.template)?" · image pending":""}</small></button>`).join("");
 document.querySelectorAll(".thumb").forEach(b=>b.onclick=()=>selectSlide(+b.dataset.i));$("thumbInfo").textContent=`${deck.length} slides`}
function shapesToSvg(data){let out=['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 650" width="1000" height="650"><rect width="100%" height="100%" fill="#fff"/>'];const num=v=>Math.max(-5000,Math.min(5000,Number(v)||0)),color=(v,d)=>/^#[0-9a-fA-F]{6}$/.test(v||"")?v:d,esc=escapeHtml;
 for(const s of (data.shapes||[]).slice(0,40)){let f=color(s.fill,"#dbeafe"),st=color(s.stroke,"#334155"),w=num(s.strokeWidth||3),label=esc(s.label||"");
 if(["line","arrow"].includes(s.type))out.push(`<line x1="${num(s.x1)}" y1="${num(s.y1)}" x2="${num(s.x2)}" y2="${num(s.y2)}" stroke="${st}" stroke-width="${w}"/>`);
 else if(["rect","rounded_rect"].includes(s.type)){let x=num(s.x),y=num(s.y),ww=num(s.width),h=num(s.height);out.push(`<rect x="${x}" y="${y}" width="${ww}" height="${h}" rx="${s.type==="rounded_rect"?14:0}" fill="${f}" stroke="${st}" stroke-width="${w}"/>`);if(label)out.push(`<text x="${x+ww/2}" y="${y+h/2}" text-anchor="middle" dominant-baseline="middle" font-size="24" fill="#172033">${label}</text>`)}
 else if(["circle","point","ellipse"].includes(s.type)){let cx=num(s.cx),cy=num(s.cy),rx=num(s.rx??s.r??8),ry=num(s.ry??rx);out.push(`<ellipse cx="${cx}" cy="${cy}" rx="${rx}" ry="${ry}" fill="${f}" stroke="${st}" stroke-width="${w}"/>`);if(label)out.push(`<text x="${cx}" y="${cy+ry+25}" text-anchor="middle" font-size="22" fill="#172033">${label}</text>`)}
 else if(["triangle","polygon"].includes(s.type)){let pts=(s.points||[]).slice(0,30).map(p=>`${num(p[0])},${num(p[1])}`).join(" ");if(pts)out.push(`<polygon points="${pts}" fill="${f}" stroke="${st}" stroke-width="${w}"/>`)}
 else if(s.type==="spline"){let pts=s.points||[];if(pts.length>1)out.push(`<polyline points="${pts.slice(0,30).map(p=>`${num(p[0])},${num(p[1])}`).join(" ")}" fill="none" stroke="${st}" stroke-width="${w}"/>`)}
 else if(s.type==="text")out.push(`<text x="${num(s.x)}" y="${num(s.y)}" font-size="${num(s.fontSize||22)}" fill="${color(s.fill,"#172033")}">${esc(s.text||"")}</text>`)}
 return out.join("")+"</svg>"}
async function redoSlide(){const s=deck[selected],prompt=$("redoPrompt").value.trim();if(!prompt)return toast("Enter an updated prompt.");$("redo").disabled=true;
 try{const d=await api("/api/regenerate-slide",{topic:$("topic").value,slide:s,prompt});deck[selected]={...s,...d,template:d.template||s.template,visual:null,visual_needed:d.visual_needed??s.visual_needed};if(needsVisual(deck[selected].template)){deck[selected].visual_needed=true;if(!deck[selected].visual_prompt)deck[selected].visual_prompt=defaultVisualPrompt(deck[selected])}render();if(deck[selected].visual_needed&&deck[selected].visual_prompt)await redoVisual();toast("Selected slide regenerated.")}
 catch(e){toast(e.message)}finally{$("redo").disabled=false}}
async function redoVisual(){const s=deck[selected],prompt=$("visualPrompt").value.trim()||s.visual_prompt||s.title;if(!prompt)return toast("Enter an SVG visual prompt.");s.visual_prompt=prompt;s.visual_needed=true;$("visualBtn").disabled=true;
 try{const d=await api("/api/generate-visual",{prompt:`${prompt}. Slide context: ${s.title}. Create a clean professional presentation illustration, landscape composition, concise labels.`});s.visual=d.visual;render();toast("SVG visual generated inside this app.")}
 catch(e){toast(e.message)}finally{$("visualBtn").disabled=false}}
function removeVisual(){if(deck[selected]){deck[selected].visual=null;deck[selected].visual_needed=false;render()}}
async function savePpt(){
 if(!deck.length)return toast("Generate slide content first.");
 const missing=deck.map((s,i)=>({s,i})).filter(({s})=>(needsVisual(s.template)||s.visual_needed)&&!s.visual);
 if(missing.length){selected=missing[0].i;render();return toast(`Generate the SVG illustration for slide ${selected+1} before exporting. ${missing.length} slide(s) still need images.`)}
 const payload={presentation_title:title,theme:themeName,slides:deck};$("save").disabled=true;const oldLabel=$("save").textContent;$("save").textContent="Building PPTX…";
 try{const r=await fetch("/api/export-pptx",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});if(!r.ok){let d={};try{d=await r.json()}catch{}throw new Error(d.error||"PowerPoint export failed")}
 const embedded=Number(r.headers.get("X-Embedded-Visuals")||0);const blob=await r.blob(),url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download=(title.replace(/[^A-Za-z0-9_-]+/g,"_")||"presentation")+".pptx";document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1500);toast(`PowerPoint created with ${embedded} embedded SVG illustration(s).`)}
 catch(e){toast(e.message)}finally{$("save").disabled=false;$("save").textContent=oldLabel}}
init();
