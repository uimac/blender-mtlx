# -*- coding: utf-8 -*- 
# author: tori31001 at gmail.com

bl_info = {
	"name": "MaterialX Material Export",
	"author": "Kazuma Hatta",
	"version": (0, 0, 1),
	"blender": (2, 7, 7),
	"location": "File > Export > materialx",
	"description": "Export MaterialX Materials(.mtlx)",
	"warning": "",
	"wiki_url": "",
	"tracker_url": "",
	"category": "Import-Export"}

import os
import sys
import bpy
import xml.etree.ElementTree as ET
from xml.dom import minidom
import uuid
import codecs

from bpy.props import (StringProperty,\
						BoolProperty,\
						FloatProperty,\
						EnumProperty,\
						)

from bpy_extras.io_utils import (ImportHelper,\
								ExportHelper,\
								path_reference_mode\
								)

def create_id():
	return str(uuid.uuid1())[0:8]

def get_texture(material):
	textures = []
	for texture_slot in material.texture_slots:
		if texture_slot != None:
			if texture_slot.use:
				textures.append(texture_slot)
	
	if len(textures) > 0:
		texture = textures[0]
		tex = texture.texture
		if tex == None:
			return ""
		if not hasattr(tex, "image"):
			return ""
		img = tex.image
		if img != None:
			return img.filepath.replace("//", "")
	return ""

def create_opgraph(material):
	if material == None:
		return None, None
	tex = get_texture(material)
	if tex == "":
		return None, None
	opgraph = ET.Element("opgraph")
	opgraph.attrib["name"] = "op_" + create_id()
	image = ET.Element("image")
	image.attrib["name"] = "col_" + create_id()
	image.attrib["type"] = "color3"
	param = ET.Element("parameter")
	param.attrib["name"] = "file"
	param.attrib["type"] = "filename"
	param.attrib["value"] = tex
	image.append(param)
	output = ET.Element("output")
	output.attrib["name"] = "out_" + create_id()
	param2 = ET.Element("parameter")
	param2.attrib["name"] = "in_" + create_id()
	param2.attrib["type"] = "opgraphnode"
	param2.attrib["value"] = image.attrib["name"] 
	output.append(param2)
	opgraph.append(image)
	opgraph.append(output)
	return opgraph, output

def create_shader(opgraph, output, material):
	shader = ET.Element("shader")
	shader.attrib["name"] = "sha_" + create_id()
	shader.attrib["shadertype"] = "surface"
	shader.attrib["shaderprogram"] = "basic_surface"
	input = ET.Element("input")
	input.attrib["name"] = "diff_albedo"
	input.attrib["type"] = "color3"
	input.attrib["opgraph"] = opgraph.attrib["name"]
	input.attrib["graphoutput"] = output.attrib["name"]
	shader.append(input)
	return shader

def create_material(shader):
	mat = ET.Element("material")
	mat.attrib["name"] = "mat_" + create_id()
	shaderref = ET.Element("shaderref")
	shaderref.attrib["name"] = shader.attrib["name"]
	mat.append(shaderref)
	return mat

def create_collection(mesh_object):
	collection = ET.Element("collection")
	collection.attrib["name"] = "co_" + create_id()
	cadd = ET.Element("collectionadd")
	cadd.attrib["name"] = "ca_" + create_id()
	objpath = mesh_object.name
	parent = mesh_object.parent
	while (parent != None):
		objpath = mesh_object.parent.name + "/" + objpath
		parent = parent.parent  
	objpath = "/" + objpath
	cadd.attrib["geom"] = objpath
	collection.append(cadd)
	return collection

def create_look(material, collection):
	look = ET.Element("look")
	look.attrib["name"] = "look_" + create_id()
	materialassign = ET.Element("materialassign")
	materialassign.attrib["name"] = material.attrib["name"]
	materialassign.attrib["collection"] = collection.attrib["name"]
	look.append(materialassign)
	return look

def export_material(root, base_path, obj, mesh, context):
	opgraph, output = create_opgraph(obj.active_material)
	if opgraph != None:
		collection = create_collection(obj)
		shader = create_shader(opgraph, output, obj.active_material)
		mat = create_material(shader)
		look = create_look(mat, collection)
		root.append(collection)
		root.append(opgraph)
		root.append(shader)
		root.append(mat)	
		root.append(look)
		return True
	return False

def export_materialx(filepath, context, only_selected):
	image_dict = {}
	mtlDict = {}
	relationDict = {}

	base_path, file_name = os.path.split(filepath)
	mesh_objects = []

	root = ET.Element("materialx")

	if only_selected:
		mesh_objects = [ob for ob in bpy.data.objects if ob.type == 'MESH' and ob.select] 
	else:
		mesh_objects = [ob for ob in bpy.data.objects if ob.type == 'MESH']

	for i, mesh_object in enumerate(mesh_objects):
		# add collection
		export_material(root, base_path, mesh_object, mesh_object.data, context)

	xmlstr = minidom.parseString(ET.tostring(root, encoding="UTF-8")).toprettyxml(indent="   ")
	with codecs.open(filepath, "w", encoding="utf8") as f:
		f.write(xmlstr)

class MaterialXExportOperator(bpy.types.Operator, ExportHelper):
	bl_idname = "export_scene.mtlx"
	bl_label = "MaterialX Exporter(.mtlx)"
	
	filename_ext = ".mtlx"
	fliter_glob = bpy.props.StringProperty(default="*.mtlx")

	filepath = bpy.props.StringProperty(subtype="FILE_PATH")
		
	path_mode = path_reference_mode

	def execute(self, context):
		export_materialx(self.filepath, bpy.context, True)
		return {'FINISHED'}

	def invoke(self, context, event):
		context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}

#
# Registration
#
def menu_func_export(self, context):
	self.layout.operator(MaterialXExportOperator.bl_idname, text="MaterialX Material (.mtlx)")

def register():
	bpy.utils.register_module(__name__)
	bpy.types.INFO_MT_file_export.append(menu_func_export)

def unregister():
	bpy.utils.unregister_module(__name__)
	bpy.types.INFO_MT_file_export.remove(menu_func_export)

if __name__ == "__main__":
	register()
