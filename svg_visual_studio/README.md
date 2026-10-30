# SVG Visual Studio

Flask + Ollama app for cartoon storyboards and SVG diagrams.

## Modes
- Story mode: 2, 4, 6 or 8 cartoon panels
- Diagram mode: flowchart, exploded pie chart, bar chart, Venn diagram, and shape-based explainers (lines, arrows, points, rectangles, circles, ellipses, triangles, polygons, splines, paths and text)

## Windows setup
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
ollama pull qwen2.5:14b
python app.py
```
Open http://127.0.0.1:8000.

The frontend sends story and diagram requests to `/api/generate`. The backend also retains `/api/generate-diagram` as a compatible alias. API errors return JSON rather than Flask HTML error pages.
