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

from . import model
from . import renderer

from PyQt5.QtCore import Qt, QSize, QThread, pyqtSignal
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QAction, QApplication, QFileDialog, QGridLayout, QHeaderView, QLabel, QLineEdit, QMainWindow, QMessageBox, QProgressDialog, QPushButton, QStyle, QTabWidget, QTreeView, QWidget

import re
import sys
import yaml

class MainWindow(QMainWindow):
	def __init__(self):
		super().__init__()
		
		self.main_ui = MainUI()
		self.setCentralWidget(self.main_ui)
		
		# Center window
		self.setGeometry(QStyle.alignedRect(Qt.LeftToRight, Qt.AlignCenter, QSize(renderer.WIDTH, renderer.HEIGHT), QApplication.instance().desktop().availableGeometry()))
		self.setWindowTitle('Anatomy')
		
		# Menu bars
		menu_file = self.menuBar().addMenu('&File')
		action_save = QAction('&Save', self)
		action_save.triggered.connect(self.on_menu_save)
		menu_file.addAction(action_save)
		action_load = QAction('&Load', self)
		action_load.triggered.connect(self.on_menu_load)
		menu_file.addAction(action_load)
		
		# Process arguments
		if len(sys.argv) > 1:
			self.load_from_file(sys.argv[1])
	
	def load_from_file(self, filename):
		with open(filename, 'r') as f:
			result = yaml.load(f)
		
		# Clear selections
		self.main_ui.list_tab.tree_model.removeRows(0, self.main_ui.list_tab.tree_model.rowCount())
		for code, component in model.ComponentItem.component_items.items():
			for loc, item in component.items.items():
				item[2].setCheckState(Qt.Unchecked)
			component.list_item = None
		
		# Parse selections
		for code, data in result.items():
			if code not in model.ComponentItem.component_items:
				print('Warning: Unknown item {}. No substitute available'.format(code))
			else:
				component = model.ComponentItem.component_items[code]
				for loc, checked in data['tree'].items():
					if loc not in component.items:
						substitute_loc = next(iter(component.items))
						print('Warning: Unknown item {}. Substituting'.format('>'.join(loc), '>'.join(substitute_loc)))
						loc = substitute_loc
					component.items[loc][2].setCheckState(Qt.Checked if checked else Qt.Unchecked)
				self.main_ui.list_tab.tree.appendRow(component.make_list_item(data['list'] if 'list' in data else True))
	
	def on_menu_load(self):
		filenames = QFileDialog.getOpenFileName(self, 'Open')
		if filenames and filenames[0]:
			self.load_from_file(filenames[0])
	
	def on_menu_save(self):
		filenames = QFileDialog.getSaveFileName(self, 'Save')
		if filenames and filenames[0]:
			result = {}
			for code, component in model.ComponentItem.component_items.items():
				data = {
					'tree': {loc: True for loc, item in component.items.items() if item[2].checkState() == Qt.Checked}
				}
				if component.list_item:
					data['list'] = component.list_item[2].checkState() == Qt.Checked
				
				if any(v == True for k, v in data['tree'].items()):
					result[code] = data
			with open(filenames[0], 'w') as f:
				yaml.dump(result, f)

