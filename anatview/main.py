#!/usr/bin/env python3

from . import qtui

from PyQt5.QtWidgets import QApplication

import sys

app = QApplication(sys.argv)

w = qtui.MainUI()
w.show()

sys.exit(app.exec_())
