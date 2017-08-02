class ComponentItem:
	component_items = {}
	
	def __init__(self, code, name, parents=None, children=None, items=None):
		# Data
		self.code = code
		self.name = name
		self.parents = [] if parents is None else parents
		self.children = [] if children is None else children
		
		# Internal
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
			       )
		if organ_type == 'cartilage':
			return (self.is_child(ComponentItem.component_items['FMA55107']) # cartilage organ
			     or self.is_child(ComponentItem.component_items['FMA7538']) # cartilage organ component
			       )
	
	@staticmethod
	def load_component_items():
		def do_file(f):
			next(f) # skip header
			for line in f:
				bits = line.rstrip('\n').split('\t')
				if bits[0] not in ComponentItem.component_items:
					ComponentItem.component_items[bits[0]] = ComponentItem(bits[0], bits[1])
				if bits[2] not in ComponentItem.component_items:
					ComponentItem.component_items[bits[2]] = ComponentItem(bits[2], bits[3])
				ComponentItem.component_items[bits[0]].children.append(ComponentItem.component_items[bits[2]])
				ComponentItem.component_items[bits[2]].parents.append(ComponentItem.component_items[bits[0]])
		with open('data/isa_inclusion_relation_list.txt', 'r') as f:
			do_file(f)
		with open('data/partof_inclusion_relation_list.txt', 'r') as f:
			do_file(f)
	
	@staticmethod
	def walk_tree(callback):
		def do_walk_tree(parent_loc, child):
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
