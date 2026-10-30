from __future__ import annotations
import json, os, re
from typing import Any
import requests
from flask import Flask, jsonify, render_template, request
from dotenv import load_dotenv

load_dotenv()
app = Flask(__name__)
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'gemma4:cloud')

SYSTEM_PROMPT = '''You create concise comic storyboards for an SVG drawing tool. Return ONLY valid JSON, no markdown.
Schema: {"title":"short title","panels":[{"caption":"short caption","setting":"simple place","characters":[{"name":"A","pose":"thinking|talking|standing|walking|surprised","thought":"optional short thought","speech":"optional short spoken line","x":0.35,"y":0.62}],"action":"one sentence visual action"}]}
Rules: create exactly the requested number of panels. Use 1-3 characters per panel. Reuse the SAME character names throughout the story so each person keeps the same cartoon appearance in every panel. Give each person a distinct, realistic first name (avoid A/B labels). x and y are normalized from 0 to 1 and should keep characters inside the panel. Thought is for a thought cloud; speech is for a discussion bubble. Keep text short and family-friendly. Use a coherent beginning, middle and ending.''' 


def fallback_story(prompt: str, count: int) -> dict[str, Any]:
    beats = [
        ('An idea appears', 'A character pauses and thinks.', 'thinking'),
        ('They share the idea', 'A second character listens.', 'talking'),
        ('They explore options', 'The characters discuss a plan.', 'talking'),
        ('A small problem', 'They notice something unexpected.', 'surprised'),
        ('They work together', 'Both characters try the plan.', 'walking'),
        ('Progress', 'The plan begins to work.', 'standing'),
        ('A final adjustment', 'They improve their solution.', 'thinking'),
        ('Success', 'The characters celebrate the result.', 'standing'),
    ]
    panels = []
    for i in range(count):
        caption, action, pose = beats[i % len(beats)]
        panels.append({
            'caption': caption,
            'setting': 'simple comic scene',
            'characters': [
                {'name': 'A', 'pose': pose, 'thought': 'Could this work?' if pose == 'thinking' else '',
                 'speech': 'Let us try it.' if pose == 'talking' else '', 'x': 0.32, 'y': 0.68},
                {'name': 'B', 'pose': 'talking' if i % 2 else 'standing', 'thought': '',
                 'speech': 'I can help!' if i % 2 else '', 'x': 0.70, 'y': 0.68}
            ],
            'action': f'{action} Story idea: {prompt[:120]}'
        })
    return {'title': 'A Little Comic', 'panels': panels}



DIAGRAM_PROMPTS = {
    "flowchart": '''Create a flowchart. Return JSON only: {"title":"...","nodes":[{"id":"a","label":"Start","type":"start"},{"id":"b","label":"Process","type":"process"},{"id":"c","label":"Decision?","type":"decision"},{"id":"d","label":"End","type":"end"}],"edges":[{"from":"a","to":"b","label":""},{"from":"b","to":"c","label":""},{"from":"c","to":"d","label":"Yes"}]}. Use 4-9 nodes. Types: start, process, decision, end. Use valid IDs and edges.''',
    "pie": '''Create an exploded pie chart. Return JSON only: {"title":"...","segments":[{"label":"Category A","value":40,"color":"#5577bb"},{"label":"Category B","value":30,"color":"#e58b55"},{"label":"Category C","value":20,"color":"#55a58b"},{"label":"Category D","value":10,"color":"#a47ac4"}]}. Use 3-7 positive values and distinct colors.''',
    "bar": '''Create a bar chart. Return JSON only: {"title":"...","xLabel":"Category","yLabel":"Value","items":[{"label":"A","value":12},{"label":"B","value":20},{"label":"C","value":15},{"label":"D","value":28}]}. Use 3-8 categories and nonnegative numeric values.''',
    "shapes": """Create an educational topic illustration using SVG primitives. Return JSON only with schema {"title":"...","description":"...","shapes":[{"type":"rounded_rect","x":80,"y":100,"width":220,"height":100,"fill":"#dceeff","stroke":"#315b8a","label":"Main concept"},{"type":"circle","cx":450,"cy":150,"r":55,"fill":"#fce3b2","label":"Related idea"},{"type":"arrow","x1":300,"y1":150,"x2":395,"y2":150,"stroke":"#333333","strokeWidth":3},{"type":"spline","points":[[100,300],[250,250],[400,350],[600,280]],"stroke":"#8b5cf6","strokeWidth":4},{"type":"text","x":100,"y":500,"text":"Explanation","fontSize":20}]}. Canvas 1000x650. Supported types: line, arrow, point, rect, rounded_rect, circle, ellipse, triangle, polygon, spline, path, text. Use 6-18 shapes, valid hex colors, concise labels, meaningful positions. Use polygon points for triangles and polygons. Use spline points for smooth curves. Explain the given topic visually, not as a generic decoration.""",
    "venn": '''Create a two- or three-set Venn diagram. Return JSON only: {"title":"...","sets":[{"label":"Set A","items":["Shared 1","A only"]},{"label":"Set B","items":["Shared 1","B only"]}]}. Use exactly 2 or 3 sets. Shared items must have identical text in each set.''',
    "story": '''Create an illustrated explainer story in exactly the requested number of panels. Return JSON only: {"title":"...","panels":[{"caption":"...","setting":"...","characters":[{"name":"Maya","pose":"thinking","thought":"...","speech":"","x":0.35,"y":0.65},{"name":"Arun","pose":"talking","thought":"","speech":"...","x":0.7,"y":0.65}],"action":"..."}]}. Use recurring named characters and coherent beginning, middle and ending.'''
}

