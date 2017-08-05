#!/usr/bin/python3

import json

class FMAClass:
	def __init__(self):
		self.name = None
		self.code = None
		self.parents = []
		#self.children = []
		
		self.added = False
	
	def to_json(self):
		return {'name': self.name, 'parents': self.parents}

classes = {}

with open('data/fma_v4.8.0/fma.owl', 'r') as f:
	for line in f:
		if line.startswith('    <owl:Class rdf:about="http://purl.org/sig/ont/fma/'):
			cls = FMAClass()
			cls.code = line[54:-3].upper()
			
			for line in f:
				if line == '    </owl:Class>\n':
					break
				elif line.startswith('        <rdfs:label xml:lang="en">'):
					cls.name = line[34:-14].lower()
				elif line.startswith('        <rdfs:subClassOf '):
					cls.parents.append(line[67:-4].upper())
				elif line == '        <rdfs:subClassOf>\n':
					for line in f:
						if line == '        </rdfs:subClassOf>\n':
							break
						elif line == '            <owl:Restriction>\n':
							restriction_parent = None
							restriction_type = None
							for line in f:
								if line == '            </owl:Restriction>\n':
									break
								elif line.startswith('                <owl:someValuesFrom '):
									restriction_parent = line[78:-4]
								elif line.startswith('                <owl:onProperty '):
									restriction_type = line[46:-4]
							if (
							#    restriction_type == 'http://purl.org/sig/ont/fma/member_of'
							# or restriction_type == 'http://purl.org/sig/ont/fma/regional_part_of'
							    restriction_type == 'http://purl.org/sig/ont/fma/constitutional_part_of'
							   ):
								if restriction_parent != cls.code:
									cls.parents.append(restriction_parent.upper())
			
			classes[cls.code] = cls

with open('data/fma_v4.8.0.json', 'w') as f:
	json.dump({k: v.to_json() for k, v in classes.items()}, f, indent='\t')
