# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

"""
This script exports Volition POF files from Blender.

Usage:
Run this script from "File->Export" menu and then save the desired POF file.

http://code.google.com/p/blender-pof-support/wiki/ExportScript
"""


import os
import time
import bpy
import bmesh
import mathutils
from collections import OrderedDict
from bpy_extras.io_utils import unpack_list, unpack_face_list
from . import pof


def create_mesh(bm, fore_is_y, bmats):
    """Takes a Blender mesh and returns a Volition mesh."""
    # Mesh will be added to SOBJ chunk somewhere else
    bm.calc_tessface()
    m = pof.Mesh()
    verts = list()
    vnorms = list()
    vnorms_by_vert = list()
    for v in bm.vertices:
        co = tuple(v.co)
        vn = tuple(v.normal)
        if co not in verts:
            verts.append(co)
            vnorms_by_vert.append(list())
        if vn not in vnorms:
            vnorms.append(vn)
            vnorms_by_vert[verts.index(co)].append(len(vnorms) - 1)

    # creating the face list might be slow, have to do a lot of index()'ing
    faces = list()
    fvnorms = list()
    centers = list()
    tex_ids = list()
    fnorms = list()
    for f in bm.polygons:
        this_face = list()
        these_norms = list()
        these_verts = list()
        for v in f.vertices:
            this_coord = tuple(bm.vertices[v].co)
            these_verts.append(this_coord)
            this_norm = tuple(bm.vertices[v].normal)
            this_vert = verts.index(this_coord)
            this_face.append(this_vert)
            these_norms.append(vnorms.index(this_norm))
        faces.append(this_face)
        fvnorms.append(these_norms)
        centers.append(pof.vavg(these_verts)) 
        # in case not all mats are linked to mesh:
        if bmats is not None and len(bm.materials) > 0:
            tex_ids.append(bmats.index(bm.materials[f.material_index].name))
        fnorms.append(tuple(f.normal))

    if bmats is not None and len(bm.tessface_uv_textures) > 0:
        uvtex = bm.tessface_uv_textures[0]
        uv = list()
        for i, tf in enumerate(uvtex.data):
            if len(faces[i]) == 3:
                uv.append([tf.uv1, tf.uv2, tf.uv3])
            else:
                uv.append([tf.uv1, tf.uv2, tf.uv3, tf.uv4])
        m.uv = uv
        m.flip_v()

    m.verts = verts
    m.vnorms = vnorms
    m.vnorms_by_vert = vnorms_by_vert
    m.faces = faces
    m.fvnorms = fvnorms
    m.centers = centers
    m.tex_ids = tex_ids
    m.fnorms = fnorms

    if fore_is_y:
        m.flip_yz()

    return m


def make_sobj_chunk(obj):
    this_chunk = pof.ModelChunk()
    this_chunk.name = obj.name
    if 'POF properties' in obj.values():
        this_chunk.properties = obj['POF properties']
    else:
        this_chunk.properties = ''
    if 'POF movement type' in obj.values():
        this_chunk.movement_type = obj['POF movement type']
    else:
        this_chunk.movement_type = -1
    if 'POF movement axis' in obj.values():
        this_chunk.movement_axis = obj['POF movement axis']
    else:
        this_chunk.movement_axis = -1
    
    return this_chunk