def fallback_diagram(mode, prompt):
    if mode == "flowchart":
        return {"title":"Flowchart","nodes":[{"id":"n1","label":"Start","type":"start"},{"id":"n2","label":"Understand the problem","type":"process"},{"id":"n3","label":"Choose an approach?","type":"decision"},{"id":"n4","label":"Complete task","type":"process"},{"id":"n5","label":"End","type":"end"}],"edges":[{"from":"n1","to":"n2"},{"from":"n2","to":"n3"},{"from":"n3","to":"n4","label":"Yes"},{"from":"n4","to":"n5"}]}
    if mode == "pie":
        return {"title":"Exploded Pie Chart","segments":[{"label":"Category A","value":40,"color":"#5577bb"},{"label":"Category B","value":30,"color":"#e58b55"},{"label":"Category C","value":20,"color":"#55a58b"},{"label":"Category D","value":10,"color":"#a47ac4"}]}
    if mode == "bar":
        return {"title":"Bar Chart","xLabel":"Category","yLabel":"Value","items":[{"label":"A","value":12},{"label":"B","value":20},{"label":"C","value":15},{"label":"D","value":28}]}
    if mode == "shapes":
        return {"title": "Concept Explainer", "description": prompt, "shapes": [
            {"type":"rounded_rect","x":75,"y":120,"width":235,"height":115,"fill":"#dceeff","stroke":"#315b8a","strokeWidth":3,"label":"Core concept"},
            {"type":"circle","cx":500,"cy":175,"r":65,"fill":"#fce3b2","stroke":"#bd7a20","strokeWidth":3,"label":"Key idea"},
            {"type":"arrow","x1":310,"y1":175,"x2":425,"y2":175,"stroke":"#475569","strokeWidth":4},
            {"type":"triangle","points":[[710,100],[825,235],[595,235]],"fill":"#dff4e8","stroke":"#34805c","strokeWidth":3,"label":"Outcome"},
            {"type":"spline","points":[[130,360],[280,290],[440,405],[620,315],[840,400]],"stroke":"#8b5cf6","strokeWidth":5},
            {"type":"point","cx":130,"cy":360,"r":8,"fill":"#8b5cf6"},
            {"type":"point","cx":840,"cy":400,"r":8,"fill":"#8b5cf6"},
            {"type":"text","x":85,"y":520,"text":"A visual explanation built from SVG shapes","fontSize":23,"fill":"#263449"}
        ]}
    if mode == "venn":
        return {"title":"Venn Diagram","sets":[{"label":"Set A","items":["Shared idea","A only"]},{"label":"Set B","items":["Shared idea","B only"]}]}
    return fallback_story(prompt, 4)


def parse_json(text: str) -> dict[str, Any]:
    text = text.strip()
    text = re.sub(r'^```(?:json)?\s*|\s*```$', '', text, flags=re.I)
    start, end = text.find('{'), text.rfind('}')
    if start < 0 or end < start:
        raise ValueError('Ollama did not return a JSON object')
    return json.loads(text[start:end + 1])

@app.get('/')
def home():
    return render_template('index.html', model=OLLAMA_MODEL)

