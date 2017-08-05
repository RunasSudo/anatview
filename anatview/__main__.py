#!/usr/bin/env python3

from . import qtui

from PyQt5.QtWidgets import QApplication

import sys

app = QApplication(sys.argv)

w = qtui.MainWindow()
w.show()

sys.exit(app.exec_())
