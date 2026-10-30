from __future__ import annotations
import json, os, re, math, io, html
from pathlib import Path
from typing import Any
import requests
from flask import Flask, jsonify, render_template, request, send_file
from dotenv import load_dotenv
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.dml import MSO_THEME_COLOR
from pptx.enum.text import MSO_AUTO_SIZE

load_dotenv()
app = Flask(__name__)
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4:cloud")
EXPORT_DIR = Path(os.getenv("EXPORT_DIR", "exports"))
EXPORT_DIR.mkdir(exist_ok=True)

THEMES = {
 "midnight_blue": {"bg":"101B35","surface":"1B2B4A","primary":"6EA8FE","accent":"F4B860","text":"F4F7FC","muted":"B7C4D9"},
 "minimal_light": {"bg":"FFFFFF","surface":"F2F5F9","primary":"2457A6","accent":"E58B45","text":"172033","muted":"65728A"},
 "forest": {"bg":"102B24","surface":"1D4035","primary":"83C5A2","accent":"E7C66A","text":"F2F8F3","muted":"B7CCBF"},
 "sunset": {"bg":"2A1830","surface":"43243D","primary":"FF8A65","accent":"FFD166","text":"FFF5F0","muted":"E5C7D4"},
 "ocean": {"bg":"092B3B","surface":"12465A","primary":"4CC9D8","accent":"8CE0C2","text":"F1FBFF","muted":"B5D5DF"},
 "royal_purple": {"bg":"211638","surface":"382653","primary":"B69CFF","accent":"F3A6D8","text":"FAF6FF","muted":"D0C4E4"},
 "corporate_gray": {"bg":"202833","surface":"303B49","primary":"8FB3D9","accent":"E5B567","text":"F6F8FA","muted":"C1CAD4"},
 "warm_cream": {"bg":"F7F0E4","surface":"EDE1CF","primary":"9B5E3C","accent":"D49A45","text":"35271F","muted":"79695E"},
 "high_contrast": {"bg":"050505","surface":"202020","primary":"FFFF00","accent":"00E5FF","text":"FFFFFF","muted":"D0D0D0"},
 "tech_neon": {"bg":"0A1020","surface":"151F37","primary":"00E5FF","accent":"B7FF5A","text":"F1F7FF","muted":"A5B4CE"}
}

TEMPLATES = [
 {"id":"title_hero","name":"Title Hero","desc":"Large title with subtitle and visual"},
 {"id":"agenda","name":"Agenda","desc":"Numbered agenda or contents"},
 {"id":"section","name":"Section Divider","desc":"Bold section title and short statement"},
 {"id":"two_column","name":"Two Columns","desc":"Balanced text columns"},
 {"id":"three_column","name":"Three Columns","desc":"Three concepts or pillars"},
 {"id":"image_only","name":"Image Only","desc":"Large full-slide illustration with title"},
 {"id":"text_only","name":"Text Only","desc":"Text-focused slide without artwork"},
 {"id":"text_image_left","name":"Text + Image (Image Left)","desc":"Text right, large illustration left"},
 {"id":"text_image_right","name":"Text + Image (Image Right)","desc":"Text left, large illustration right"},
 {"id":"text_image_top","name":"Text + Image (Image Top)","desc":"Large illustration above concise text"},
 {"id":"image_left","name":"Image Left (Legacy)","desc":"Illustration left, text right"},
 {"id":"image_right","name":"Image Right (Legacy)","desc":"Text left, illustration right"},
 {"id":"problem_solution","name":"Problem / Solution","desc":"Contrast problem and solution"},
 {"id":"timeline","name":"Timeline","desc":"Chronological milestones"},
 {"id":"process","name":"Process Steps","desc":"Sequential steps with connectors"},
 {"id":"comparison","name":"Comparison","desc":"Compare two or more options"},
 {"id":"kpi_cards","name":"KPI Cards","desc":"Metrics and key numbers"},
 {"id":"quote","name":"Quote Spotlight","desc":"Prominent quote and attribution"},
 {"id":"data_chart","name":"Data / Chart","desc":"Chart-like values and takeaways"},
 {"id":"pyramid","name":"Pyramid","desc":"Hierarchy or maturity levels"},
 {"id":"swot","name":"SWOT Matrix","desc":"Four-quadrant analysis"},
 {"id":"architecture","name":"Architecture","desc":"System components and connections"},
 {"id":"case_study","name":"Case Study","desc":"Context, action, result"},
 {"id":"summary","name":"Key Takeaways","desc":"Three to five concise takeaways"},
 {"id":"closing","name":"Closing / Q&A","desc":"Final message and next step"}
]

def parse_json(text: str) -> dict:
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.I)
    a, b = text.find("{"), text.rfind("}")
    if a < 0 or b <= a: raise ValueError("Model did not return a JSON object")
    return json.loads(text[a:b+1])

