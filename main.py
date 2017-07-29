#!/usr/bin/env python3

import ctypes
import os
import os.path
import re
import sys
import tempfile

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtWidgets import QApplication, QGridLayout, QHeaderView, QLabel, QLineEdit, QPushButton, QTreeView, QWidget

import pyglet
from pyglet.gl import *
import pywavefront

# Patch
import pywavefront.material
_Material_init = pywavefront.material.Material.__init__
pywavefront.material.Material.__init__ = lambda self, name=None: _Material_init(self, name)

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
		
		# Init UI
		
		self.setGeometry(300, 300, 1600, 900)
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
		with open('/home/runassudo/Documents/Anatomy/data/isa_inclusion_relation_list.txt', 'r') as f:
			do_file(f)
		with open('/home/runassudo/Documents/Anatomy/data/partof_inclusion_relation_list.txt', 'r') as f:
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
				components.add(v.code)
				add_children(v)
		
		# Resolve parts
		parts = set()
		def do_file(f):
			next(f) # skip header
			for line in f:
				bits = line.rstrip('\n').split('\t')
				if bits[0] in components:
					parts.add(bits[2])
		with open('/home/runassudo/Documents/Anatomy/data/isa_element_parts.txt', 'r') as f:
			do_file(f)
		with open('/home/runassudo/Documents/Anatomy/data/partof_element_parts.txt', 'r') as f:
			do_file(f)
		
		# Resolve filenames
		files = []
		for part in parts:
			if os.path.exists('/home/runassudo/Documents/Anatomy/data/partof_BP3D_4.0_obj_99/' + part + '.obj'):
				files.append((part, '/home/runassudo/Documents/Anatomy/data/partof_BP3D_4.0_obj_99/' + part + '.obj'))
			elif os.path.exists('/home/runassudo/Documents/Anatomy/data/isa_BP3D_4.0_obj_99/' + part + '.obj'):
				files.append((part, '/home/runassudo/Documents/Anatomy/data/isa_BP3D_4.0_obj_99/' + part + '.obj'))
			else:
				print('Warning: No file for part {}'.format(part))
		
		# Build OBJ
		print('Building OBJ')
		with tempfile.NamedTemporaryFile('w', suffix='.obj', prefix='anatomy_', delete=False) as f:
			v_offset = 0
			vn_offset = 0
			bounds_min = [False, False, False]
			bounds_max = [False, False, False]
			for part, file_name in files:
				with open(file_name, 'r') as f2:
					v_num = 0
					vn_num = 0
					for line in f2:
						line = line.rstrip()
						if line.startswith('v '):
							v_num += 1
							bits = line.split(' ')
							print('v ' + bits[1] + ' ' + bits[3] + ' ' + bits[2], file=f) # swap y/z
						elif line.startswith('vn '):
							vn_num += 1
							bits = line.split(' ')
							print('vn ' + bits[1] + ' ' + bits[3] + ' ' + bits[2], file=f) # swap y/z
						elif line.startswith('f '):
							bits = line.split(' ')
							print('f ', end='', file=f)
							for bit in bits[1:]:
								bits2 = bit.split('/')
								print(int(bits2[0]) + v_offset, end='', file=f)
								if len(bits2) >= 2:
									print('/' + bits2[1], end='', file=f)
								if len(bits2) >= 3:
									print('/' + str(int(bits2[2]) + vn_offset), end='', file=f)
								print(' ', end='', file=f)
							print(file=f)
						elif line.startswith('g '):
							print('o ' + part + '-' + line[2:], file=f)
						elif line.startswith('usemtl '):
							pass
						elif line.startswith('mtllib '):
							pass
						elif line.startswith('# Bounds(mm):'):
							match = re.match(r'# Bounds\(mm\): \(([0-9.-]*),([0-9.-]*),([0-9.-]*)\)-\(([0-9.-]*),([0-9.-]*),([0-9.-]*)\)', line)
							bounds_min = [float(match.group(x+1)) if bounds_min[x] is False else min(bounds_min[x], float(match.group(x+1))) for x in range(3)]
							bounds_max = [float(match.group(x+4)) if bounds_max[x] is False else max(bounds_max[x], float(match.group(x+4))) for x in range(3)]
							print(line, file=f)
						else:
							print(line, file=f)
					v_offset += v_num
					vn_offset += vn_num
			
			print('Parsing OBJ {}'.format(f.name))
			mesh = pywavefront.Wavefront(f.name)
		print('Rendering OBJ')
		self.render_ui = pyglet.window.Window(width=1600, height=900)
		
		bounds_mid = [(bounds_min[x] + bounds_max[x]) / 2 for x in range(3)] # not swapped!
		
		rotation = 0
		scale = 0.01
		
		@self.render_ui.event
		def on_resize(width, height):
			glMatrixMode(GL_PROJECTION)
			glLoadIdentity()
			gluPerspective(45., float(width)/height, 1., 100.)
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
			glClearDepth(0.0) # idk why - see below
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
			glDepthFunc(GL_GREATER) # OpenGL is weird...
			# Omitting glClearDepth(0.0) and using glDepthFunc(GL_LEQUAL) as usual, bits frequently draw back to front, but only from certain angles...
			
			glTranslated(0, 0, -3.0)
			glRotatef(rotation, 0, 1, 0)
			glScalef(scale, scale, scale)
			glTranslated(-bounds_mid[0], -bounds_mid[2], -bounds_mid[1])
			
			mesh.draw()
		@self.render_ui.event
		def on_mouse_drag(x, y, dx, dy, buttons, modifiers):
			nonlocal rotation
			rotation -= dx
		@self.render_ui.event
		def on_mouse_scroll(x, y, scroll_x, scroll_y):
			nonlocal scale
			scale += scroll_y * 0.001
		pyglet.app.run()

#class RenderUI(QOpenGLWidget):
class RenderUI:
	def __init__(self, files):
		super().__init__()
		self.files = files
	
	def paintGL(self):
		glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
		glLoadIdentity()
	
	
		#glTranslatef(-2.5, 0.5, -6.0)
		#glColor3f( 1.0, 1.5, 0.0 );
		#glPolygonMode(GL_FRONT, GL_FILL);
		glScale(0.001, 0.001, 0.001)
	
		#glBegin(GL_TRIANGLES)
		#glVertex3f(2.0,-1.2,0.0)
		#glVertex3f(2.6,0.0,0.0)
		#glVertex3f(2.9,-1.2,0.0)
		#glEnd()
		
		for obj in self.objs:
			glCallList(obj.gl_list)
	
	
		glFlush()
	
	def initializeGL(self):
		glClearDepth(1.0)
		glDepthFunc(GL_LESS)
		glEnable(GL_DEPTH_TEST)
		glShadeModel(GL_SMOOTH)
	
		glMatrixMode(GL_PROJECTION)
		glLoadIdentity()
		gluPerspective(45.0,1.33,0.1, 100.0)
		glMatrixMode(GL_MODELVIEW)
		
		# Load files
		self.objs = []
		for file_name in self.files:
			print('Loading {}'.format(file_name))
			self.objs.append(objloader.OBJ(file_name))

app = QApplication(sys.argv)

w = MainUI()
w.show()
#r = RenderUI()
#r.show()

sys.exit(app.exec_())
