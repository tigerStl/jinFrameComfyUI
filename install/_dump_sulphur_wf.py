import json
from pathlib import Path
p = Path(__file__).resolve().parents[1] / "workflows/测试/Sulphur_I2V_图生视频.json"
d = json.loads(p.read_text(encoding="utf-8"))
out = []
for n in d["nodes"]:
    t = n.get("type", "")
    if "LTX2" in t or t == "LoadImage":
        out.append(f"{n['id']}\t{t}\t{n.get('title', '')}\t{n.get('widgets_values')}")
(p.parents[1] / "workflows/测试/_params.txt").write_text("\n".join(out), encoding="utf-8")
