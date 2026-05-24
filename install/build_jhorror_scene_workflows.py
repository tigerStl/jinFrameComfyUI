"""Generate per-scene SDXL/Flux T2I workflow JSON files."""
import copy
import json
import shutil
import sys
import uuid
from pathlib import Path

_INST = Path(__file__).resolve().parent
sys.path.insert(0, str(_INST))
from repo_paths import REPO_WF, COMFY_WF  # noqa: E402

ROOT = REPO_WF / "日系惊悚_场景"
COMFY_ROOT = COMFY_WF / "日系惊悚_场景"
SDXL_SRC = ROOT / "SDXL_T2I_日系惊悚_场景.json"
FLUX_SRC = ROOT / "Flux_T2I_日系惊悚_场景.json"
HUNYUAN_SRC = REPO_WF / "HunyuanDiT_T2I_中国风格.json"

SCENES = [
    {
        "slug": "大厅走廊",
        "landscape": True,
        "chinese": False,
        "sdxl_scene": "modern office building or apartment corridor at night, long one-point perspective, closed doors, green EXIT sign glow, polished floor with faint reflection, ceiling strip lights, eerie silence, mundane dread.",
        "flux_scene": "long office or apartment corridor at night, symmetrical perspective, rows of doors, dim EXIT sign, glossy floor reflection, ceiling light strips, oppressive quiet.",
        "hunyuan_scene": (
            "深夜长长的室内走廊，办公或公寓一侧，强烈一点透视，一排紧闭房门，"
            "墙上绿色安全出口指示灯，抛光地面微弱反光，天花板条状灯带，空无一人。"
        ),
    },
    {
        "slug": "办公大楼大厅走廊",
        "landscape": True,
        "chinese": False,
        "sdxl_scene": (
            "contemporary modern corporate office tower lobby and corridor, after hours, very dark low-key lighting, underexposed, "
            "dominant sickly green-cyan fluorescent color cast on walls floor and glass, glowing green EXIT sign as main accent light, "
            "emerald spill on polished marble, deep shadows in ceiling corners and far end of corridor, cold desaturated palette, "
            "sleek glass and metal, minimalist reception in darkness, strong one-point perspective, empty silence, "
            "NOT warm yellow light, NOT golden tones, NOT bright white lobby, NOT orange tungsten, NOT daylight, NOT high key, "
            "NOT old building, NOT vintage, NOT residential apartment, no people."
        ),
        "sdxl_neg_extra": (
            "warm yellow lighting, golden hour, amber cast, orange tungsten, bright lobby, overexposed, high key, "
            "sunny daylight, beige interior, cheerful, well lit"
        ),
        "flux_scene": (
            "dark modern office tower lobby and corridor, low-key underexposed, sickly green-cyan fluorescent cast, "
            "green EXIT sign glow on stone floor, deep shadows, cold emerald tint, glass and metal, empty night, "
            "NOT warm yellow NOT bright lobby NOT golden, no people."
        ),
        "hunyuan_scene": (
            "现代化办公大楼大堂与走廊，深夜极低照度，阴暗压抑，惨绿色荧光灯笼罩墙面与地面，"
            "绿色安全出口指示牌为主要光源，走廊深处浓重阴影，冷色低饱和偏绿，大理石弱反光，"
            "不要暖黄色灯光，不要明亮金黄大堂，不要日光，无人。"
        ),
    },
    {
        "slug": "ArtDeco_经典大堂",
        "landscape": True,
        "chinese": False,
        "sdxl_scene": (
            "Rockefeller Center style grand commercial lobby interior, 1930s Art Deco New York skyscraper, "
            "monumental scale, double-height or very high ceiling, geometric Art Deco ceiling relief and brass trim, "
            "polished marble floor with large reflections, travertine or limestone walls, ornate metal elevator doors, "
            "symmetrical grand hall opening to corridor wings, warm brass accent lights mixed with cool downlights, "
            "luxurious historic landmark office building, well maintained NOT decayed, after hours empty, "
            "NOT minimalist modern office, NOT 2020s glass startup lobby, NOT apartment corridor, no people."
        ),
        "flux_scene": (
            "Rockefeller Center type Art Deco skyscraper lobby, 1930s NYC landmark interior, grand monumental hall, "
            "marble floor reflections, brass and stone, geometric deco ceiling, ornate elevator banks, "
            "symmetrical perspective, historic luxury commercial building, empty night, NOT sleek modern LED office, no people."
        ),
        "hunyuan_scene": (
            "洛克菲勒中心风格的装饰艺术摩天楼大堂，1930年代纽约地标写字楼室内，"
            "宏伟尺度，大理石地面强烈反光，黄铜与石材装饰，几何浮雕天花板，"
            "对称华丽的电梯厅，历史地标建筑保养良好，深夜空无人，"
            "不要现代极简玻璃办公室，不要破旧老公寓走廊。"
        ),
    },
    {
        "slug": "办公室",
        "landscape": True,
        "chinese": False,
        "sdxl_scene": "after-hours Japanese corporate office, empty cubicles, dark monitors, glass partition walls, cold fluorescent ceiling panels, lone rolling chair, stacks of folders, psychological dread, late night overtime atmosphere, no people.",
        "flux_scene": "empty Japanese office after midnight, cubicles, dark PC screens, fluorescent tubes, rolling chair, glass meeting room, psychological tension, no people.",
        "hunyuan_scene": (
            "深夜空置的开放式办公室，格子间与暗掉的显示器，玻璃隔断会议室，"
            "冷色荧光灯面板，孤独转椅与堆叠文件夹，加班后心理压迫感，无人。"
        ),
    },
    {
        "slug": "卧室",
        "landscape": False,
        "chinese": False,
        "sdxl_scene": "small Japanese apartment bedroom at 3am, unmade futon or single bed, thin curtain, wardrobe shadow in corner, view from doorway, dim street light through window, claustrophobic quiet, uncanny stillness, no people.",
        "flux_scene": "cramped bedroom at night, messy bed, curtain gap, wardrobe corner shadow, view from door crack, 3am insomnia mood, no people.",
        "hunyuan_scene": (
            "凌晨三点狭小的出租屋卧室，凌乱床铺，从门缝向内看的构图，"
            "窗帘缝隙路灯光，衣柜角落深重阴影，幽闭安静，诡异静止，无人。"
        ),
    },
    {
        "slug": "电梯",
        "landscape": False,
        "chinese": False,
        "sdxl_scene": "elevator interior, stainless steel walls, closed doors, floor indicator panel, harsh ceiling light, faint mirror reflection, cramped liminal space, uncanny waiting stillness, no people, no gore.",
        "flux_scene": "elevator cabin, steel panels, floor indicator, mirror reflection, harsh ceiling lamp, doors shut, claustrophobic, empty, no people.",
        "hunyuan_scene": (
            "电梯轿厢内部，不锈钢壁板，紧闭门，楼层指示灯，顶灯刺眼，"
            "镜面微弱倒影，狭窄边缘空间，诡异等待般的静止，空无一人。"
        ),
    },
    {
        "slug": "带电梯走廊",
        "landscape": True,
        "chinese": False,
        "sdxl_scene": (
            "long modern office or apartment building corridor at night, elevator bank along one wall, "
            "multiple closed stainless elevator doors, call buttons and floor indicator panels with dim glow, "
            "green EXIT sign, polished floor reflecting sickly green-cyan fluorescent light, "
            "very dark low-key underexposed, deep shadows toward corridor vanishing point, one-point perspective, "
            "after hours empty, liminal psychological dread, "
            "NOT inside elevator cabin, NOT warm yellow light, NOT bright lobby, NOT golden tones, no people."
        ),
        "sdxl_neg_extra": (
            "warm yellow lighting, golden hour, bright corridor, overexposed, high key, sunny, "
            "elevator interior cabin view, open elevator doors showing shaft"
        ),
        "flux_scene": (
            "dark corridor with elevator doors on side wall, closed metal elevators, floor indicators, "
            "green EXIT sign, green-cyan fluorescent cast, glossy floor, deep perspective, empty night, "
            "NOT elevator interior, NOT warm yellow, no people."
        ),
        "hunyuan_scene": (
            "深夜狭长室内走廊，一侧墙面成排电梯门与呼梯面板，金属门紧闭，"
            "楼层指示灯微亮，绿色安全出口标志，地面映出惨绿荧光，"
            "阴暗低照度、一点透视、远处浓重阴影，空无一人，"
            "不要轿厢内部视角，不要暖黄明亮灯光。"
        ),
    },
]