def ollama_json(system: str, prompt: str, timeout: int = 180) -> dict:
    r = requests.post(f"{OLLAMA_URL}/api/chat", json={
        "model": OLLAMA_MODEL, "stream": False, "format": "json",
        "messages":[{"role":"system","content":system},{"role":"user","content":prompt}],
        "options":{"temperature":0.45}
    }, timeout=timeout)
    r.raise_for_status()
    return parse_json(r.json().get("message",{}).get("content",""))

def default_deck(topic: str, count: int) -> dict:
    slides=[]
    for i in range(count):
        slides.append({"title": f"{topic}: {['Overview','Context','Core ideas','How it works','Benefits','Implementation','Risks','Next steps'][i%8]}",
          "subtitle": "", "bullets":[f"Explain the key idea of {topic}", "Connect the concept to a practical example", "Highlight the decision or takeaway"],
          "visual_prompt": f"Create a clean educational visual explaining {topic}, slide {i+1}",
          "speaker_notes": ""})
    return {"presentation_title":topic,"audience":"General","slides":slides}

@app.get("/")
def home():
    return render_template("index.html", templates=TEMPLATES, themes=list(THEMES.keys()), model=OLLAMA_MODEL)

@app.get("/api/health")
def health():
    result={"ok":True,"ollama_model":OLLAMA_MODEL,"ollama_url":OLLAMA_URL,
            "visual_generation":"Integrated in this Flask application"}
    try:
        r=requests.get(f"{OLLAMA_URL}/api/tags",timeout=3); r.raise_for_status()
        result["ollama_models"]=[m.get("name") for m in r.json().get("models",[])]
    except Exception as e: result["ollama_error"]=str(e)
    result["ok"]=not bool(result.get("ollama_error"))
    return jsonify(result), (200 if result["ok"] else 503)

@app.get("/api/catalog")
def catalog():
    return jsonify({"templates":TEMPLATES,"themes":THEMES})

@app.post("/api/generate-outline")
def generate_outline():
    body=request.get_json(silent=True) or {}
    topic=str(body.get("topic","")).strip()
    if not topic: return jsonify({"error":"Enter a presentation topic."}),400
    try: count=max(3,min(20,int(body.get("slide_count",10))))
    except Exception: count=10
    audience=str(body.get("audience","General audience"))
    instructions=str(body.get("instructions",""))
    system="""You are a presentation instructional designer. Return ONLY valid JSON:
{"presentation_title":"...","audience":"...","learning_objective":"...","slides":[{"title":"...","purpose":"...","key_points":["..."],"visual_needed":true,"visual_reason":"...","visual_prompt":"...","suggested_layout":"..."}]}
Create exactly the requested slide count. Make a coherent progression: opening/context, foundational concepts, detailed explanation, worked examples or applications, synthesis and conclusion. Every slide must add new information and must be specific to the topic. Never use generic placeholder bullets. For conceptual explanations, identify which ideas are clearer as a diagram and set visual_needed true only where an image genuinely improves understanding. Select suggested_layout from: title_hero, agenda, section, text_only, image_only, text_image_left, text_image_right, text_image_top, two_column, three_column, image_left, image_right, problem_solution, timeline, process, comparison, kpi_cards, quote, data_chart, pyramid, swot, architecture, case_study, summary, closing. Do not invent statistics."""
    prompt=f"Topic: {topic}\nAudience: {audience}\nNumber of slides: {count}\nAdditional direction: {instructions}\nCreate a detailed slide-by-slide outline, not full slide content."
    try:
        data=ollama_json(system,prompt)
        slides=data.get("slides")
        if not isinstance(slides,list) or len(slides)!=count: raise ValueError(f"Expected {count} outline slides")
        valid={t["id"] for t in TEMPLATES}
        for s in slides:
            s.setdefault("title","Untitled"); s.setdefault("purpose",""); s.setdefault("key_points",[])
            s.setdefault("visual_needed",False); s.setdefault("visual_reason",""); s.setdefault("visual_prompt","")
            if s.get("suggested_layout") not in valid: s["suggested_layout"]="two_column"
        data["slides"]=slides
        data["source"]="ollama"
        return jsonify(data)
    except Exception as e:
        return jsonify({"error":f"Outline generation failed: {e}"}),503

