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

WIDTH = 1200
HEIGHT = 675
FOV = 30

from . import model

from PyQt5.QtCore import Qt, QTimer

import pyglet
from pyglet.gl import *
import pywavefront

lightfv = pyglet.gl.GLfloat * 4

class Renderer:
	def __init__(self, main_ui):
		self.main_ui = main_ui
		
		self.wavefronts = {} # loc/part -> Wavefront
		self.parts_to_render = set()
		
		self.bounds_min = [False, False, False]
		self.bounds_max = [False, False, False]
		self.bounds_mid = None
		
		self.render_ui = None
		self.render_timer = QTimer(self.main_ui)
	
	def set_locs(self, locs):
		components = {x[-1]: x for x in locs} # code -> loc
		
		# Resolve parts
		self.parts_to_render = set()
		def do_file(f, prefix):
			next(f) # skip header
			for line in f:
				bits = line.rstrip('\n').split('\t')
				if bits[0] in components:
					#if parent in components[bits[0]]:
						self.parts_to_render.add((components[bits[0]], bits[2], 'data/bp3d_20130619/' + prefix + '_BP3D_4.0_obj_99/' + bits[2] + '.obj')) # TODO: stop passing these things around like crazy
		with open('data/bp3d_20130619/isa_element_parts.txt', 'r') as f:
			do_file(f, 'isa')
		with open('data/bp3d_20130619/partof_element_parts.txt', 'r') as f:
			do_file(f, 'partof')
		# TODO: remove dependence on magic numbers
		
		# Count number of OBJs to load
		to_load = set()
		for loc, part, file_name in self.parts_to_render:
			if (loc + (part,)) not in self.wavefronts:
				to_load.add(loc + (part,))
		return len(to_load)
	
	def load_objs(self, callback):
		# Build OBJ
		print('Processing OBJs')
		self.bounds_min = [False, False, False]
		self.bounds_max = [False, False, False]
		num_loaded = 0 # cache misses only
		for loc, part, file_name in self.parts_to_render:
			if (loc + (part,)) not in self.wavefronts:
				print('Parsing OBJ {}'.format(file_name))
				wavefront = pywavefront.Wavefront(file_name, parse_materials=False, swap_yz=True)
				for mesh in wavefront.mesh_list:
					for material in mesh.materials:
						if model.ComponentItem.component_items[loc[-1]].is_type('bone'):
							material.set_diffuse([227/255, 218/255, 201/255, 1])
						elif model.ComponentItem.component_items[loc[-1]].is_type('muscle'):
							material.set_diffuse([169/255, 17/255, 1/255, 1])
				self.wavefronts[loc + (part,)] = wavefront
				num_loaded += 1
				callback(num_loaded)
			else:
				#print('Cached OBJ {}'.format(file_name))
				wavefront = self.wavefronts[loc + (part,)]
			self.bounds_min = [wavefront.bounds_min[i] if self.bounds_min[i] is False else min(self.bounds_min[i], wavefront.bounds_min[i]) for i in range(3)]
			self.bounds_max = [wavefront.bounds_max[i] if self.bounds_max[i] is False else max(self.bounds_max[i], wavefront.bounds_max[i]) for i in range(3)]
			self.bounds_mid = [(self.bounds_min[x] + self.bounds_max[x]) / 2 for x in range(3)]
	
	def render(self):
		print('Rendering {} OBJs'.format(len(self.parts_to_render)))
		
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
				if not self.bounds_mid:
					return
				
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
				
				for loc, part, _ in self.parts_to_render:
					if loc + (part,) in self.wavefronts:
						self.wavefronts[loc + (part,)].draw()
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
			
			def on_timer_timeout():
				# Supplant event loop
				pyglet.clock.tick()
				for window in pyglet.app.windows:
					window.switch_to()
					window.dispatch_events()
					window.dispatch_event('on_draw')
					window.flip()
			self.render_timer.timeout.connect(on_timer_timeout)
		self.render_timer.start(0)
		#else:
		#	#self.render_timer.setInterval(0)
		#	