HUNYUAN_COMMON = (
    "日系心理惊悚电影空镜，写实摄影静帧，低饱和冷色调，病态荧光灯与深阴影，"
    "非血腥恐怖，无鲜血尸体，画面无人。\n"
    "{scene}\n"
    "高清摄影，电影感构图，轻微胶片颗粒，无文字无水印，非动漫非插画非卡通。"
)

HUNYUAN_NEG = (
    "丑陋，变形，低质量，模糊，水印，文字，血腥，尸体，怪物，动漫，插画，卡通，"
    "二次元，过饱和，鲜艳色彩，欢快，热闹人群，裸露"
)

SDXL_COMMON = (
    "RAW photo, masterpiece, best quality, cinematic still, Japanese psychological horror (J-horror), NOT gory, no blood.\n"
    "Muted desaturated colors, sickly fluorescent light, deep shadows, subtle film grain, 35mm, liminal uncanny mood, empty space, no people in frame.\n"
    "{scene}\n"
    "Kiyoshi Kurosawa / Nakata Hideo tone, high detail, no text watermark."
)
FLUX_COMMON = (
    "RAW photograph, photorealistic, live-action, NOT anime, NOT cartoon, NOT illustration, NOT CGI.\n"
    "Cinematic photograph, Japanese psychological horror (J-horror), NOT gory slasher, no blood.\n"
    "Muted desaturated palette, sickly fluorescent mixed with deep shadow, subtle 35mm grain, shallow depth of field, liminal uncanny atmosphere, empty scene without people.\n"
    "{scene}\n"
    "Hyperreal architecture, documentary realism, no watermark, no text."
)