@app.post("/api/generate-content")
def generate_content():
    body=request.get_json(silent=True) or {}
    outline=body.get("outline") or {}
    outline_slides=outline.get("slides")
    if not isinstance(outline_slides,list) or not outline_slides:
        return jsonify({"error":"Approved slide outline is required."}),400
    topic=str(body.get("topic") or outline.get("presentation_title") or "Presentation")
    audience=str(body.get("audience") or outline.get("audience") or "General audience")
    system="""You are an expert educator, subject-matter explainer and presentation designer. Return ONLY JSON:
{"presentation_title":"...","slides":[{"title":"...","subtitle":"...","bullets":["..."],"speaker_notes":"...","template":"two_column","visual_needed":true,"visual_prompt":"..."}]}
Create exactly one full slide for each supplied outline item, in the same order. Preserve every outline slide's intent and key points, expanding them into accurate, detailed but presentation-ready content. Each slide must contain 3-5 meaningful bullets; each bullet should explain a distinct point with enough detail to teach the audience, not generic filler. Use examples and definitions where appropriate. Select the best layout for each individual slide from: title_hero, agenda, section, text_only, image_only, text_image_left, text_image_right, text_image_top, two_column, three_column, image_left, image_right, problem_solution, timeline, process, comparison, kpi_cards, quote, data_chart, pyramid, swot, architecture, case_study, summary, closing. Set visual_needed true only if a diagram, process, conceptual illustration, comparison, or other visual will explain the content better than text. If true, write a specific visual_prompt for the SVG shape generator. Never fabricate numerical data. For data/chart slides use qualitative or explicitly illustrative values unless data was provided. No markdown."""
    prompt=f"Topic: {topic}\nAudience: {audience}\nApproved outline (follow this structure exactly):\n{json.dumps(outline_slides,ensure_ascii=False)}\nReturn exactly {len(outline_slides)} slides."
    try:
        data=ollama_json(system,prompt,timeout=240)
        slides=data.get("slides")
        if not isinstance(slides,list) or len(slides)!=len(outline_slides): raise ValueError("Model returned a different slide count than the approved outline.")
        valid={t["id"] for t in TEMPLATES}
        for i,s in enumerate(slides):
            s.setdefault("title",outline_slides[i].get("title","Untitled"))
            s.setdefault("subtitle",""); s.setdefault("bullets",[]); s.setdefault("speaker_notes","")
            s.setdefault("visual_needed",bool(outline_slides[i].get("visual_needed")))
            s.setdefault("visual_prompt",outline_slides[i].get("visual_prompt",""))
            approved_layout=outline_slides[i].get("suggested_layout")
            if approved_layout in valid:
                s["template"]=approved_layout
            elif s.get("template") not in valid:
                s["template"]="two_column"
            if s["template"] in {"image_only","text_image_left","text_image_right","text_image_top","image_left","image_right"}:
                s["visual_needed"]=True
                if not s["visual_prompt"]:
                    s["visual_prompt"]=f"Create a clear, professional educational illustration for the slide: {s['title']}. Context: {topic}. Use a landscape composition, readable labels, and a clean visual hierarchy."
        data["slides"]=slides; data["source"]="ollama"
        return jsonify(data)
    except Exception as e:
        return jsonify({"error":f"Slide content generation failed: {e}"}),503

@app.post("/api/regenerate-slide")
def regenerate_slide():
    body=request.get_json(silent=True) or {}
    topic=str(body.get("topic","Presentation")).strip()
    slide=body.get("slide") or {}
    prompt=str(body.get("prompt","")).strip()
    if not prompt: return jsonify({"error":"Enter an updated prompt for this slide."}),400
    system="""Return ONLY JSON for one presentation slide: {"title":"...","subtitle":"...","bullets":["..."],"template":"two_column","visual_needed":true,"visual_prompt":"...","speaker_notes":"..."}.
Keep 3-5 informative bullets. Respect the requested change while preserving factual accuracy. Choose the best layout from the known template list. Set visual_needed true only when a diagram genuinely helps explain the slide. No markdown."""
    try:
        data=ollama_json(system,f"Presentation topic: {topic}\nCurrent slide: {json.dumps(slide,ensure_ascii=False)}\nRequested revision: {prompt}")
        for k,v in {"title":"Updated slide","subtitle":"","bullets":[],"visual_prompt":prompt,"speaker_notes":""}.items(): data.setdefault(k,v)
        data["source"]="ollama"
        return jsonify(data)
    except Exception as e:
        revised=dict(slide)
        revised["title"]=revised.get("title") or "Updated slide"
        revised["bullets"]=(revised.get("bullets") or [])[:4]+[f"Revision requested: {prompt}"]
        revised["visual_prompt"]=prompt
        revised["visual_needed"]=True
        revised["source"]="fallback"
        revised["warning"]=str(e)
        return jsonify(revised)