class MainUI(QWidget):
	def __init__(self):
		super().__init__()
		
		self.renderer = renderer.Renderer(self)
		
		# Init UI
		
		self.grid = QGridLayout()
		self.setLayout(self.grid)
		
		# Search box
		self.search_box = QLineEdit()
		self.search_box.returnPressed.connect(self.search_box_return)
		self.grid.addWidget(QLabel('Search:'), 0, 0)
		self.grid.addWidget(self.search_box, 0, 1, 1, 15)
		
		self.tab_widget = QTabWidget()
		self.tree_tab = TreeTab(self)
		self.tab_widget.addTab(self.tree_tab, 'FMA Tree')
		self.list_tab = ListTab(self)
		self.tab_widget.addTab(self.list_tab, 'Selection List')
		
		self.grid.addWidget(self.tab_widget, 1, 0, 7, 16)
		
		# Render button
		self.render_button = QPushButton('Render')
		self.render_button.clicked.connect(self.render_button_click)
		self.grid.addWidget(self.render_button, 8, 15)
		
		self.search_box.setFocus(True)
	
	def search_box_return(self):
		if self.tab_widget.currentIndex() == 0:
			self.tree_tab.search_box_return()
		else:
			self.list_tab.search_box_return()
	
	def render_button_click(self):
		if self.tab_widget.currentIndex() == 0:
			self.tree_tab.render_button_click()
		else:
			self.list_tab.render_button_click()

class TreeTab(QWidget):
	def __init__(self, main_ui):
		super().__init__()
		
		self.main_ui = main_ui
		
		self.grid = QGridLayout()
		self.setLayout(self.grid)
		
		self.tree_model = QStandardItemModel()
		self.tree_model.setHorizontalHeaderItem(0, QStandardItem('ID'))
		self.tree_model.setHorizontalHeaderItem(1, QStandardItem('Name'))
		self.tree_model.setHorizontalHeaderItem(2, QStandardItem('?'))
		self.tree = self.tree_model.invisibleRootItem()
		
		# Load tree data
		model.ComponentItem.load_component_items()
		
		# Build QT tree
		def add_to_tree(loc, child):
			check_item = QStandardItem()
			check_item.setCheckable(True)
			check_item.setEnabled(child.parts is not None)
			check_item.setCheckState(Qt.Unchecked)
			
			child_item = [QStandardItem(child.code), QStandardItem(child.name), check_item]
			if len(loc) <= 1:
				self.tree.appendRow(child_item)
			else:
				model.ComponentItem.item_by_loc(loc[:-1])[0].appendRow(child_item)
			child.items[loc] = child_item
		
		model.ComponentItem.walk_tree(add_to_tree)
		
		self.tree_view = QTreeView()
		self.tree_view.setModel(self.tree_model)
		self.tree_view.header().resizeSection(0, 400)
		self.tree_view.header().setSectionResizeMode(1, QHeaderView.Stretch)
		self.tree_view.header().resizeSection(2, 32)
		self.tree_view.header().setStretchLastSection(False)
		self.grid.addWidget(self.tree_view, 1, 0, 7, 16)
	
	def search_box_return(self):
		# not_before is loc
		def do_search(not_before):
			after_before = not_before is None # Flag representing if we are past the current selection
			def check_tree_item(loc, item):
				nonlocal after_before # ily python 3
				
				# Check for match
				if after_before and item.parts is not None and item.name and re.search(self.main_ui.search_box.text(), item.name):
					return loc
				
				# Are we passing the current selection?
				if loc == not_before:
					after_before = True
				
				return None # Continue to children
			
			result = model.ComponentItem.walk_tree(check_tree_item)
			
			if result is not None:
				result_item = model.ComponentItem.item_by_loc(result)
				self.tree_view.setCurrentIndex(result_item[0].index())
				self.tree_view.scrollTo(result_item[0].index())
			else:
				# no result, try again for another pass
				if not_before is not None:
					do_search(None)
				else:
					msgBox = QMessageBox()
					msgBox.setText('No search results.');
					msgBox.exec();
		
		if self.tree_view.selectionModel().hasSelection():
			# qt is hard :(
			current_index = self.tree_view.currentIndex().sibling(self.tree_view.currentIndex().row(), 0)
			current_item = self.tree_model.itemFromIndex(current_index) # points to item[0]
			current_code = current_index.data() # slightly hacky
			current_component = model.ComponentItem.component_items[current_code]
			if re.search(self.main_ui.search_box.text(), current_component.name):
				# resume search only if the current item matches
				current_loc = next(k for k, v in current_component.items.items() if v[0] == current_item)
				do_search(current_loc)
			else:
				# otherwise, start from the top
				do_search(None)
		else:
			do_search(None)
	
	def render_button_click(self):
		# Collate components
		locs_base = []
		locs = set()
		def add_with_children(loc, component):
			if component.parts is not None:
				locs.add(loc)
				for child in component.children:
					add_with_children(loc + (child.code,), child)
		
		for k, v in model.ComponentItem.component_items.items():
			for loc, item in v.items.items():
				if item[2].checkState() == Qt.Checked:
					print(v.code, end=' ')
					locs_base.append(v)
					add_with_children(loc, v)
		print()
		
		# Update list
		for code, component in model.ComponentItem.component_items.items():
			if component in locs_base:
				if component.list_item is None:
					self.main_ui.list_tab.tree.appendRow(component.make_list_item(True))
			else:
				if component.list_item is not None:
					self.main_ui.list_tab.tree_model.removeRows(component.list_item[0].row(), 1)
					component.list_item = None
		
		to_load = self.main_ui.renderer.set_locs(locs)
		
		# Load models and wait
		self.progress_worker = RenderWaitWavefrontsWorker(self.main_ui.renderer, to_load)
		self.progress_worker.start()

