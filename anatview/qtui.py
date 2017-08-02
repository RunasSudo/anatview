WIDTH = 1200
HEIGHT = 675
FOV = 30

from . import model
from . import renderer

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QApplication, QGridLayout, QHeaderView, QLabel, QLineEdit, QMessageBox, QPushButton, QTreeView, QWidget

import pyglet
from pyglet.gl import *
import pywavefront

import os.path
import sys

lightfv = pyglet.gl.GLfloat * 4

class MainUI(QWidget):
	def __init__(self):
		super().__init__()
		
		self.renderer = renderer.Renderer()
		
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
		
		# Render button
		self.render_button = QPushButton('Render')
		self.render_button.clicked.connect(self.render_button_click)
		self.grid.addWidget(self.render_button, 8, 15)
		
		self.search_box.setFocus(True)
	
	def search_box_return(self):
		# not_before is loc
		def do_search(not_before):
			after_before = not_before is None # Flag representing if we are past the current selection
			def check_tree_item(loc, item):
				nonlocal after_before # ily python 3
				
				# Check for match
				if after_before and self.search_box.text() in item.name:
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
		return
		
		# Collate components
		components = set()
		def add_with_children(component):
			components.add(component.code)
			for child in component.children:
				add_with_children(child)
		
		for k, v in self.component_items.items():
			if v.item[2].checkState() == Qt.Checked:
				print(v.code, end=' ')
				add_with_children(v)
		print()
		
		# Resolve parts
		self.parts = set()
		def do_file(f):
			next(f) # skip header
			for line in f:
				bits = line.rstrip('\n').split('\t')
				if bits[0] in components:
					self.parts.add((bits[0], bits[2])) # TODO: stop passing these things around like crazy
		with open('data/isa_element_parts.txt', 'r') as f:
			do_file(f)
		with open('data/partof_element_parts.txt', 'r') as f:
			do_file(f)
		
		# Resolve filenames
		files = []
		for component, part in self.parts:
			if os.path.exists('data/partof_BP3D_4.0_obj_99/' + part + '.obj'):
				files.append((component, part, 'data/partof_BP3D_4.0_obj_99/' + part + '.obj'))
			elif os.path.exists('data/isa_BP3D_4.0_obj_99/' + part + '.obj'):
				files.append((component, part, 'data/isa_BP3D_4.0_obj_99/' + part + '.obj'))
			else:
				print('Warning: No file for part {}'.format(part))
		
		# Build OBJ
		def is_child(part, parent):
			if part == parent:
				return True
			for part_parent in part.parents:
				if is_child(part_parent, parent):
					return True
			return False
		
		print('Processing OBJ')
		bounds_min = [False, False, False]
		bounds_max = [False, False, False]
		for component, part, file_name in files:
			if part not in self.meshes:
				print('Parsing OBJ {}'.format(file_name))
				mesh = pywavefront.Wavefront(file_name, parse_materials=False, swap_yz=True)
				for mesh_ in mesh.mesh_list:
					for material in mesh_.materials:
						if is_child(self.component_items[component], self.component_items['FMA5018']): # bone organ
							material.set_diffuse([227/255, 218/255, 201/255, 1])
						elif is_child(self.component_items[component], self.component_items['FMA5022']): # muscle organ
							material.set_diffuse([169/255, 17/255, 1/255, 1])
				self.meshes[part] = mesh
			else:
				print('Cached OBJ {}'.format(file_name))
				mesh = self.meshes[part]
			bounds_min = [mesh.bounds_min[i] if bounds_min[i] is False else min(bounds_min[i], mesh.bounds_min[i]) for i in range(3)]
			bounds_max = [mesh.bounds_max[i] if bounds_max[i] is False else max(bounds_max[i], mesh.bounds_max[i]) for i in range(3)]
		
		print('Rendering OBJ')
		
		self.bounds_mid = [(bounds_min[x] + bounds_max[x]) / 2 for x in range(3)]
		
		if self.render_ui is None:
			self.render_ui = pyglet.window.Window(width=WIDTH, height=HEIGHT)
		
			rotation_x = 0
			rotation_y = 0
			translation_y = 0
			scale = 0.01
			
			@self.render_ui.event
			def on_resize(width, height):
				glMatrixMode(GL_PROJECTION)
				glLoadIdentity()
				gluPerspective(FOV, width/height, 1., 100.)
				glMatrixMode(GL_MODELVIEW)
				return True
			def set_light(num, x, y, z):
				glLightfv(num, GL_POSITION, lightfv(x, y, z, 1.0))
				glLightfv(num, GL_DIFFUSE, lightfv(1.0, 1.0, 1.0, 1.0))
				glLightf(num, GL_CONSTANT_ATTENUATION, 0.0)
				glLightf(num, GL_QUADRATIC_ATTENUATION, 0.75)
				glEnable(num)
			@self.render_ui.event
			def on_draw():
				self.render_ui.clear()
				glLoadIdentity()
				
				glEnable(GL_LIGHTING)
				glShadeModel(GL_SMOOTH)
				set_light(GL_LIGHT0, 1.0, 1.0, 1.0)
				set_light(GL_LIGHT1, 1.0, 1.0, -1.0)
				set_light(GL_LIGHT2, -1.0, 1.0, -1.0)
				set_light(GL_LIGHT3, -1.0, 1.0, 1.0)
				#set_light(GL_LIGHT4, 0.0, -3.0, 0.0)
				glEnable(GL_NORMALIZE) # required for correct lighting when we scale
				
				glEnable(GL_DEPTH_TEST)
				glDepthFunc(GL_LEQUAL)
				
				glTranslated(0, translation_y, -3.0)
				glRotatef(rotation_x, 1, 0, 0)
				glRotatef(rotation_y, 0, 1, 0)
				glScalef(scale, scale, scale)
				glTranslated(-self.bounds_mid[0], -self.bounds_mid[1], -self.bounds_mid[2])
				
				for _, part in self.parts:
					self.meshes[part].draw()
			@self.render_ui.event
			def on_mouse_drag(x, y, dx, dy, buttons, modifiers):
				nonlocal rotation_x
				nonlocal rotation_y
				rotation_y += dx
				rotation_x -= dy
			@self.render_ui.event
			def on_mouse_scroll(x, y, scroll_x, scroll_y):
				nonlocal scale
				scale += scroll_y * 0.001
			@self.render_ui.event
			def on_key_press(symbol, modifiers):
				nonlocal translation_y
				if symbol == pyglet.window.key.W:
					translation_y -= 0.3
				elif symbol == pyglet.window.key.S:
					translation_y += 0.3
			
			timer = QTimer(self)
			def on_timer_timeout():
				# Supplant event loop
				pyglet.clock.tick()
				for window in pyglet.app.windows:
					window.switch_to()
					window.dispatch_events()
					window.dispatch_event('on_draw')
					window.flip()
			timer.timeout.connect(on_timer_timeout)
			timer.start(0)