@app.get('/api/health')
def health():
    try:
        r = requests.get(f'{OLLAMA_URL.rstrip("/")}/api/tags', timeout=4)
        r.raise_for_status()
        names = [m.get('name', '') for m in r.json().get('models', [])]
        return jsonify({'ok': True, 'ollama_url': OLLAMA_URL, 'configured_model': OLLAMA_MODEL, 'models': names})
    except Exception as e:
        return jsonify({'ok': False, 'ollama_url': OLLAMA_URL, 'configured_model': OLLAMA_MODEL, 'error': str(e)}), 503

@app.post('/api/generate')
@app.post('/api/generate-diagram')
def generate():
    body = request.get_json(silent=True) or {}
    prompt = str(body.get('prompt', '')).strip()
    mode = str(body.get('mode') or body.get('diagram_type') or body.get('diagramType') or 'comic').lower()
    if mode == 'diagram':
        mode = str(body.get('diagram_type') or body.get('diagramType') or 'flowchart').lower()
    try:
        count = int(body.get('panels', 4))
    except (TypeError, ValueError):
        count = 4
    if not prompt:
        return jsonify({'error': 'Enter a prompt or describe the data.'}), 400
    if mode not in ('comic', 'story', 'flowchart', 'pie', 'bar', 'venn', 'shapes'):
        return jsonify({'error': 'Unsupported visual type.'}), 400
    if mode in ('comic', 'story') and count not in (2, 4, 6, 8):
        return jsonify({'error': 'Panel count must be 2, 4, 6, or 8.'}), 400

    if mode == 'comic':
        system_prompt = SYSTEM_PROMPT
        user_prompt = f'Create a comic based on: {prompt}. Exactly {count} panels. Return the requested JSON.'
    else:
        system_prompt = DIAGRAM_PROMPTS[mode]
        user_prompt = f'Create a {mode} visual based on: {prompt}. Story panel count if applicable: {count}. Return requested JSON only.'
    try:
        response = requests.post(
            f'{OLLAMA_URL.rstrip("/")}/api/chat',
            json={'model': OLLAMA_MODEL, 'stream': False, 'format': 'json',
                  'messages': [{'role': 'system', 'content': system_prompt}, {'role': 'user', 'content': user_prompt}],
                  'options': {'temperature': 0.4}}, timeout=180)
        response.raise_for_status()
        data = parse_json(response.json().get('message', {}).get('content', ''))
        if mode in ('comic', 'story'):
            panels = data.get('panels', [])
            if not isinstance(panels, list) or len(panels) != count:
                raise ValueError(f'Expected exactly {count} panels.')
            for panel in panels:
                panel.setdefault('caption', '')
                panel.setdefault('action', '')
                panel.setdefault('characters', [])
                if not isinstance(panel['characters'], list):
                    panel['characters'] = []
        elif mode == 'flowchart' and (not data.get('nodes') or not isinstance(data.get('edges'), list)):
            raise ValueError('Invalid flowchart data.')
        elif mode == 'pie' and not data.get('segments'):
            raise ValueError('Invalid pie chart data.')
        elif mode == 'bar' and not data.get('items'):
            raise ValueError('Invalid bar chart data.')
        elif mode == 'venn' and not data.get('sets'):
            raise ValueError('Invalid Venn diagram data.')
        elif mode == 'shapes' and (not isinstance(data.get('shapes'), list) or not data.get('shapes')):
            raise ValueError('Invalid shape illustration data.')
        data.update({'mode': mode, 'model': OLLAMA_MODEL, 'source': 'ollama'})
        return jsonify(data)
    except Exception as e:
        data = fallback_diagram(mode, prompt)
        data.update({'mode': mode, 'model': OLLAMA_MODEL, 'source': 'fallback',
                     'warning': f'Ollama generation failed: {e}. A sample visual was generated instead.'})
        return jsonify(data)


@app.errorhandler(404)
def api_not_found(error):
    if request.path.startswith('/api/'):
        return jsonify({'error': f'API endpoint not found: {request.path}'}), 404
    return error

@app.errorhandler(500)
def api_error_handler(error):
    if request.path.startswith('/api/'):
        app.logger.exception("Unhandled API error")
        return jsonify({'error': 'Internal server error. Check the Flask console for details.'}), 500
    return error

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=int(os.getenv('PORT', '8000')), debug=True)
