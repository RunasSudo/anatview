from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItem

import yaml
import json

class ComponentItem:
	component_items = {}
	
	def __init__(self, code, name, parents=None, children=None, items=None):
		# Data
		self.code = code
		self.name = name
		self.parents = [] if parents is None else parents
		self.children = [] if children is None else children
		
		# Internal
		self.can_render = False
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
			return self.is_child(ComponentItem.component_items['FMA5018']) # bone organ
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
		check_item.setEnabled(self.can_render)
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
		
		# Sanity check
		#def walk_item(component, seen=[]):
		#	if component in seen:
		#		print('!! Loop with {}'.format(component.code))
		#		print(' > '.join([x.code for x in seen]))
		#		sys.exit(1)
		#	for parent in component.parents:
		#		walk_item(parent, seen + [component])
		#for code, component in ComponentItem.component_items.items():
		#	walk_item(component)
		
		# Ascertain whether renderable
		def do_file(f):
			def mark_renderable(component):
				if component.can_render:
					return
				component.can_render = True
				for parent in component.parents:
					mark_renderable(parent)
			
			next(f) # skip header
			for line in f:
				bits = line.rstrip('\n').split('\t')
				if bits[0] in ComponentItem.component_items:
					mark_renderable(ComponentItem.component_items[bits[0]])
				else:
					print('Warning: No FMA data for wavefront {}'.format(bits[0]))
		with open('data/bp3d_20130619/isa_element_parts.txt', 'r') as f:
			do_file(f)
		with open('data/bp3d_20130619/partof_element_parts.txt', 'r') as f:
			do_file(f)
	
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
