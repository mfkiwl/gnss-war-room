from dataclasses import dataclass

from dataclass_wizard import JSONWizard


@dataclass
class Palette(JSONWizard):
	"""Color palette for the map."""

	background: str
	foreground: str
	admin0Border: str
	continentsBorder: str
	cities: str
	polarGrid: str
	satelliteNetworks: dict[str, str]


def loadPalette(paletteName: str) -> Palette:
	"""Load the palette with the given name."""
	with open(f"palettes/{paletteName}.json", "r", encoding="utf8") as f:
		palette = Palette.from_json(f.read())
		if isinstance(palette, list):
			palette = palette[0]
	return palette
