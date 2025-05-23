import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from palettes.palette import Palette


@dataclass
class SatelliteInView:
	"""Satellite data"""

	prnNumber: int = 0
	network: str = "??"
	elevation: float = 0
	azimuth: float = 0
	previousPositions: list[tuple[datetime, float, float]] = field(default_factory=list)
	snr: float = 0
	lastSeen: datetime = field(default_factory=lambda: datetime.fromtimestamp(0))

	def toJSON(
		self,
		measuredFromLat: float,
		measuredFromLong: float,
		palette: Palette,
		currentTime: datetime,
	) -> dict[str, Any]:
		"""Return data as dictionary to be converted to json"""
		lat, long = getSatelliteLatLong(
			self.azimuth, self.elevation, self.network, measuredFromLat, measuredFromLong
		)
		(lat, long) = rotateLatLongByTime((lat, long), self.lastSeen, currentTime)

		previousPositions = [
			(
				str(measuredTime),
				rotateLatLongByTime(
					getSatelliteLatLong(
						azimuth, elevation, self.network, measuredFromLat, measuredFromLong
					),
					measuredTime,
					currentTime,
				),
			)
			for (measuredTime, elevation, azimuth) in self.previousPositions
		]
		previousPositions.append((str(self.lastSeen), (lat, long)))

		return {
			"prnNumber": self.prnNumber,
			"network": self.network,
			"elevation": self.elevation,
			"azimuth": self.azimuth,
			"snr": self.snr,
			"lastSeen": self.lastSeen.isoformat(),
			"lat": lat,
			"long": long,
			"colour": colourForNetwork(self.network, palette),
			"altitude": orbitHeightForNetwork(self.network),
			"previousPositions": previousPositions,
		}


def rotateLatLongByTime(
	latLong: tuple[float, float], measuredTime: datetime, currentTime: datetime
) -> tuple[float, float]:
	"""Rotates a lat/long coordinate by the time passed since the measurement time."""
	rotationPerDay = 360.985647
	rotationPerSecond = rotationPerDay / (24 * 60 * 60)
	timePassed = (currentTime - measuredTime).total_seconds()
	return (latLong[0], latLong[1] - timePassed * rotationPerSecond)


def colourForNetwork(network: str, palette: Palette) -> str:
	networkName = networkCodeToName(network)
	if networkName in palette.satelliteNetworks:
		return palette.satelliteNetworks[networkName]
	return palette.satelliteNetworks["Unknown"]


def networkCodeToName(networkCode: str) -> str:
	"""Map a talker ID/network code to a network name"""
	match networkCode:
		case "GA":
			return "Galileo"
		case "GP":
			return "GPS"
		case "GL":
			return "GLONASS"
		case "BD" | "GB":
			return "BeiDou"
		case "GQ":
			return "QZSS"
		case _:
			return "Unknown"


def nameToNetworkCode(name: str) -> str:
	"""Map a network name to a talker ID/network code"""
	match name:
		case "Galileo":
			return "GA"
		case "GPS":
			return "GP"
		case "GLONASS":
			return "GL"
		case "BeiDou":
			return "GB"
		case "QZSS":
			return "GQ"
		case _:
			return "GZ"


def orbitHeightForNetwork(network: str) -> float:
	"""Map a network ID to its orbit height"""
	match network:
		case "GA":  # Galileo
			return 23.222
		case "GP":  # GPS
			return 20.18
		case "GL":  # GLONASS
			return 19.13
		case "BD" | "GB":
			# BeiDou
			return 21.528
		case "GQ":
			return 42.164
		case _:  # something else I need to add
			print(network)
			return 21.0  # in the middle-ish


def azimuthToWorldXyz(
	azimuth: float, elevation: float, satelliteNetwork: str
) -> tuple[float, float, float]:
	"""Projecting from the azimuth and elevation to world xyz coordinates
	:param azimuth: in degrees
	:param elevation: in degrees
	"""
	# https://www.desmos.com/3d/jxqcoesfg3 for visualisation of 3d,
	# https://www.desmos.com/calculator/oskkcd5rdb for 2d

	azimuthRadians = math.radians(azimuth)

	orbit = orbitHeightForNetwork(satelliteNetwork)
	ground = 6.37

	x1, x2 = calcX(elevation, orbit, ground)
	x1 *= math.cos(azimuthRadians)
	x2 *= math.cos(azimuthRadians)

	y1, y2 = calcY(elevation, orbit, ground)

	z1 = x1 * math.tan(azimuthRadians)
	z2 = x2 * math.tan(azimuthRadians)

	# divide by orbit
	x1 /= orbit
	y1 /= orbit
	z1 /= orbit

	x2 /= orbit
	y2 /= orbit
	z2 /= orbit

	return (x1, y2, z1)


def calcY(elevation: float, orbit: float, ground: float) -> tuple[float, float]:
	"""Calculate possible global Y coordinates of a satellite"""
	if elevation == 0:
		return (ground, ground)

	yConst = 1 / (math.tan(math.radians(elevation))) ** 2
	ay = -1 - yConst
	by = 2 * ground * yConst
	cy = orbit**2 - ground**2 * yConst

	y1, y2 = quadraticFormula(ay, by, cy)
	return y1, y2


def calcX(elevation: float, orbit: float, ground: float) -> tuple[float, float]:
	"""Calculate possible global X coordinates of a satellite"""
	if elevation == 90:
		return 0, 0

	ax = 1 + math.tan(math.radians(elevation)) ** 2
	bx = 2 * ground * math.tan(math.radians(elevation))
	cx = ground**2 - orbit**2

	x1, x2 = quadraticFormula(ax, bx, cx)
	return x1, x2


def quadraticFormula(a: float, b: float, c: float) -> tuple[float, float]:
	discriminant = b**2 - 4 * a * c
	root1 = (-b + math.sqrt(discriminant)) / (2 * a)
	root2 = (-b - math.sqrt(discriminant)) / (2 * a)
	return (root1, root2)


def xyzToLatLong(x: float, y: float, z: float) -> tuple[float, float]:
	"""Projecting from the xyz coordinates to the lat long coordinates. XYZ should be in the range
	[-1, 1]
	"""
	lat = math.degrees(math.asin(x))
	long = math.degrees(math.atan2(z, y))
	return (lat, long)


def rotateXyzByLatitude(x: float, y: float, z: float, lat: float) -> tuple[float, float, float]:
	"""Rotate the xyz coordinates by the given longitude"""
	rotationAngle = math.radians(-lat)
	x2 = x * math.cos(rotationAngle) - y * math.sin(rotationAngle)
	y2 = x * math.sin(rotationAngle) + y * math.cos(rotationAngle)
	return (x2, y2, z)


def getSatelliteLatLong(
	azimuth: float,
	elevation: float,
	satelliteNetwork: str,
	measuredFromLat: float,
	measuredFromLong: float,
) -> tuple[float, float]:
	"""Get the lat/long of a satellite"""
	x, y, z = azimuthToWorldXyz(azimuth, elevation, satelliteNetwork)
	x, y, z = rotateXyzByLatitude(x, y, z, measuredFromLat)
	lat, long = xyzToLatLong(x, y, z)
	long += measuredFromLong
	return (lat, long)


def isSameSatellite(satellite1: SatelliteInView, satellite2: SatelliteInView) -> bool:
	return satellite1.prnNumber == satellite2.prnNumber and satellite1.network == satellite2.network