@app.post("/api/generate-visual")
def generate_visual():
    body=request.get_json(silent=True) or {}
    prompt=str(body.get("prompt","")).strip()
    if not prompt: return jsonify({"error":"Visual prompt is required."}),400
    # SVG illustration generation runs inside this same Flask application and
    # uses the same configured Ollama model as slide-content generation.
    system = """You are an expert SVG educational illustrator. Return ONLY valid JSON, no markdown.
Schema: {\"title\":\"Short visual title\",\"description\":\"What the visual explains\",\"shapes\":[{"type":"rounded_rect","x":80,"y":100,"width":220,"height":100,"fill":"#dceeff","stroke":"#315b8a","strokeWidth":3,"label":"Main concept"},{"type":"arrow","x1":300,"y1":150,"x2":395,"y2":150,"stroke":"#333333","strokeWidth":3},{"type":"circle","cx":500,"cy":150,"r":55,"fill":"#fce3b2","stroke":"#bd7a20","label":"Related idea"},{"type":"text","x":100,"y":500,"text":"Explanation","fontSize":20,"fill":"#263449"}]}.
Canvas is 1000x650. Use 6-18 meaningful shapes. Supported types: line, arrow, point, rect, rounded_rect, circle, ellipse, triangle, polygon, spline, text. Use valid #RRGGBB colors. For polygons use points:[[x,y],...]. For spline use points:[[x,y],...]. Keep labels short and readable, distribute elements across canvas, explain the specific topic as a diagram or concept illustration, not as decoration. Do not invent numerical data. Avoid tiny text."""
    try:
        data=ollama_json(system, f"Create a professional slide illustration for this request: {prompt}\nReturn the shapes schema exactly.", timeout=240)
        shapes=data.get("shapes")
        if not isinstance(shapes,list) or len(shapes)<2:
            raise ValueError("Ollama returned no usable SVG shapes. Try a more specific visual prompt.")
        data["shapes"] = shapes[:40]
        data["mode"] = "shapes"
        data["source"] = "ollama_integrated"
        return jsonify({"visual":data,"source":"ollama_integrated","model":OLLAMA_MODEL})
    except Exception as e:
        return jsonify({"error":f"Integrated SVG generation failed: {e}","model":OLLAMA_MODEL}),503

def rgb(hexstr):
    h=hexstr.lstrip("#")
    return RGBColor(int(h[0:2],16),int(h[2:4],16),int(h[4:6],16))

def add_text(slide, text, x,y,w,h, color, size=18, bold=False, font="Aptos", align=None):
    box=slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf=box.text_frame; tf.clear(); tf.word_wrap=True
    tf.margin_left=Inches(.05); tf.margin_right=Inches(.05); tf.margin_top=Inches(.03); tf.margin_bottom=Inches(.03)
    p=tf.paragraphs[0]; p.text=str(text or "")
    if align is not None: p.alignment=align
    for run in p.runs:
        run.font.name=font; run.font.size=Pt(size); run.font.bold=bold; run.font.color.rgb=color
    return box

