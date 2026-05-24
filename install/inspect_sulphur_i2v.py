import json
from pathlib import Path

import sys
name = sys.argv[1] if len(sys.argv) > 1 else "Sulphur_I2V_图生视频.json"
p = Path(__file__).resolve().parents[1] / "workflows/测试" / name
d = json.loads(p.read_text(encoding="utf-8"))
for n in d["nodes"]:
    t = n.get("type", "")
    if "LTX2" in t or t == "LoadImage":
        line = f"{n['id']}\t{t}\t{n.get('title','')}\t{n.get('widgets_values')}"
        print(line.encode("unicode_escape").decode())