#!/usr/bin/env python3
#    anatview - Open-source offline viewer of BodyParts3D models
#    Copyright © 2017  Yingtong Li (RunasSudo)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

from . import qtui

from PyQt5.QtWidgets import QApplication

import sys

app = QApplication(sys.argv)

w = qtui.MainWindow()
w.show()

sys.exit(app.exec_())
