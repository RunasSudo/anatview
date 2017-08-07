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

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItem

import json
import os

class ComponentItem:
	component_items = {}
	
	def __init__(self, code, name, parents=None, children=None, items=None):
		# Data
		self.code = code
		self.name = name
		self.parents = [] if parents is None else parents
		self.children = [] if children is None else children
		
		# Internal
		self.parts = None
		self.items = {} if items is None else items # loc -> item
		self.list_item = None
	
	def is_child(self, parent):
		if self == parent:
			return True
		for part_parent in self.parents:
			if part_parent.is_child(parent):
				return True
		return False
	
	def is_type(self, organ_type):
		if organ_type == 'bone':
			return (self.is_child(ComponentItem.component_items['FMA5018']) # bone organ
			     or self.is_child(ComponentItem.component_items['FMA71324']) # set of bone organs
			       )
		if organ_type == 'muscle':
			return (self.is_child(ComponentItem.component_items['FMA5022']) # muscle organ
			     or self.is_child(ComponentItem.component_items['FMA10474']) # zone of muscle organ
			     or self.is_child(ComponentItem.component_items['FMA32555']) # zone of ascending trapezius
			     or self.is_child(ComponentItem.component_items['FMA32557']) # zone of descending trapezius
			     or self.is_child(ComponentItem.component_items['FMA79979']) # sternocostal part of right pectoralis major (???)
			       )
		if organ_type == 'cartilage':
			return (self.is_child(ComponentItem.component_items['FMA55107']) # cartilage organ
			     or self.is_child(ComponentItem.component_items['FMA7538']) # cartilage organ component
			       )
	
	def make_list_item(self, checked):
		check_item = QStandardItem()
		check_item.setCheckable(True)
		check_item.setEnabled(self.parts is not None)
		check_item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
		
		self.list_item = [QStandardItem(self.code), QStandardItem(self.name), check_item]
		return self.list_item
	
	@staticmethod
	def load_component_items():
		# Read FMA data
		with open('data/fma_v4.8.0.json', 'r') as f:
			fma_data = json.load(f)
		for code, json_component in fma_data.items():
			ComponentItem.component_items[code] = ComponentItem(code, json_component['name'])
		for code, json_component in fma_data.items():
			for parent_code in json_component['parents']:
				if parent_code in ComponentItem.component_items:
					#if ComponentItem.component_items[parent_code].is_child(ComponentItem.component_items[code]):
					#	# About to add a circular reference
					#	pass
					#else:
						ComponentItem.component_items[code].parents.append(ComponentItem.component_items[parent_code])
						ComponentItem.component_items[parent_code].children.append(ComponentItem.component_items[code])
				else:
					print('Warning: No FMA data for parent {}'.format(parent_code))
		
		# Ascertain whether renderable
		for loader in LOADERS:
			loader.load()
	
	@staticmethod
	def walk_tree(callback):
		def do_walk_tree(parent_loc, child):
			if child.code in parent_loc:
				# Prevent infinite loops from circular references
				return None
			res = callback(parent_loc + (child.code,), child)
			if res is not None:
				return res
			for subchild in child.children:
				res = do_walk_tree(parent_loc + (child.code,), subchild)
				if res is not None:
					return res
			return None
		
		for k, v in ComponentItem.component_items.items():
			if len(v.parents) == 0:
				res = do_walk_tree((), v)
				if res is not None:
					return res
		return None
	
	@staticmethod
	def item_by_loc(loc):
		return ComponentItem.component_items[loc[-1]].items[loc]

class ComponentLoader:
	def mark_renderable(self, component):
		if component.parts is not None:
			return
		component.parts = set()
		for parent in component.parents:
			self.mark_renderable(parent)

# Loads components from a BP3D official archive
class BP3DArchiveLoader(ComponentLoader):
	def __init__(self, directory, tree_type):
		self.directory = directory
		self.tree_type = tree_type
	
	def load(self):
		with open(self.directory + '/' + self.tree_type + '_element_parts.txt', 'r') as f:
			next(f) # skip header
			for line in f:
				bits = line.rstrip('\n').split('\t')
				if bits[0] in ComponentItem.component_items:
					self.mark_renderable(ComponentItem.component_items[bits[0]])
					ComponentItem.component_items[bits[0]].parts.add((bits[2], self.directory + '/' + self.tree_type + '_BP3D_4.0_obj_99/' + bits[2] + '.obj'))
				else:
					print('Warning: No FMA data for wavefront {}'.format(bits[0]))

# Loads components manually downloaded from BP3D/Anatomography
class BP3DObjLoader(ComponentLoader):
	def __init__(self, directory):
		self.directory = directory
	
	def load(self):
		for f in os.listdir(self.directory):
			bits = f.split('_')
			if bits[2] in ComponentItem.component_items:
				self.mark_renderable(ComponentItem.component_items[bits[2]])
				ComponentItem.component_items[bits[2]].parts.add((bits[0], self.directory + '/' + f))
			else:
				print('Warning: No FMA data for wavefront {}'.format(bits[2]))

LOADERS = [
	BP3DArchiveLoader('data/bp3d_20130619', 'isa'),
	BP3DArchiveLoader('data/bp3d_20130619', 'partof'),
	BP3DObjLoader('data/bp3d_obj_20161017i4')
]