# FLUX KSampler CFG=1 时负向几乎无效 → 写实/反动画必须写在正向，并保留英文锚词（T5 对英文摄影词更稳）
PHOTO_LOCK_CN = (
    "RAW photograph, photorealistic, live-action, real-world location, 8k uhd, dslr.\n"
    "写实摄影照片，真实场景实拍，真人电影实拍静帧，NOT anime NOT cartoon NOT illustration NOT CGI NOT 3d render NOT game screenshot.\n"
    "非动漫，非插画，非卡通，非二次元，非赛璐璐，非三渲二，非游戏画面，非手绘，非漫画背景。"
)

SDXL_COMMON_CN = (
    f"{PHOTO_LOCK_CN}\n"
    "Japanese psychological horror live-action film still (J-horror), NOT gory, no blood.\n"
    "低饱和冷色调，惨白日光灯与深阴影，轻微胶片颗粒，35mm，边缘空间不安感，画面中空无一人。\n"
    "{scene}\n"
    "Kiyoshi Kurosawa cinematic realism, hyperreal architecture and materials, no text, no watermark."
)

FLUX_COMMON_CN = (
    f"{PHOTO_LOCK_CN}\n"
    "Japanese psychological horror live-action film still (J-horror), NOT gory, no blood.\n"
    "低饱和配色，病态荧光灯与深阴影，轻微35mm颗粒，浅景深，诡异空旷氛围，空镜无人。\n"
    "{scene}\n"
    "Hyperreal architectural photography, documentary realism, no watermark, no text."
)

NEG_CN = (
    "anime, cartoon, illustration, cel shading, 3d render, cgi, game art, digital painting, comic, manga style, "
    "chibi, stylized, vibrant saturated, gore, blood, monster, zombie, bright daylight, crowded, cheerful, "
    "low quality, blurry, text, watermark, people, face, corpse, "
    "动漫, 插画, 卡通, 二次元, 赛璐璐, 三渲二, 游戏CG, 手绘, 漫画风, 过饱和, 鲜艳色彩"
)


def _sdxl_prompt(scene: dict) -> str:
    tpl = SDXL_COMMON_CN if scene.get("chinese") else SDXL_COMMON
    return tpl.format(scene=scene["sdxl_scene"])


def _flux_prompt(scene: dict) -> str:
    tpl = FLUX_COMMON_CN if scene.get("chinese") else FLUX_COMMON
    return tpl.format(scene=scene["flux_scene"])


def _hunyuan_prompt(scene: dict) -> str:
    return HUNYUAN_COMMON.format(scene=scene["hunyuan_scene"])