class ListTab(QWidget):
	def __init__(self, main_ui):
		super().__init__()
		
		self.main_ui = main_ui
		
		self.grid = QGridLayout()
		self.setLayout(self.grid)
		
		# TODO: Standardize
		self.tree_model = QStandardItemModel()
		self.tree_model.setHorizontalHeaderItem(0, QStandardItem('ID'))
		self.tree_model.setHorizontalHeaderItem(1, QStandardItem('Name'))
		self.tree_model.setHorizontalHeaderItem(2, QStandardItem('?'))
		self.tree = self.tree_model.invisibleRootItem()
		
		self.tree_view = QTreeView()
		self.tree_view.setModel(self.tree_model)
		self.tree_view.header().resizeSection(0, 400)
		self.tree_view.header().setSectionResizeMode(1, QHeaderView.Stretch)
		self.tree_view.header().resizeSection(2, 32)
		self.tree_view.header().setStretchLastSection(False)
		self.grid.addWidget(self.tree_view, 1, 0, 7, 16)
	
	def search_box_return(self):
		... # TODO
	
	def render_button_click(self):
		# Collate components
		locs = set()
		def add_with_children(loc, component):
			if component.parts is not None:
				locs.add(loc)
				for child in component.children:
					add_with_children(loc + (child.code,), child)
		
		for k, v in model.ComponentItem.component_items.items():
			if v.list_item is not None and v.list_item[2].checkState() == Qt.Checked:
				for loc, item in v.items.items():
					if item[2].checkState() == Qt.Checked:
						add_with_children(loc, v)
		
		to_load = self.main_ui.renderer.set_locs(locs)
		
		# Load models and wait
		self.progress_worker = RenderWaitWavefrontsWorker(self.main_ui.renderer, to_load)
		self.progress_worker.start()

class RenderWaitWavefrontsWorker(QThread):
	progress_signal = pyqtSignal(int)
	ready_signal = pyqtSignal()
	
	def __init__(self, renderer, to_load):
		super().__init__()
		self.renderer = renderer
		
		self.progress_dialog = QProgressDialog('Loading models', None, 0, to_load, flags=Qt.WindowStaysOnTopHint)
		self.progress_dialog.setMinimumDuration(0)
		
		self.progress_signal.connect(self.progress_dialog.setValue)
		def on_ready():
			self.renderer.render()
			self.progress_dialog.reset()
		self.ready_signal.connect(on_ready)
		
		self.renderer.render_timer.stop()
	
	def run(self):
		self.progress_signal.emit(0) # setValue(0)
		#self.ready_signal.emit()
		self.renderer.load_objs(self.progress_signal.emit)
		self.ready_signal.emit()
