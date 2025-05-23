from PyQt6.QtCore import QByteArray, QSize, pyqtSignal
from PyQt6.QtGui import QResizeEvent
from PyQt6.QtSvgWidgets import QSvgWidget

from font.hp1345Font import Font
from font.mksvgs import makeSvgString
from gnss.nmea import GnssData
from misc.config import MiscStatsConfig
from palettes.palette import Palette
from views.baseWindow import BaseWindow
from views.stats.generate import generateStats


class MiscStatsWindow(BaseWindow):
	"""Window for displaying miscellaneous statistics"""

	satelliteReceivedEvent = pyqtSignal()

	def __init__(self, palette: Palette, config: MiscStatsConfig):
		super().__init__(palette)
		self.setWindowTitle("Misc Stats")
		self.config = config

		self.satelliteReceivedEvent.connect(self.updateWithNewData)
		self.latestData = GnssData()

		self.svgFont = Font()
		(svgStr, width, height) = makeSvgString(
			self.svgFont,
			"Waiting for data...".encode("ascii"),
			fontThickness=self.config.fontThickness,
			fontColour=palette.foreground,
		)
		self.svg = QSvgWidget(parent=self)
		self.svg.load(QByteArray(svgStr.encode()))
		self.svg.setGeometry(0, 0, width, height)

	def resizeEvent(self, event: QResizeEvent | None):
		"""Resize the text to always fit the window"""
		super().resizeEvent(event)
		if event is None:
			return
		self.resizeSvg(event.size())

	def resizeSvg(self, size: QSize):
		"""Resize the SVG to always fit within the window"""
		newWidth = size.width()
		newHeight = size.height()
		oldWidth = self.svg.width()
		oldHeight = self.svg.height()

		if newWidth / oldWidth < newHeight / oldHeight:
			newHeight = round(oldHeight * newWidth / oldWidth)
		else:
			newWidth = round(oldWidth * newHeight / oldHeight)

		self.svg.setGeometry(0, 0, newWidth, newHeight)

	def onNewData(self, gnssData: GnssData):
		"""Update window with new data"""
		self.latestData = gnssData
		self.satelliteReceivedEvent.emit()

	def updateWithNewData(self):
		"""Update the misc stats window with new data"""
		if self.latestData is None:
			return
		(svgStr, desiredWidth, desiredHeight) = generateStats(
			self.latestData, self.customPalette, self.svgFont, self.config
		)

		if desiredWidth / self.svg.width() < desiredHeight / self.svg.height():
			height = desiredHeight * self.svg.width() / desiredWidth
			width = self.svg.width()
		else:
			width = desiredWidth * self.svg.height() / desiredHeight
			height = self.svg.height()

		self.svg.load(QByteArray(svgStr.encode()))
		self.svg.setGeometry(0, 0, int(width), int(height))

		self.resizeSvg(self.size())
