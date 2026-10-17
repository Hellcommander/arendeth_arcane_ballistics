"""Arcane Ballistics animations (tools/build_fx.py): every ability gets its own FX built from core_2 particle templates with
neutral (tint-clean) tiles: electric bolts and impacts, frost crystals, holy sparkle, void glitch. Only the game's particle
atlas is used (filter = colour tint; value tweaks = timing, blast range, camera shake, sound).

    python tools/build_fx.py            writes animations/*.json and sets each ability's `animation`
"""
import copy
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORE = Path(os.environ.get("S2_CORE_ANIMATIONS") or ROOT.parent / "core_2" / "animations")
P = "arendeth_arcane_ballistics_"

def vanilla(stem):
    for f in CORE.iterdir():
        if f.stem == stem or f.stem.startswith(stem + "_"):
            return json.load(open(f, encoding="utf-8-sig"))
    raise FileNotFoundError(stem)

T = {k: vanilla(k) for k in ("3_Fireball", "4_Fireball_explosion", "61_Flame_nova", "65_Phaseshift", "Frost_armor", "15_Whirlwind")}

# neutral tile sets (tint cleanly): mapping of the 9 explosion-template ids -> new ids, per flavour
EXPL_SRC = [376, 377, 378, 379, 380, 381, 382, 383, 364]
FLAVOUR = {
    "sparkle": [65, 66, 67, 68, 69, 1343, 1344, 1345, 1346],
    "frost":   [553, 554, 555, 556, 557, 1344, 1345, 1346, 554],
    "smoke":   [545, 546, 547, 548, 549, 550, 551, 1344, 546],
    "lines":   [65, 66, 1297, 1298, 1299, 1300, 1301, 1302, 1343],
    "ring":    [743, 744, 745, 746, 745, 744, 743, 1344, 1345],
    "glitch":  [1386, 1387, 1388, 1389, 1390, 1391, 1387, 1344, 1345],
    "heal":    [65, 66, 67, 1193, 1194, 1195, 1196, 1197, 1344],
    "death":   [49, 50, 51, 52, 53, 1344, 1345, 1346, 1343],
}