def svg_from_shapes(data: dict) -> str:
    W,H=1000,650
    out=[
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">',
        '<defs><marker id="arr" markerWidth="12" markerHeight="12" refX="9" refY="6" orient="auto" markerUnits="strokeWidth"><path d="M 0 0 L 12 6 L 0 12 z" fill="#334155"/></marker></defs>',
        '<rect width="100%" height="100%" fill="#ffffff"/>'
    ]
    def n(v,default=0): 
        try:return max(-5000,min(5000,float(v)))
        except:return default
    def col(v,default="#64748b"): return v if isinstance(v,str) and re.fullmatch(r"#[0-9a-fA-F]{6}",v) else default
    for sh in data.get("shapes",[])[:40]:
        typ=sh.get("type"); fill=col(sh.get("fill"),"#dbeafe"); stroke=col(sh.get("stroke"),"#334155")
        sw=n(sh.get("strokeWidth",3),3); label=html.escape(str(sh.get("label","")))
        if typ in ("line","arrow"):
            x1,y1,x2,y2=[n(sh.get(k)) for k in ("x1","y1","x2","y2")]
            out.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{stroke}" stroke-width="{sw}" '+('marker-end="url(#arr)"' if typ=="arrow" else '')+'/>')
        elif typ in ("rect","rounded_rect"):
            x,y,w,h=[n(sh.get(k)) for k in ("x","y","width","height")]
            out.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{14 if typ=="rounded_rect" else 0}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
            if label: out.append(f'<text x="{x+w/2}" y="{y+h/2}" text-anchor="middle" dominant-baseline="middle" font-family="Arial" font-size="24" fill="#172033">{label}</text>')
        elif typ in ("circle","point","ellipse"):
            cx=n(sh.get("cx")); cy=n(sh.get("cy")); rx=n(sh.get("rx",sh.get("r",8))); ry=n(sh.get("ry",rx))
            out.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
            if label: out.append(f'<text x="{cx}" y="{cy+ry+25}" text-anchor="middle" font-family="Arial" font-size="22" fill="#172033">{label}</text>')
        elif typ in ("triangle","polygon"):
            pts=sh.get("points",[])
            points=" ".join(f'{n(p[0])},{n(p[1])}' for p in pts[:30] if isinstance(p,(list,tuple)) and len(p)>=2)
            if points: out.append(f'<polygon points="{points}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
            if label and pts: out.append(f'<text x="{n(pts[0][0])+30}" y="{n(pts[0][1])+30}" font-family="Arial" font-size="22" fill="#172033">{label}</text>')
        elif typ=="spline":
            pts=sh.get("points",[])
            if len(pts)>=2:
                d="M "+" L ".join(f'{n(p[0])} {n(p[1])}' for p in pts[:30])
                out.append(f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{sw}" stroke-linecap="round"/>')
        elif typ=="text":
            x,y=n(sh.get("x")),n(sh.get("y")); txt=html.escape(str(sh.get("text","")))
            out.append(f'<text x="{x}" y="{y}" font-family="Arial" font-size="{n(sh.get("fontSize",22))}" fill="{col(sh.get("fill"),"#172033")}">{txt}</text>')
    out.append("</svg>")
    return "".join(out)

def normalize_visual(visual):
    """Accept the API visual object or its common nested response wrappers."""
    if not isinstance(visual, dict):
        raise ValueError("Visual data must be a JSON object.")
    if isinstance(visual.get("visual"), dict):
        visual = visual["visual"]
    shapes = visual.get("shapes")
    if not isinstance(shapes, list) or not shapes:
        raise ValueError("Visual has no SVG shapes. Regenerate the slide illustration before exporting.")
    clean=[]
    for shape in shapes:
        if isinstance(shape, dict) and isinstance(shape.get("type"), str):
            clean.append(shape)
    if not clean:
        raise ValueError("Visual contains no supported shapes.")
    return {**visual, "shapes": clean[:40]}

def render_visual_png(visual: dict, width: int = 2000, height: int = 1300) -> bytes:
    """Rasterize the app's SVG shape model with Pillow (no Cairo/native DLLs)."""
    from PIL import Image, ImageDraw, ImageFont
    scale_x, scale_y = width / 1000.0, height / 650.0
    img = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(img)

    def xy(v, scale):
        try: return int(float(v) * scale)
        except (TypeError, ValueError): return 0

    def color(value, default):
        return value if isinstance(value, str) and re.fullmatch(r"#[0-9a-fA-F]{6}", value) else default

    def font(size):
        px = max(10, int(float(size) * (scale_x + scale_y) / 2))
        for candidate in ("C:/Windows/Fonts/arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"):
            try: return ImageFont.truetype(candidate, px)
            except OSError: pass
        return ImageFont.load_default()

    def label_text(text, center, y, fnt, fill="#172033"):
        if not text: return
        lines = str(text).splitlines()[:4]
        for i, line in enumerate(lines):
            box = draw.textbbox((0, 0), line, font=fnt)
            draw.text((center - (box[2]-box[0]) / 2, y + i * (box[3]-box[1]+4)), line, font=fnt, fill=fill)

    for sh in visual.get("shapes", [])[:40]:
        typ = sh.get("type")
        fill = color(sh.get("fill"), "#dbeafe")
        stroke = color(sh.get("stroke"), "#334155")
        sw = max(1, int(float(sh.get("strokeWidth", 3)) * (scale_x + scale_y) / 2))
        if typ in ("line", "arrow"):
            x1,y1,x2,y2 = [float(sh.get(k, 0) or 0) for k in ("x1","y1","x2","y2")]
            a=(xy(x1,scale_x),xy(y1,scale_y)); b=(xy(x2,scale_x),xy(y2,scale_y))
            draw.line((a,b), fill=stroke, width=sw)
            if typ == "arrow":
                import math
                ang=math.atan2(b[1]-a[1], b[0]-a[0]); length=18*((scale_x+scale_y)/2)
                left=(b[0]-length*math.cos(ang-.48), b[1]-length*math.sin(ang-.48))
                right=(b[0]-length*math.cos(ang+.48), b[1]-length*math.sin(ang+.48))
                draw.polygon([b,left,right], fill=stroke)
        elif typ in ("rect", "rounded_rect"):
            x,y,w,h=[float(sh.get(k,0) or 0) for k in ("x","y","width","height")]
            box=(xy(x,scale_x),xy(y,scale_y),xy(x+w,scale_x),xy(y+h,scale_y))
            if typ == "rounded_rect": draw.rounded_rectangle(box, radius=int(14*scale_x), fill=fill, outline=stroke, width=sw)
            else: draw.rectangle(box, fill=fill, outline=stroke, width=sw)
            label_text(sh.get("label",""), (box[0]+box[2])//2, (box[1]+box[3])//2-14*scale_y, font(24))
        elif typ in ("circle", "point", "ellipse"):
            cx=float(sh.get("cx",0) or 0); cy=float(sh.get("cy",0) or 0)
            rx=float(sh.get("rx",sh.get("r",8)) or 8); ry=float(sh.get("ry",rx) or rx)
            box=(xy(cx-rx,scale_x),xy(cy-ry,scale_y),xy(cx+rx,scale_x),xy(cy+ry,scale_y))
            draw.ellipse(box, fill=fill, outline=stroke, width=sw)
            label_text(sh.get("label",""), xy(cx,scale_x), xy(cy+ry+25,scale_y), font(22))
        elif typ in ("triangle", "polygon"):
            pts=sh.get("points",[])
            points=[(xy(pt[0],scale_x),xy(pt[1],scale_y)) for pt in pts[:30] if isinstance(pt,(list,tuple)) and len(pt)>=2]
            if len(points)>=3: draw.polygon(points, fill=fill, outline=stroke)
            if sh.get("label") and points: label_text(sh["label"],points[0][0]+30,points[0][1]+30,font(22))
        elif typ == "spline":
            pts=sh.get("points",[])
            points=[(xy(pt[0],scale_x),xy(pt[1],scale_y)) for pt in pts[:30] if isinstance(pt,(list,tuple)) and len(pt)>=2]
            if len(points)>=2: draw.line(points, fill=stroke, width=sw, joint="curve")
        elif typ == "text":
            x,y=xy(sh.get("x",0),scale_x),xy(sh.get("y",0),scale_y)
            draw.text((x,y),str(sh.get("text","")),font=font(sh.get("fontSize",22)),fill=color(sh.get("fill"),"#172033"))

    buf=io.BytesIO(); img.save(buf, format="PNG", optimize=True); return buf.getvalue()


def add_visual(slide, visual, x,y,w,h):
    """Embed the generated vector illustration as a PNG using Pillow only."""
    if not visual:
        return False
    visual = normalize_visual(visual)
    try:
        png = render_visual_png(visual)
        if not png.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError("Image renderer did not produce a valid PNG image.")
        slide.shapes.add_picture(io.BytesIO(png), Inches(x), Inches(y), width=Inches(w), height=Inches(h))
        return True
    except Exception as exc:
        raise RuntimeError(f"Could not embed SVG illustration in PowerPoint: {exc}") from exc

def add_bullets(slide, bullets, x,y,w,h, color, size=18):
    box=slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf=box.text_frame; tf.clear(); tf.word_wrap=True
    tf.margin_left=Inches(.08); tf.margin_right=Inches(.04)
    for i,b in enumerate((bullets or [])[:6]):
        p=tf.paragraphs[0] if i==0 else tf.add_paragraph()
        p.text="•  "+str(b); p.space_after=Pt(12)
        for run in p.runs:
            run.font.name="Aptos"; run.font.size=Pt(size); run.font.color.rgb=color
    return box

def draw_slide(prs, item, theme, template, visual, index, total):
    s=prs.slides.add_slide(prs.slide_layouts[6])
    bg=rgb(theme["bg"]); surface=rgb(theme["surface"]); primary=rgb(theme["primary"]); accent=rgb(theme["accent"]); fg=rgb(theme["text"]); muted=rgb(theme["muted"])
    s.background.fill.solid(); s.background.fill.fore_color.rgb=bg
    # top accent + footer
    bar=s.shapes.add_shape(MSO_SHAPE.RECTANGLE,0,0,prs.slide_width, Inches(.09)); bar.fill.solid(); bar.fill.fore_color.rgb=primary; bar.line.fill.background()
    title=str(item.get("title","Untitled slide"))
    subtitle=str(item.get("subtitle",""))
    bullets=item.get("bullets") or []
    add_text(s,title,.62,.42,12.0,.72,fg,28,True)
    if subtitle: add_text(s,subtitle,.66,1.16,11.9,.42,muted,13)
    has_visual=bool(visual)
    # template-driven composition
    if template=="image_only":
        if has_visual: add_visual(s,visual,.75,1.45,11.85,5.45)
        else: add_text(s,"Image not generated — use Generate / regenerate SVG visual",1.0,3.0,11.0,.6,muted,18,align=PP_ALIGN.CENTER)
    elif template=="text_only":
        add_bullets(s,bullets,.9,1.65,11.5,5.1,fg,20)
    elif template in ("text_image_left","image_left","text_image_right","image_right"):
        image_left=template in ("text_image_left","image_left")
        vx=0.65 if image_left else 7.0
        tx=6.5 if image_left else .75
        if has_visual: add_visual(s,visual,vx,1.65,5.8,4.8)
        else: add_text(s,"Image pending — generate the SVG visual",vx,3.0,5.8,.5,muted,14,align=PP_ALIGN.CENTER)
        add_bullets(s,bullets,tx,1.85,5.7,4.4,fg,18)
    elif template=="text_image_top":
        if has_visual: add_visual(s,visual,2.0,1.45,9.3,3.35)
        else: add_text(s,"Image pending — generate the SVG visual",2.0,2.6,9.3,.5,muted,14,align=PP_ALIGN.CENTER)
        add_bullets(s,bullets,.9,5.0,11.5,1.45,fg,14)
    elif template=="title_hero":
        add_text(s,subtitle or "A clear, visual overview",.8,2.05,5.2,.8,primary,24,True)
        add_bullets(s,bullets,.85,3.0,5.4,2.5,fg,17)
        if has_visual: add_visual(s,visual,6.5,1.65,6.1,4.9)
    elif template=="section":
        add_text(s,subtitle or "A new chapter",.9,2.3,11.4,.7,primary,30,True,align=PP_ALIGN.CENTER)
        add_bullets(s,bullets,2.0,3.5,9.3,1.7,fg,18)
    elif template=="quote":
        quote=(bullets[0] if bullets else subtitle or title)
        add_text(s,"“"+str(quote)+"”",1.0,2.0,11.3,2.0,primary,30,True,align=PP_ALIGN.CENTER)
        add_text(s,bullets[1] if len(bullets)>1 else "",2.0,4.5,9.3,.5,muted,16,align=PP_ALIGN.CENTER)
        if has_visual: add_visual(s,visual,9.7,5.0,2.3,1.4)
    elif template in ("two_column","problem_solution","comparison","case_study"):
        labels=["Context","Action","Result"] if template=="case_study" else (["Problem","Solution"] if template=="problem_solution" else ["Perspective 1","Perspective 2"])
        cols=3 if template=="case_study" else 2
        chunk=max(1,math.ceil(len(bullets)/cols))
        for c in range(cols):
            x=.7+c*(4.15 if cols==3 else 6.05); w=3.8 if cols==3 else 5.65
            sh=s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(1.8), Inches(w), Inches(4.65))
            sh.fill.solid(); sh.fill.fore_color.rgb=surface; sh.line.color.rgb=primary
            add_text(s,labels[c],x+.2,2.0,w-.4,.45,accent,17,True)
            add_bullets(s,bullets[c*chunk:(c+1)*chunk],x+.2,2.7,w-.4,3.4,fg,16)
    elif template in ("three_column","kpi_cards"):
        for c in range(3):
            x=.72+c*4.2; w=3.85
            sh=s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(2.0), Inches(w), Inches(3.8))
            sh.fill.solid(); sh.fill.fore_color.rgb=surface; sh.line.color.rgb=primary
            text=bullets[c] if c<len(bullets) else "Key point"
            add_text(s,f"{c+1:02d}",x+.22,2.25,w-.44,.6,accent,26,True)
            add_text(s,text,x+.22,3.1,w-.44,2.2,fg,18,True)
    elif template=="agenda":
        for i,b in enumerate(bullets[:6]):
            y=1.75+i*.72
            add_text(s,f"{i+1:02d}",.9,y,.75,.48,primary,21,True)
            add_text(s,b,1.9,y,10.3,.48,fg,19)
    elif template in ("timeline","process"):
        count=max(1,min(6,len(bullets)))
        y=3.15
        line=s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(1.15), Inches(y+.15), Inches(10.9), Inches(.05))
        line.fill.solid(); line.fill.fore_color.rgb=primary; line.line.fill.background()
        for i,b in enumerate(bullets[:count]):
            x=1.0+i*(10.9/max(1,count-1))
            dot=s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y-.08), Inches(.48), Inches(.48))
            dot.fill.solid(); dot.fill.fore_color.rgb=accent; dot.line.color.rgb=primary
            add_text(s,str(i+1),x,y+.55,1.0,.35,primary,14,True)
            add_text(s,b,x-.35,y+1.0,1.8,1.35,fg,13,align=PP_ALIGN.CENTER)
    elif template=="swot":
        for i,label in enumerate(["Strengths","Weaknesses","Opportunities","Threats"]):
            x=.8+(i%2)*6.0; y=1.75+(i//2)*2.35
            sh=s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(5.55), Inches(2.05))
            sh.fill.solid(); sh.fill.fore_color.rgb=surface; sh.line.color.rgb=primary
            add_text(s,label,x+.2,y+.12,5.1,.35,accent,16,True)
            add_bullets(s,bullets[i:i+1],x+.2,y+.65,5.1,1.1,fg,14)
    elif template=="pyramid":
        for i in range(3):
            width=4.2+i*2.0; x=(13.33-width)/2; y=1.8+i*1.35
            sh=s.shapes.add_shape(MSO_SHAPE.TRAPEZOID, Inches(x), Inches(y), Inches(width), Inches(1.15))
            sh.fill.solid(); sh.fill.fore_color.rgb=[primary,accent,surface][i]; sh.line.color.rgb=bg
            add_text(s,bullets[i] if i<len(bullets) else f"Level {i+1}",x+.2,y+.28,width-.4,.5,fg,15,True,align=PP_ALIGN.CENTER)
    elif template=="architecture":
        count=max(1,min(5,len(bullets)))
        for i,b in enumerate(bullets[:count]):
            x=.7+i*(11.9/count); w=11.0/count-.2
            sh=s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(2.5), Inches(w), Inches(1.45))
            sh.fill.solid(); sh.fill.fore_color.rgb=surface; sh.line.color.rgb=primary
            add_text(s,b,x+.08,2.8,w-.16,.8,fg,14,True,align=PP_ALIGN.CENTER)
            if i<count-1:
                add_text(s,"→",x+w,2.9,.35,.4,accent,22,True)
        if has_visual: add_visual(s,visual,3.6,4.35,6.1,1.8)
    elif template=="data_chart":
        vals=[]
        for i,b in enumerate(bullets[:6]):
            val=50+((len(str(b))*7+i*13)%45); vals.append((b,val))
        for i,(label,val) in enumerate(vals):
            x=1.0+i*1.85; h=val/100*3.3
            sh=s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(5.2-h), Inches(1.05), Inches(h))
            sh.fill.solid(); sh.fill.fore_color.rgb=primary if i%2==0 else accent; sh.line.fill.background()
            add_text(s,label[:22],x-.25,5.35,1.55,.85,fg,10,align=PP_ALIGN.CENTER)
        add_text(s,"Illustrative visual scale — not measured data",1.0,6.25,11,.3,muted,9)
    elif template=="summary":
        add_bullets(s,bullets,.9,1.8,11.6,4.8,fg,21)
    elif template=="closing":
        add_text(s,subtitle or "Questions & discussion",1.0,2.15,11.3,1.0,primary,32,True,align=PP_ALIGN.CENTER)
        add_bullets(s,bullets,2.0,3.6,9.3,1.8,fg,18)
    else:
        add_bullets(s,bullets,.8,1.8,5.8,4.8,fg,18)
        if has_visual: add_visual(s,visual,6.8,1.8,5.8,4.8)
    # small illustration for layouts without dedicated image placement, if supplied and not already used
    if has_visual and template not in ("title_hero","image_only","text_image_left","text_image_right","text_image_top","image_left","image_right","architecture","quote") and len(bullets)<=2:
        add_visual(s,visual,8.3,4.3,4.2,2.0)
    add_text(s,f"{index+1:02d}  /  {total:02d}",11.65,7.12,1.0,.2,muted,8,align=PP_ALIGN.RIGHT)
    if item.get("speaker_notes"):
        try: s.notes_slide.notes_text_frame.text=str(item["speaker_notes"])
        except Exception: pass
    return s

