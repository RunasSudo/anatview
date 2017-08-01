#!/usr/bin/env python3

WIDTH = 1200
HEIGHT = 675
FOV = 30

import ctypes
import os
import os.path
import re
import sys
import tempfile

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QApplication, QGridLayout, QHeaderView, QLabel, QLineEdit, QPushButton, QTreeView, QWidget

import pyglet
from pyglet.gl import *
import pywavefront

lightfv = ctypes.c_float * 4

class ComponentItem:
	def __init__(self, code, name, parent=None, children=None, item=None):
		self.code = code
		self.name = name
		self.parent = parent
		self.children = [] if children is None else children
		self.item = item

class MainUI(QWidget):
	def __init__(self):
		super().__init__()
		
		self.render_ui = None
		self.meshes = {} # id -> Wavefront
		
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
		self.component_items = {}
		def do_file(f):
			next(f) # skip header
			for line in f:
				bits = line.rstrip('\n').split('\t')
				if bits[0] not in self.component_items:
					self.component_items[bits[0]] = ComponentItem(bits[0], bits[1])
				if bits[2] not in self.component_items:
					self.component_items[bits[2]] = ComponentItem(bits[2], bits[3])
				self.component_items[bits[0]].children.append(self.component_items[bits[2]])
				self.component_items[bits[2]].parent = self.component_items[bits[0]]
		with open('data/isa_inclusion_relation_list.txt', 'r') as f:
			do_file(f)
		with open('data/partof_inclusion_relation_list.txt', 'r') as f:
			do_file(f)
		
		# Build QT tree
		def walk_tree(item, child):
			check_item = QStandardItem()
			check_item.setCheckable(True)
			check_item.setCheckState(Qt.Unchecked)
			
			if child.code in sys.argv[1:]:
				check_item.setCheckState(Qt.Checked)
			
			child_item = [QStandardItem(child.code), QStandardItem(child.name), check_item]
			item.appendRow(child_item)
			child.item = child_item
			for subchild in child.children:
				walk_tree(child_item[0], subchild)
		
		for k, v in self.component_items.items():
			if v.parent is None:
				walk_tree(self.tree, v)
		
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
		if self.tree_view.selectionModel().hasSelection():
			not_before = self.component_items[self.tree_view.currentIndex().sibling(self.tree_view.currentIndex().row(), 0).data()]
			#not_before = self.component_items[self.tree_model.item(self.tree_view.currentIndex().row(), 0).text()]
		else:
			not_before = None
		
		after_before = not_before is None # Flag representing if we are past the current selection
		def walk_tree(item):
			nonlocal after_before # ily python 3
			
			# Check for match
			if after_before and self.search_box.text() in item.name:
				return item
			
			# Are we passing the current selection?
			if item == not_before:
				after_before = True
			
			# Descend into children
			for child in item.children:
				val = walk_tree(child)
				if val is not None:
					return val
			return None
		
		result = None
		for k, v in self.component_items.items():
			if v.parent is None:
				result = walk_tree(v)
				if result is not None:
					break
		
		if result is not None:
			self.tree_view.setCurrentIndex(result.item[0].index())
			self.tree_view.scrollTo(result.item[0].index())
	
	def render_button_click(self):
		# Collate components
		components = set()
		def add_children(component):
			for child in component.children:
				components.add(child.code)
				add_children(child)
		
		for k, v in self.component_items.items():
			if v.item[2].checkState() == Qt.Checked:
				print(v.code, end=' ')
				components.add(v.code)
				add_children(v)
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
		print('Processing OBJ')
		bounds_min = [False, False, False]
		bounds_max = [False, False, False]
		for component, part, file_name in files:
			if part not in self.meshes:
				print('Parsing OBJ {}'.format(file_name))
				mesh = pywavefront.Wavefront(file_name, parse_materials=False, swap_yz=True)
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
				glLightf(num, GL_QUADRATIC_ATTENUATION, 10.0)
				glEnable(num)
			@self.render_ui.event
			def on_draw():
				self.render_ui.clear()
				glLoadIdentity()
				
				glEnable(GL_LIGHTING)
				glShadeModel(GL_SMOOTH)
				set_light(GL_LIGHT0, 3.0, 3.0, 3.0)
				set_light(GL_LIGHT1, 3.0, 3.0, -3.0)
				set_light(GL_LIGHT2, -3.0, 3.0, -3.0)
				set_light(GL_LIGHT3, -3.0, 3.0, 3.0)
				set_light(GL_LIGHT4, 0.0, -3.0, 0.0)
				
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

app = QApplication(sys.argv)

w = MainUI()
w.show()

sys.exit(app.exec_())