def slug(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")

def tint(parts, rgb, alpha=None):
    for p in parts:
        rows = p.get("color") or [[255, 255, 255, 255]]
        new = []
        for row in rows:
            a = row[3] if len(row) > 3 else 255
            new.append([rgb[0], rgb[1], rgb[2], a if alpha is None else alpha])
        p["color"] = new

def remap(parts, mapping):
    for p in parts:
        p["tile_id"] = mapping.get(p.get("tile_id"), p.get("tile_id"))

def shake(a, power):
    a["camera_shake"] = {"bounces": 4 if power else 2, "duration": 0.25 if power else 0.0, "power": power, "type": 1}

def clamp_range(parts, r):
    for p in parts:
        if "explosion_range" in p:
            p["explosion_range"] = max(1, min(int(p["explosion_range"]), r))

def base(id_, name, tmpl, parts, sound=None, power=0, chain=None):
    a = {k: copy.deepcopy(v) for k, v in tmpl.items() if k != "particles"}
    a["id"] = P + id_
    a["name"] = name
    a["particles"] = parts
    if sound:
        a["sound"] = {"id": sound, "volume": 100}
    if chain is not None:
        a["chain_particles"] = chain
    shake(a, power)
    return a

def hit(id_, name, rgb, flavour, rng, power, sound="13"):
    parts = copy.deepcopy(T["4_Fireball_explosion"]["particles"])
    remap(parts, dict(zip(EXPL_SRC, FLAVOUR[flavour])))
    tint(parts, rgb)
    clamp_range(parts, rng + 1)
    return base(id_, name, T["4_Fireball_explosion"], parts, sound=sound, power=power, chain=False)

BOLT_MAP = dict(zip([390, 391, 392, 393, 394, 395, 396, 397, 398, 399], [65, 66, 67, 68, 69, 68, 67, 66, 65, 67]))
def bolt(id_, name, rgb, hit_id, small=False):
    parts = copy.deepcopy(T["3_Fireball"]["particles"])
    remap(parts, BOLT_MAP)
    tint(parts, rgb)
    parts[-1]["on_impact"] = P + hit_id          # the flying particle hands over to the impact
    if small:
        parts = parts[:3] + parts[-1:]
    return base(id_, name, T["3_Fireball"], parts, sound="10", power=0, chain=True)

def aura(id_, name, rgb):
    parts = copy.deepcopy(T["Frost_armor"]["particles"])
    remap(parts, dict(zip([928, 929, 930, 931, 932, 933, 934], [743, 744, 745, 746, 1343, 1344, 1345])))
    tint(parts, rgb)
    return base(id_, name, T["Frost_armor"], parts, sound="35", power=0, chain=True)

def conjure(id_, name, rgb):
    parts = [p for p in copy.deepcopy(T["65_Phaseshift"]["particles"]) if not p.get("on_impact")]
    remap(parts, dict(zip([523, 522, 520, 519, 518, 517, 516, 515, 514, 513, 524], [65, 66, 67, 68, 67, 66, 65, 1344, 1345, 1346, 1343])))
    tint(parts, rgb)
    return base(id_, name, T["65_Phaseshift"], parts, sound="62", power=0, chain=True)

def nova(id_, name, rgb, flavour="ring", big=False):
    parts = copy.deepcopy(T["61_Flame_nova"]["particles"])
    ids = {"ring": [743, 744, 745], "sparkle": [67, 68, 69], "lines": [1297, 1298, 1299]}[flavour]
    remap(parts, dict(zip([561, 562, 563], ids)))
    extra = copy.deepcopy(parts[-1]); extra["tile_id"] = 746 if flavour == "ring" else ids[-1]
    extra["delay"] = 150.0; extra["explosion_range"] = parts[-1]["explosion_range"] + 1
    parts.append(extra)
    if big:
        for p in parts: p["explosion_range"] += 1
    tint(parts, rgb)
    return base(id_, name, T["61_Flame_nova"], parts, sound="13", power=0, chain=False)

def whirl(id_, name, rgb):
    parts = copy.deepcopy(T["15_Whirlwind"]["particles"])
    remap(parts, {606: 752, 450: 753})
    tint(parts, rgb)
    return base(id_, name, T["15_Whirlwind"], parts, sound="20", power=0, chain=False)


# ---- the plan ---------------------------------------------------------------------------------------------------------------
def snd(stem):
    try:
        return str(vanilla(stem)["sound"]["id"])
    except Exception:
        return "13"
SOUND = {"elec": snd("7_Lightning"), "frost": snd("Freeze_AoE"), "holy": snd("Holy_strike"), "death": snd("Death_Aura")}

ELEC, ELEC2, FROST, HOLY, VOID, FLAME, GOLD, MORTAR = (130, 185, 255), (190, 220, 255), (170, 220, 255), (255, 235, 170), (160, 110, 230), (255, 170, 90), (255, 225, 150), (150, 195, 110)

# ability -> (kind, flavour, tint, camera power, element-for-sound, small)
#   kind: shot (bolt + impact) | burst (impact at the spot) | nova (rings) | summon (assembles) | aura (self)
PLAN = {
    "astral_arrow":                 ("shot",   "lines",   ELEC,   1, "elec", False),
    "arc_beam":                     ("shot",   "lines",   ELEC2,  1, "elec", False),
    "arcane_volley":                ("shot",   "lines",   ELEC,   1, "elec", False),
    "arcane_snare_arrow":           ("shot",   "ring",    (170, 150, 255), 1, "elec", False),
    "spore_burst_arrow":            ("shot",   "lines",   (220, 230, 255), 2, "elec", False),
    "astral_volley":                ("shot",   "sparkle", HOLY,   1, "holy", False),
    "shatterfrost_lance":           ("shot",   "frost",   FROST,  2, "frost", False),
    "void_shot":                    ("shot",   "glitch",  VOID,   1, "elec", False),
    "void_piercer":                 ("shot",   "death",   (150, 80, 200), 2, "death", False),
    "mag_charged_shot":             ("shot",   "lines",   (120, 180, 255), 3, "elec", False),
    "arcane_rail_shot":             ("shot",   "lines",   (205, 228, 255), 4, "elec", False),
    "turret_bolt":                  ("shot",   "lines",   ELEC,   0, "elec", True),
    "void_ballista_bolt":           ("shot",   "glitch",  VOID,   0, "elec", True),
    "astral_cannon_blast":          ("shot",   "sparkle", GOLD,   3, "holy", False),
    "spore_mortar_shell":           ("shot",   "lines",   MORTAR, 1, "elec", True),
    "pulse_turret_pulse":           ("nova",   "ring",    (160, 205, 255), 0, "elec", False),
    "arcane_battery_pulse":         ("nova",   "ring",    (120, 170, 255), 1, "elec", False),
    "arcane_mine_blast":            ("burst",  "lines",   (255, 225, 130), 1, "elec", False),
    "astral_flame_burst":           ("burst",  "sparkle", FLAME,  1, "holy", False),
    "glyph_snare_pulse":            ("nova",   "ring",    (170, 140, 255), 0, "elec", False),
    "singularity_collapse":         ("nova",   "ring",    (140, 120, 255), 3, "elec", False),
    "arc_spark_release":            ("burst",  "lines",   ELEC2,  1, "elec", False),
    "astral_wisp_release":          ("burst",  "sparkle", HOLY,   1, "holy", False),
    "shatterfrost_needle_release":  ("burst",  "frost",   FROST,  1, "frost", False),
    "void_pulse_release":           ("nova",   "ring",    VOID,   1, "death", False),
    "summon_arcane_turret":         ("summon", None,      ELEC,   0, "elec", False),
    "twin_turret_deployment":       ("summon", None,      ELEC,   0, "elec", False),
    "tri_node_deployment":          ("summon", None,      ELEC,   0, "elec", False),
    "summon_arcane_battery_turret": ("summon", None,      (110, 160, 255), 0, "elec", False),
    "summon_pulse_turret":          ("summon", None,      (160, 205, 255), 0, "elec", False),
    "summon_spore_mortar":          ("summon", None,      MORTAR, 0, "elec", False),
    "summon_void_ballista":         ("summon", None,      VOID,   0, "elec", False),
    "summon_astral_cannon":         ("summon", None,      GOLD,   0, "holy", False),
    "arcane_mine":                  ("summon", None,      (255, 225, 130), 0, "elec", False),
    "glyph_snare_trap":             ("summon", None,      (170, 140, 255), 0, "elec", False),
    "astral_flame_trap":            ("summon", None,      FLAME,  0, "holy", False),
    "arcane_singularity_trap":      ("summon", None,      (140, 120, 255), 0, "elec", False),
    "ballistic_infusion_arcane":    ("aura",   None,      ELEC,   0, "elec", False),
    "ballistic_infusion_frost":     ("aura",   None,      FROST,  0, "frost", False),
    "ballistic_infusion_astral":    ("aura",   None,      HOLY,   0, "holy", False),
    "ballistic_infusion_void":      ("aura",   None,      VOID,   0, "death", False),
    "turret_overclock":             ("aura",   None,      (255, 220, 100), 0, "elec", False),
}

abil = {}
for f in (ROOT / "abilities").glob("*.json"):
    a = json.load(open(f, encoding="utf-8-sig"))
    abil[a["id"]] = a

anims, fx = {}, {}
def put(a, ability_id=None):
    anims[a["id"]] = a
    if ability_id:
        fx[ability_id] = a["id"]
    return a

for short, (kind, flav, rgb, power, el, small) in PLAN.items():
    aid = P + short
    if aid not in abil:
        print("skip (no ability):", short)
        continue
    name = abil[aid]["name"]
    e = abil[aid].get("effects") or {}
    rng = int(e.get("aoe_range") or (2 if kind == "nova" else 1))
    s = slug(name)
    if kind == "shot":
        hid = f"{s}_fx_hit"
        h = put(hit(hid, f"{name} FX Hit", rgb, flav, max(1, rng), power))
        h["sound"] = {"id": SOUND[el], "volume": 100}
        b = put(bolt(f"{s}_fx", f"{name} FX", rgb, hid, small=small), aid)
        b["sound"] = {"id": SOUND[el], "volume": 100}
    elif kind == "burst":
        h = put(hit(f"{s}_fx", f"{name} FX", rgb, flav, max(1, rng), power), aid)
        h["sound"] = {"id": SOUND[el], "volume": 100}
    elif kind == "nova":
        n = put(nova(f"{s}_fx", f"{name} FX", rgb, "ring", big=(rng >= 3)), aid)
        n["sound"] = {"id": SOUND[el], "volume": 100}
        shake(n, power)
    elif kind == "summon":
        c = put(conjure(f"{s}_fx", f"{name} FX", rgb), aid)
    elif kind == "aura":
        a2 = put(aura(f"{s}_fx", f"{name} FX", rgb), aid)
        a2["sound"] = {"id": SOUND[el], "volume": 100}

print("animations:", len(anims), "bound abilities:", len(fx))
unbound = [k for k in abil if k not in fx]
print("abilities without FX:", [k.replace(P, "") for k in unbound])

(ROOT / "animations").mkdir(exist_ok=True)
for i, a in anims.items():
    (ROOT / "animations" / f"{i[len(P):]}.json").write_text(json.dumps(a, indent="\t", ensure_ascii=False), encoding="utf-8", newline="\n")
patched = 0
for f in (ROOT / "abilities").glob("*.json"):
    a = json.load(open(f, encoding="utf-8-sig"))
    if a.get("id") in fx and a.get("animation") != fx[a["id"]]:
        a["animation"] = fx[a["id"]]
        f.write_text(json.dumps(a, indent="\t", ensure_ascii=False), encoding="utf-8", newline="\n")
        patched += 1
print("wrote", len(anims), "animations, patched", patched, "abilities")

if "--preview" in sys.argv:
    sys.path.insert(0, r"D:\\games\\Ai assisted toolkit\\Tools\\Soulash2\\SkillCreator")
    os.chdir(r"D:\\games\\Ai assisted toolkit\\Tools\\Soulash2\\SkillCreator")
    from s2_fx_preview import write_preview_pack
    root = Path(r"D:\\games\\Ai assisted toolkit\\Tools\\Output\\Soulash2\\_fx_preview\\arcane_ballistics")
    for short in PLAN:
        a = anims.get(fx.get(P + short, ""))
        if a:
            write_preview_pack(a, root / short, extras=[x for i, x in anims.items() if i == a["id"] + "_hit"])
    print("previews written to", root)