def make_eye_chunk(eye_objs, fore_is_y, submodels):
    this_chunk = pof.EyeChunk()
    this_chunk.num_eyes = len(eye_objs)
    
    eye_sobj_nums = list()
    eye_offsets = list()
    eye_normals = list()
    for eye in eye_objs:
        eye_sobj_nums.append(submodels.index(eye.parent)
        loc = eye.location
        if fore_is_y:
            loc = (loc[0], loc[2], loc[1])
            znorm = mathutils.Vector((0,0,1))
        else:
            znorm = mathutils.Vector((0,1,0))
        eye_offsets.append(loc)
        this_norm = znorm.rotate(eye.rotation_quaternion).normalize()
        if fore_is_y:
            eye_normals.append(this_norm.xzy)
        else:
            eye_normals.append(this_norm)
    
    this_chunk.sobj_num = eye_sobj_nums
    this_chunk.eye_offset = eye_offsets
    this_chunk.eye_normal = eye_normals
    
    return this_chunk
    
    
def make_thrust_chunk(thruster_objs):
    pass
    
    
def make_path_chunk(path_objs):
    pass
    
    
def make_dock_chunk(dock_objs):
    pass
    
    
def make_gun_chunk(gun_objs, type='GPNT'):
    pass
    
    
def make_tgun_chunk(gun_objs, type='TGUN'):
    pass
    
    
def make_acen_chunk(acen_obj):
    pass


def make_hdr_chunk(scene, detail_list, debris_list, mass_ctr, flash_objs):
    hdr_chunk = pof.HeaderChunk()
    hdr_chunk.obj_flags = 0
    
    hdr_chunk.num_detail_levels = len(detail_list)
    sobj_detail_levels = list()
    for i, obj in enumerate(detail_list):
        if 'POF model ID' in obj.values():
            sobj_detail_levels.append(obj['POF model ID'])
        else:
            sobj_detail_levels.append(i)
    
    hdr_chunk.sobj_detail_levels = sobj_detail_levels
    hdr_chunk.num_debris = len(debris_list)
    sobj_debris = list()
    for i, obj in enumerate(debris_list):
        if 'POF model ID' in obj.values():
            sobj_debris.append(obj['POF model ID'])
        else:
            sobj_debris.append(i)
    hdr_chunk.sobj_debris = sobj_debris
    
    if 'Mass' in scene.values():
        hdr_chunk.mass = scene['Mass']
    else:
        hdr_chunk.mass = 1000    #sensible default?
        
    if ('Inertia-0' in scene.values() and 
        'Inertia-1' in scene.values() and 
        'Inertia-2' in scene.values()):
        hdr_chunk.inertia_tensor = [scene['Inertia-0'], scene['Inertia-1'], scene['Inertia-2']]
    else:
        hdr_chunk.inertia_tensor = [[0,0,0] * 3]
        
    if mass_ctr is not None:
        hdr_chunk.mass_center = mass_ctr.location
    else:
        hdr_chunk.mass_center = (0,0,0)
        
    hdr_chunk.num_cross_sections = 0
    hdr_chunk.cross_section_depth = []
    hdr_chunk.cross_section_radius = []
    
    hdr_chunk.num_lights = len(flash_objs)
    hdr_chunk.light_locations = list()
    hdr_chunk.light_types = list()
    for obj in flash_objs:
        hdr_chunk.light_locations.append(obj.location)
        if 'Muzzleflash type' in obj.values():
            hdr_chunk.light_types.append(obj['Muzzleflash type'])
        else:
            hdr_chunk.light_types.append(0)
    
    return hdr_chunk


def export(operator, context, filepath,
            export_header_data=True,
            export_acen=True,
            fore_is_y=True,
            export_subobjects=True,
            export_geometry=True,
            export_textures=True,
            export_eye_points=True,
            export_thruster_points=True,
            export_glow_points=True,
            export_special_points=True,
            export_paths=True,
            export_dock_points=True,
            export_gun_points=True,
            export_mis_points=True,
            export_tgun_points=True,
            export_tmis_points=True,
            export_flash_points=True,
            ):
    
    filepath = os.fsencode(filepath)
    if not os.path.isfile(filepath):
        # file doesn't already exist, export everything
        print("File doesn't already exist.  Ignoring export options and exporting everything.")
        export_header_data = True
        export_acen = True
        export_subobjects=True
        export_geometry=True
        export_textures=True
        export_eye_points=True
        export_thruster_points=True
        export_glow_points=True
        export_special_points=True
        export_paths=True
        export_dock_points=True
        export_gun_points=True
        export_mis_points=True
        export_tgun_points=True
        export_tmis_points=True
        export_flash_points=True
        pof_handler = None
    else:
        print("File already exists, opening for update: " + filepath)
        cur_time = time.time()
        pof_file = open(filepath, 'rb')
        pof_handler = pof.read_pof(pof_file)
        pof_file.close()
        new_time = time.time()
        print("\ttime to load POF handler {} sec".format(new_time - cur_time))
        
    if export_subobjects:
        export_textures = True

    scene = context.scene
    
    eye_objs = list()
    thruster_objs = list()
    glow_objs = list()
    special_objs = list()
    path_objs = list()
    dock_objs = list()
    gun_objs = list()
    mis_objs = list()
    tgun_objs = list()
    tmis_objs = list()
    flash_objs = list()
    submodels = list()
    acen_obj = None
    mass_ctr = None
    chunk_list = list()
    submodel_chunks = list()
    bmats = list()
    
    lods = list()
    debris = list()
    others = list()
    insigs = list()
    shield = None
    
    print("Beginning export...")
    for obj in scene.objects:
        # go through all objects in scene and assign to lists by name
        name = obj.name.lower()
        helper = obj.type == 'EMPTY'
        if name.startswith('eye') and helper:
            print("Found eye: " + obj.name)
            eye_objs.append(obj)
        elif name.startswith('thrust') and helper:
            print("Found thruster: " + obj.name)
            thruster_objs.append(obj)
        elif name.startswith('path') and helper:
            print("Found path: " + obj.name)
            path_objs.append(obj)
        elif name.startswith('dock') and helper:
            print("Found dock: " + obj.name)
            dock_objs.append(obj)
        elif name.startswith('gun') and helper:
            print("Found gun: " + obj.name)
            gun_objs.append(obj)
        elif name.startswith('mis') and helper:
            print("Found missile: " + obj.name)
            mis_objs.append(obj)
        elif name.startswith('tgun') and helper:
            print("Found turret gun: " + obj.name)
            tgun_objs.append(obj)
        elif name.startswith('tmis') and helper:
            print("Found turret missile: " + obj.name)
            tmis_objs.append(obj)
        elif name.startswith('flash') and helper:
            print("Found flash point: " + obj.name)
            flash_objs.append(obj)
        elif name == 'acen' and helper:
            print("Found autocenter point.")
            acen_obj = obj
        elif name == 'center-mass' and helper:
            print("Found center of mass.")
            mass_ctr = obj
        elif obj.type == 'MESH':
            print("Found submodel: " + obj.name)
            submodels.append(obj)
            
    if export_textures:
        for mat in bpy.data.materials:
            bmats.append(mat.name)
        txtr_chunk = pof.TextureChunk()
        txtr_chunk.textures = bmats
        chunk_list.append(txtr_chunk)
            
    for obj in submodels:
        name = obj.name.lower()
        if 'detail' in name:
            lods.append(obj)
        elif 'debris' in name:
            debris.append(obj)
        elif 'insig' in name:
            insigs.append(obj)
        elif name == 'shield':
            shield = obj
        else:
            others.append(obj)
    
    if export_header_data:
        chunk_list.append(make_hdr_chunk(scene, lods, debris, mass_ctr, flash_objs))

    # if header data, get counts for detail and debris
    # if subobjects and not geometry, get chunks from pof_handler
    # if geometry, make new chunks
    if export_subobjects:    
        all_submodels = submodels
        submodels = lods + debris + others
        if export_geometry:
            if shield is not None:
                shield_chunk = pof.ShieldChunk()
                shield_mesh = create_mesh(shield.data, fore_is_y, None)
                shield_chunk.set_mesh(shield_mesh)
                chunk_list.append(shield_chunk)
            for i, obj in enumerate(submodels):
                mesh = create_mesh(obj.data, fore_is_y, bmats)
                #mesh.obj_ctr = obj.location
                this_chunk = make_sobj_chunk(obj)
                if obj.parent is not None:
                    this_chunk.parent_id = submodels.index(obj.parent)
                else:
                    this_chunk.parent_id = -1
                this_chunk.offset = obj.location    # fore is y?
                if 'POF model ID' in obj.values():
                    this_chunk.model_id = obj['POF model ID']
                else:
                    this_chunk.model_id = i
                this_chunk.set_mesh(mesh)
                submodel_chunks.append(this_chunk)
        else:
            for i, obj in enumerate(submodels):
                this_chunk = make_sobj_chunk(obj)
                if 'POF model ID' in obj.values():
                    this_chunk.model_id = obj['POF model ID']
                else:
                    this_chunk.model_id = i
                this_chunk.bsp_tree = None
                submodel_chunks.append(this_chunk)
    
    if export_eye_points:
        eye_chunk = make_eye_chunk(eye_objs, fore_is_y, submodels)
        chunk_list.append(eye_chunk)
    
    if pof_handler is None:
        pof_handler = pof.PolyModel(chunk_list + submodel_chunks)
    else:
        pof_handler.update_pof(chunk_list, submodel_chunks)
    pof_data = pof.write_pof(pof_handler)
    pof_file = open(filepath, 'wb')
    pof_file.write(pof_data)
    pof_file.close
    
    return {'FINISHED'}