def patch_hunyuan(data: dict, scene: dict) -> dict:
    d = copy.deepcopy(data)
    d["id"] = str(uuid.uuid4())
    w, h = (1024, 768) if scene["landscape"] else (768, 1024)
    for n in d["nodes"]:
        if n["id"] == 2:
            n["title"] = f"正向 · {scene['slug']}（中文）"
            n["widgets_values"] = [_hunyuan_prompt(scene)]
        elif n["id"] == 3:
            n["title"] = "负向（中文）"
            n["widgets_values"] = [HUNYUAN_NEG]
        elif n["id"] == 4:
            n["title"] = f"{'横' if scene['landscape'] else '竖'}构图 {w}x{h}"
            n["widgets_values"] = [w, h, 1]
        elif n["id"] == 7:
            n["widgets_values"] = [f"sample/hunyuan_jhorror_{scene['slug']}"]
    d["groups"][0]["title"] = f"Hunyuan DiT 1.2 · 日系惊悚 · {scene['slug']}"
    return d


def patch_sdxl(data: dict, scene: dict) -> dict:
    d = copy.deepcopy(data)
    d["id"] = str(uuid.uuid4())
    w, h = (1216, 832) if scene["landscape"] else (832, 1216)
    for n in d["nodes"]:
        if n["id"] == 3:
            n["title"] = f"正向 · {scene['slug']}" + ("（中文）" if scene.get("chinese") else "")
            n["widgets_values"] = [_sdxl_prompt(scene)]
        elif n["id"] == 4 and scene.get("chinese"):
            n["title"] = "负向（中文）"
            n["widgets_values"] = [NEG_CN]
        elif n["id"] == 4 and scene.get("sdxl_neg_extra"):
            base = (n.get("widgets_values") or [""])[0]
            n["widgets_values"] = [f"{base}, {scene['sdxl_neg_extra']}"]
        elif n["id"] == 5:
            n["title"] = f"{'横' if scene['landscape'] else '竖'}构图 {w}x{h}"
            n["widgets_values"] = [w, h, 1]
        elif n["id"] == 8:
            n["widgets_values"] = [f"sample/sdxl_jhorror_{scene['slug']}"]
    d["nodes"] = [x for x in d["nodes"] if x.get("id") != 10]
    d["groups"][0]["title"] = f"SDXL · 日系惊悚 · {scene['slug']}"
    return d


def patch_flux(data: dict, scene: dict) -> dict:
    d = copy.deepcopy(data)
    d["id"] = str(uuid.uuid4())
    w, h = (1344, 768) if scene["landscape"] else (768, 1344)
    for n in d["nodes"]:
        if n["id"] == 4:
            n["title"] = f"正向 · {scene['slug']}" + ("（中文）" if scene.get("chinese") else "")
            n["widgets_values"] = [_flux_prompt(scene)]
        elif n["id"] == 5 and scene.get("chinese"):
            n["title"] = "负向（中文）"
            n["widgets_values"] = [NEG_CN]
        elif n["id"] == 6:
            n["title"] = f"{'横' if scene['landscape'] else '竖'}构图 {w}x{h}"
            n["widgets_values"] = [w, h, 1]
        elif n["id"] == 9:
            n["widgets_values"] = [f"sample/flux_jhorror_{scene['slug']}"]
    d["nodes"] = [x for x in d["nodes"] if x.get("type") != "MarkdownNote"]
    d["groups"][0]["title"] = f"FLUX Dev · 日系惊悚 · {scene['slug']}"
    return d


def main() -> None:
    sdxl = json.loads(SDXL_SRC.read_text(encoding="utf-8"))
    flux = json.loads(FLUX_SRC.read_text(encoding="utf-8"))
    hunyuan = json.loads(HUNYUAN_SRC.read_text(encoding="utf-8"))

    tpl_hy = patch_hunyuan(hunyuan, SCENES[0])
    (ROOT / "HunyuanDiT_T2I_日系惊悚_场景.json").write_text(
        json.dumps(tpl_hy, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    for sc in SCENES:
        sdxl_out = ROOT / f"SDXL_T2I_惊悚_{sc['slug']}.json"
        flux_out = ROOT / f"Flux_T2I_惊悚_{sc['slug']}.json"
        hy_out = ROOT / f"HunyuanDiT_T2I_惊悚_{sc['slug']}.json"
        sdxl_out.write_text(
            json.dumps(patch_sdxl(sdxl, sc), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        flux_out.write_text(
            json.dumps(patch_flux(flux, sc), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        hy_out.write_text(
            json.dumps(patch_hunyuan(hunyuan, sc), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        if COMFY_ROOT.parent.exists():
            COMFY_ROOT.mkdir(parents=True, exist_ok=True)
            for p in (sdxl_out, flux_out, hy_out):
                shutil.copy(p, COMFY_ROOT / p.name)
        print("ok", sc["slug"].encode("unicode_escape").decode())


if __name__ == "__main__":
    main()
