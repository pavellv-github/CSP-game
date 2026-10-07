#!/usr/bin/env python3
"""Builds a local page that copies hero sprite composites to the clipboard for pasting into Miro.

Each composite = the hero's animation sheet x3 plus the sprites of its attack (projectile,
explosion VFX) and skill (VFX, companion), all taken from game/data. Miro's page cannot load
images from localhost, so the transfer goes through the system clipboard (see the miro-sync skill).

Usage: python3 tools/miro/make_copy_page.py <out_dir> [hero_id ...]
Then serve <out_dir> (python3 -m http.server 8765 -d <out_dir>) and open /copy.html.
"""
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GAME = ROOT / "game"


def res_path(res: str) -> Path:
	return GAME / res.removeprefix("res://")


def main() -> None:
	out = Path(sys.argv[1])
	only = set(sys.argv[2:])
	out.mkdir(parents=True, exist_ok=True)
	characters = json.loads((GAME / "data/characters/characters.json").read_text())["items"]
	skills = {s["id"]: s for s in json.loads((GAME / "data/skills/skills.json").read_text())["items"]}
	heroes = {}
	for c in characters:
		hero = c["id"].removeprefix("character_")
		if c.get("status") != "published" or (only and hero not in only):
			continue
		sprites = [c["sprite"]]
		projectile = c.get("attack", {}).get("projectile", {})
		sprites += [projectile[k] for k in ("sprite", "aoe_vfx") if k in projectile]
		for skill_id in c.get("skills", []):
			skill = skills.get(skill_id, {})
			sprites += [skill[k] for k in ("vfx",) if k in skill]
			sprites += [skill[k]["sprite"] for k in ("projectile", "companion") if k in skill]
		names = []
		for res in dict.fromkeys(sprites):
			src = res_path(res)
			name = f"{src.parent.name}_{src.name}"
			shutil.copyfile(src, out / name)
			names.append(name)
		heroes[hero] = names
	template = (Path(__file__).parent / "copy_template.html").read_text()
	(out / "copy.html").write_text(template.replace("/*HEROES*/{}", json.dumps(heroes)))
	print(f"{out / 'copy.html'}: {', '.join(heroes)}")


if __name__ == "__main__":
	main()