@app.post("/api/export-pptx")
def export_pptx():
    body=request.get_json(silent=True) or {}
    slides=body.get("slides")
    if not isinstance(slides,list) or not slides: return jsonify({"error":"No slides to export."}),400
    theme=THEMES.get(str(body.get("theme","midnight_blue")),THEMES["midnight_blue"])
    default_template=str(body.get("template","title_hero"))
    prs=Presentation(); prs.slide_width= Inches(13.333); prs.slide_height= Inches(7.5)
    visual_count = 0
    for i,item in enumerate(slides):
        if not isinstance(item,dict): continue
        template=str(item.get("template") or default_template)
        if template not in {t["id"] for t in TEMPLATES}: template=default_template
        visual=item.get("visual")
        if visual and not isinstance(visual, dict):
            return jsonify({"error":f"Slide {i+1} has invalid visual data. Regenerate its SVG illustration."}),400
        try:
            draw_slide(prs,item,theme,template,visual,i,len(slides))
            # Count embedded picture shapes, rather than trusting a visual flag.
            slide = prs.slides[-1]
            visual_count += sum(1 for shape in slide.shapes if shape.shape_type == 13)
        except Exception as exc:
            return jsonify({"error":f"Slide {i+1} export failed: {exc}"}),500
    name=re.sub(r"[^A-Za-z0-9_-]+","_",str(body.get("presentation_title","presentation")))[:60] or "presentation"
    path=EXPORT_DIR/f"{name}.pptx"
    prs.save(path)
    response = send_file(path,as_attachment=True,download_name=f"{name}.pptx",mimetype="application/vnd.openxmlformats-officedocument.presentationml.presentation")
    response.headers["X-Embedded-Visuals"] = str(visual_count)
    return response

@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api/"): return jsonify({"error":"API endpoint not found"}),404
    return e

@app.errorhandler(500)
def server_error(e):
    if request.path.startswith("/api/"): return jsonify({"error":"Internal server error"}),500
    return e

if __name__=="__main__":
    app.run(host="127.0.0.1",port=int(os.getenv("PORT","8100")),debug=True)
