WIDTH = 1200
HEIGHT = 675
FOV = 30

from . import model
from . import renderer

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QApplication, QGridLayout, QHeaderView, QLabel, QLineEdit, QMessageBox, QPushButton, QTabWidget, QTreeView, QWidget

import sys

class MainUI(QWidget):
	def __init__(self):
		super().__init__()
		
		self.renderer = renderer.Renderer(self)
		
		# Init UI
		
		self.setGeometry(300, 300, WIDTH, HEIGHT)
		self.setWindowTitle('Anatomy')
		
		self.grid = QGridLayout()
		self.setLayout(self.grid)
		
		# Search box
		self.search_box = QLineEdit()
		self.search_box.returnPressed.connect(self.search_box_return)
		self.grid.addWidget(QLabel('Search:'), 0, 0)
		self.grid.addWidget(self.search_box, 0, 1, 1, 15)
		
		self.list_tab = ListTab(self)
		
		self.tab_widget = QTabWidget()
		self.tab_widget.addTab(self.list_tab, 'List')
		
		self.grid.addWidget(self.tab_widget, 1, 0, 7, 16)
		
		# Render button
		self.render_button = QPushButton('Render')
		self.render_button.clicked.connect(self.render_button_click)
		self.grid.addWidget(self.render_button, 8, 15)
		
		self.search_box.setFocus(True)
	
	def search_box_return(self):
		self.list_tab.search_box_return()
	
	def render_button_click(self):
		self.list_tab.render_button_click()

class ListTab(QWidget):
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
			check_item.setCheckState(Qt.Unchecked)
			
			if child.code in sys.argv[1:]:
				check_item.setCheckState(Qt.Checked)
				sys.argv.remove(child.code) # one only
			
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
				if after_before and self.main_ui.search_box.text() in item.name:
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
			current_loc = next(k for k, v in current_component.items.items() if v[0] == current_item)
			do_search(current_loc)
		else:
			do_search(None)
	
	def render_button_click(self):
		# Collate components
		locs = set()
		def add_with_children(loc, component):
			locs.add(loc)
			for child in component.children:
				add_with_children(loc + (child.code,), child)
		
		for k, v in model.ComponentItem.component_items.items():
			for loc, item in v.items.items():
				if item[2].checkState() == Qt.Checked:
					print(v.code, end=' ')
					add_with_children(loc, v)
		print()
		
		self.main_ui.renderer.set_locs(locs)
		self.main_ui.renderer.render()
