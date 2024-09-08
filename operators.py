import math
import mathutils
import random

import bmesh
import bpy


class SelectByFaceIDOperator(bpy.types.Operator):
    bl_idname = "mesh.select_by_plasticity_face_id"
    bl_label = "Select by Plasticity Face ID"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.mode != 'EDIT_MESH':
            return False
        obj = context.active_object
        if not obj or not obj.select_get() or obj.type != 'MESH' or "plasticity_id" not in obj.keys():
            return False
        return True

    def execute(self, context):
        obj = context.object
        bpy.ops.object.mode_set(mode='EDIT')

        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)

        groups = mesh["groups"]
        if not groups:
            self.report({'ERROR'}, "No groups found")
            return {'CANCELLED'}

        face_ids = mesh["face_ids"]
        if not face_ids:
            self.report({'ERROR'}, "No face_ids found")
            return {'CANCELLED'}

        # Collect group IDs of all selected faces
        selected_group_ids = set()
        for face in bm.faces:
            if face.select:
                loop_idx = face.loops[0].index
                for i in range(0, len(groups), 2):
                    group_start = groups[i + 0]
                    group_count = groups[i + 1]
                    if loop_idx >= group_start and loop_idx < group_start + group_count:
                        selected_group_ids.add(i)
                        break

        # Select all faces belonging to any of the selected group IDs
        for face in bm.faces:
            loop_start = face.loops[0].index
            for group_id in selected_group_ids:
                group_start = groups[group_id + 0]
                group_count = groups[group_id + 1]
                if loop_start >= group_start and loop_start < group_start + group_count:
                    face.select = True
                    break

        bmesh.update_edit_mesh(mesh)
        return {'FINISHED'}


class SelectByFaceIDEdgeOperator(bpy.types.Operator):
    bl_idname = "mesh.select_by_plasticity_face_id_edge"
    bl_label = "Select by Plasticity Face ID (Edge)"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.mode != 'EDIT_MESH':
            return False
        obj = context.active_object
        if not obj or not obj.select_get() or obj.type != 'MESH' or "plasticity_id" not in obj.keys():
            return False
        return True

    def execute(self, context):
        obj = context.object
        bpy.ops.object.mode_set(mode='EDIT')
        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)
        groups = mesh["groups"]

        if not groups:
            self.report({'ERROR'}, "No groups found")
            return {'CANCELLED'}

        face_ids = mesh["face_ids"]
        if not face_ids:
            self.report({'ERROR'}, "No face_ids found")
            return {'CANCELLED'}

        selected_group_ids = get_selected_group_ids(groups, bm)
        boundary_edges = get_boundary_edges_for_group_ids(
            groups, bm, selected_group_ids)

        # Unselect the faces in selected_group_ids
        for face in bm.faces:
            loop_start = face.loops[0].index
            for group_id in selected_group_ids:
                group_start = groups[group_id + 0]
                group_count = groups[group_id + 1]
                if loop_start >= group_start and loop_start < group_start + group_count:
                    face.select = False
                    break

        # Select the boundary edges
        for edge in boundary_edges:
            edge.select = True

        bmesh.update_edit_mesh(mesh)
        return {'FINISHED'}


class MergeUVSeams(bpy.types.Operator):
    bl_idname = "mesh.merge_uv_seams"
    bl_label = "Merge UV Seams"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.mode != 'EDIT_MESH':
            return False
        obj = context.active_object
        active_poly_index = obj.data.polygons.active
        if active_poly_index is None:
            return False
        return True

    def execute(self, context):
        bpy.ops.mesh.select_linked(delimit={'SEAM'})
        bpy.ops.mesh.mark_seam(clear=True)
        bpy.ops.mesh.region_to_loop()
        bpy.ops.mesh.mark_seam(clear=False)
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.mesh.select_mode(
            use_extend=False, use_expand=False, type='FACE')

        return {'FINISHED'}


class AutoMarkEdgesOperator(bpy.types.Operator):
    bl_idname = "mesh.auto_mark_edges"
    bl_label = "Auto Mark Edges"
    bl_description = "Mark edges as sharp or seams based on the selected faces"
    bl_options = {'REGISTER', 'UNDO'}

    mark_smart: bpy.props.BoolProperty(
        name="Smart Edges Marking", default=False)
    mark_sharp: bpy.props.BoolProperty(name="Mark Sharp", default=True)
    mark_seam: bpy.props.BoolProperty(name="Mark Seam", default=False)

    @classmethod
    def poll(cls, context):
        return (
            any("plasticity_id" in obj.keys() and obj.type ==
                'MESH' for obj in context.selected_objects)
            or (context.mode == 'EDIT_MESH' and context.active_object and "plasticity_id" in context.active_object.keys())
        )

    def execute(self, context):
        prev_obj_mode = bpy.context.object.mode

        if context.mode == 'EDIT_MESH':
            obj = context.active_object
            mesh = obj.data
            bm = bmesh.from_edit_mesh(mesh)
            groups = mesh["groups"]
            selected_group_ids = get_selected_group_ids(groups, bm)
            if len(selected_group_ids) == 0:
                bpy.ops.object.mode_set(mode='OBJECT')
                self.mark_sharp_edges(obj, groups)
                bpy.ops.object.mode_set(mode='EDIT')
            else:
                self.mark_edges_for_selected_faces(context, selected_group_ids)
        else:
            for obj in context.selected_objects:
                if obj.type != 'MESH':
                    continue
                if not "plasticity_id" in obj.keys():
                    continue

                mesh = obj.data
                bpy.ops.object.mode_set(mode='OBJECT')

                if "plasticity_id" not in obj.keys():
                    self.report(
                        {'ERROR'}, "Object doesn't have a plasticity_id attribute.")
                    return {'CANCELLED'}

                groups = mesh["groups"]
                self.mark_sharp_edges(obj, groups)

        bpy.ops.object.mode_set(mode=prev_obj_mode)
        return {'FINISHED'}

    def mark_edges_for_selected_faces(self, context, selected_group_ids):
        obj = context.active_object
        mesh = obj.data
        bm = bmesh.from_edit_mesh(mesh)

        boundary_edges = get_boundary_edges_for_group_ids(
            mesh["groups"], bm, selected_group_ids)

        for edge in boundary_edges:
            if self.mark_sharp:
                edge.smooth = False
            if self.mark_seam:
                edge.seam = True

        bmesh.update_edit_mesh(mesh)

    def mark_sharp_edges(self, obj, groups):
        mesh = obj.data
        bm = bmesh.new()
        #mesh.calc_normals_split()
        bm.from_mesh(mesh)
        bm.edges.ensure_lookup_table()
        bm.verts.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        loops = mesh.loops

        all_face_boundary_edges = face_boundary_edges(groups, mesh, bm)

        split_edges = set()
        if self.mark_smart:
            for vert in bm.verts:
                for edge in vert.link_edges:
                    loops_for_vert_and_edge = []
                    for face in edge.link_faces:
                        for loop in face.loops:
                            if loop.vert == vert:
                                loops_for_vert_and_edge.append(loop)
                    if len(loops_for_vert_and_edge) != 2:
                        continue
                    loop1, loop2 = loops_for_vert_and_edge
                    normal1 = loops[loop1.index].normal
                    normal2 = loops[loop2.index].normal
                    if are_normals_different(normal1, normal2):
                        split_edges.add(edge)

        for edge in all_face_boundary_edges:
            if self.mark_sharp:
                if self.mark_smart and edge in split_edges:
                    edge.smooth = False
                elif not self.mark_smart:
                    edge.smooth = False

            if self.mark_seam:
                if self.mark_smart and edge in split_edges:
                    edge.seam = True
                elif not self.mark_smart:
                    edge.seam = True

        bm.to_mesh(obj.data)
        bm.free()


def face_boundary_edges(groups, mesh, bm):
    all_face_boundary_edges = set()
    face_boundary_edges = set()

    group_idx = 0
    group_start = groups[group_idx * 2 + 0]
    group_count = groups[group_idx * 2 + 1]
    face_boundary_edges = set()

    for poly in mesh.polygons:
        loop_start = poly.loop_start
        if loop_start >= group_start + group_count:
            all_face_boundary_edges.update(face_boundary_edges)
            group_idx += 1
            group_start = groups[group_idx * 2 + 0]
            group_count = groups[group_idx * 2 + 1]
            face_boundary_edges = set()

        face = bm.faces[poly.index]
        for edge in face.edges:
            if edge in face_boundary_edges:
                face_boundary_edges.remove(edge)
            else:
                face_boundary_edges.add(edge)
    all_face_boundary_edges.update(face_boundary_edges)

    return all_face_boundary_edges


def get_boundary_edges_for_group_ids(groups, bm, selected_group_ids):
    boundary_edges = set()
    for face in bm.faces:
        loop_start = face.loops[0].index
        for group_id in selected_group_ids:
            group_start = groups[group_id + 0]
            group_count = groups[group_id + 1]
            if loop_start >= group_start and loop_start < group_start + group_count:
                for edge in face.edges:
                    if edge in boundary_edges:
                        boundary_edges.remove(edge)
                    else:
                        boundary_edges.add(edge)
                break
    return boundary_edges


def get_selected_group_ids(groups, bm):
    selected_group_ids = set()
    for face in bm.faces:
        if face.select:
            loop_idx = face.loops[0].index
            for i in range(0, len(groups), 2):
                group_start = groups[i + 0]
                group_count = groups[i + 1]
                if loop_idx >= group_start and loop_idx < group_start + group_count:
                    selected_group_ids.add(i)
                    break
    return selected_group_ids


class PaintPlasticityFacesOperator(bpy.types.Operator):
    bl_idname = "mesh.paint_plasticity_faces"
    bl_label = "Paint Plasticity Faces"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return any("plasticity_id" in obj.keys() and obj.type == 'MESH' for obj in context.selected_objects)

    def execute(self, context):
        prev_obj_mode = bpy.context.mode

        for obj in context.selected_objects:
            if obj.type != 'MESH':
                continue
            if not "plasticity_id" in obj.keys():
                continue
            mesh = obj.data

            if "plasticity_id" not in obj.keys():
                self.report(
                    {'ERROR'}, "Object doesn't have a plasticity_id attribute.")
                return {'CANCELLED'}

            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='OBJECT')

            self.colorize_mesh(obj, mesh)

            mat = bpy.data.materials.new(name="VertexColorMat")
            mat.use_nodes = True
            nodes = mat.node_tree.nodes

            for node in nodes:
                nodes.remove(node)

            vertex_color_node = nodes.new(type='ShaderNodeVertexColor')
            shader_node = nodes.new(type='ShaderNodeBsdfPrincipled')
            shader_node.location = (400, 0)
            mat.node_tree.links.new(
                shader_node.inputs['Base Color'], vertex_color_node.outputs['Color'])

            material_output = nodes.new(type='ShaderNodeOutputMaterial')
            material_output.location = (800, 0)
            mat.node_tree.links.new(
                material_output.inputs['Surface'], shader_node.outputs['BSDF'])

            if obj.data.materials:
                obj.data.materials[0] = mat
            else:
                obj.data.materials.append(mat)

        bpy.ops.object.mode_set(mode=map_mode(prev_obj_mode))

        return {'FINISHED'}

    def colorize_mesh(self, obj, mesh):
        groups = mesh["groups"]
        face_ids = mesh["face_ids"]

        if len(groups) == 0:
            return
        if len(face_ids) * 2 != len(groups):
            return

        if not mesh.vertex_colors:
            mesh.vertex_colors.new()
        color_layer = mesh.vertex_colors.active

        group_idx = 0
        group_start = groups[group_idx * 2 + 0]
        group_count = groups[group_idx * 2 + 1]
        face_id = face_ids[group_idx]
        color = generate_random_color(face_id)

        for poly in mesh.polygons:
            loop_start = poly.loop_start
            if loop_start >= group_start + group_count:
                group_idx += 1
                group_start = groups[group_idx * 2 + 0]
                group_count = groups[group_idx * 2 + 1]
                face_id = face_ids[group_idx]
                color = generate_random_color(face_id)
            for loop_index in range(loop_start, loop_start + poly.loop_total):
                color_layer.data[loop_index].color = color

class NonOverlappingMeshesMerger(bpy.types.Operator):
    bl_idname = "object.merge_nonoverlapping_meshes"
    bl_label = "Merge Non-overlapping Meshes"
    bl_options = {'REGISTER', 'UNDO'}

    def check_overlap(self, obj1, obj2, overlap_threshold):
        bm1 = bmesh.new()
        bm1.from_mesh(obj1.data)
        bm1.transform(obj1.matrix_world)

        tree1 = mathutils.kdtree.KDTree(len(bm1.verts))
        for i, v in enumerate(bm1.verts):
            tree1.insert(v.co, i)
        tree1.balance()

        bm2 = bmesh.new()
        bm2.from_mesh(obj2.data)
        bm2.transform(obj2.matrix_world)

        for v in bm2.verts:
            co, index, dist = tree1.find(v.co)
            if dist < overlap_threshold:
                return True

        return False

    def merge_meshes(self, obj1, obj2):
        bpy.ops.object.select_all(action='DESELECT') 
        obj1.select_set(True)
        obj2.select_set(True)
        bpy.context.view_layer.objects.active = obj1
        bpy.ops.object.join()

    def execute(self, context):
        overlap_threshold = context.scene.overlap_threshold

        merged = True

        while merged:
            visible_mesh_objects = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH' and obj.visible_get()]
            non_overlapping_pairs = [(visible_mesh_objects[i], visible_mesh_objects[j]) for i in range(len(visible_mesh_objects)) for j in range(i + 1, len(visible_mesh_objects)) if not self.check_overlap(visible_mesh_objects[i], visible_mesh_objects[j], overlap_threshold)]

            merged = set()
            merge_occurred = False

            for pair in non_overlapping_pairs:
                obj1, obj2 = pair
                if obj1 not in merged and obj2 not in merged:
                    self.merge_meshes(obj1, obj2)
                    merged.add(obj1)
                    merged.add(obj2)
                    merge_occurred = True

            merged = merge_occurred

        return {'FINISHED'}

class SimilarGeometrySelector(bpy.types.Operator):
    bl_idname = "object.select_similar_geometry"
    bl_label = "Select Similar Geometry"
    bl_options = {'REGISTER', 'UNDO'}
    
    similarity_threshold: bpy.props.FloatProperty(
        name="Similarity Threshold",
        description="Percentage difference between objects to consider them similar",
        default=0.2,  # Default 20% difference allowed
        min=0,
        max=1
    )

    def execute(self, context):
        active_object = context.active_object
        if active_object and active_object.type == 'MESH':
            active_vert_count = len(active_object.data.vertices)
            active_poly_count = len(active_object.data.polygons)
            
            # Calculate total surface area for the active object
            active_surface_area = sum(poly.area for poly in active_object.data.polygons)

            for obj in bpy.context.scene.objects:
                if obj.type == 'MESH':
                    vert_count = len(obj.data.vertices)
                    poly_count = len(obj.data.polygons)
                    
                    # Calculate total surface area for the current object
                    surface_area = sum(poly.area for poly in obj.data.polygons)
                    
                    # Calculate percentage difference for vertices, polygons and surface area
                    vert_diff = abs(vert_count - active_vert_count) / active_vert_count
                    poly_diff = abs(poly_count - active_poly_count) / active_poly_count
                    area_diff = abs(surface_area - active_surface_area) / active_surface_area

                    # If all differences are within the threshold, select the object
                    if vert_diff <= self.similarity_threshold and poly_diff <= self.similarity_threshold and area_diff <= self.similarity_threshold:
                        obj.select_set(True)

        return {'FINISHED'}

class SelectedJoiner(bpy.types.Operator):
    bl_idname = "object.join_selected"
    bl_label = "Join Selected"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        bpy.ops.object.join()
        
        return {'FINISHED'}

class SelectedUnjoiner(bpy.types.Operator):
    bl_idname = "object.unjoin_selected"
    bl_label = "Unjoin Selected"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        original_objects = context.selected_objects
        for obj in original_objects:
            context.view_layer.objects.active = obj
            bpy.ops.object.mode_set(mode='EDIT')
            bpy.ops.mesh.select_all(action='SELECT')
            bpy.ops.mesh.separate(type='LOOSE')
            bpy.ops.object.mode_set(mode='OBJECT')

            temp_name = obj.name + "_temp_unique_name"
            for new_obj in context.selected_objects:
                if new_obj not in original_objects: 
                    new_obj.name = temp_name

        for obj in bpy.data.objects:
            if obj.name.startswith(temp_name):
                obj.name = obj.name.replace(temp_name, "")

        return {'FINISHED'}    

class OpenUVEditorOperator(bpy.types.Operator):
    bl_idname = "object.open_uv_editor"
    bl_label = "Open UV Editor"
    bl_options = {'REGISTER'}

    def execute(self, context):
        original_resolution_x = context.scene.render.resolution_x
        original_resolution_y = context.scene.render.resolution_y
        original_resolution_percentage = context.scene.render.resolution_percentage

        context.scene.render.resolution_x = 800
        context.scene.render.resolution_y = 600
        context.scene.render.resolution_percentage = 100

        original_display_type = context.preferences.view.render_display_type
        context.preferences.view.render_display_type = 'WINDOW'

        if context.selected_objects:
            for obj in context.selected_objects:
                if obj.type == 'MESH':
                    context.view_layer.objects.active = obj
                    bpy.ops.object.mode_set(mode='EDIT')
                    bpy.ops.mesh.select_all(action='SELECT')

        bpy.ops.render.view_show('INVOKE_DEFAULT')

        context.scene.render.resolution_x = original_resolution_x
        context.scene.render.resolution_y = original_resolution_y
        context.scene.render.resolution_percentage = original_resolution_percentage

        context.preferences.view.render_display_type = original_display_type

        new_window = context.window_manager.windows[-1]
        new_area = new_window.screen.areas[0]
        new_area.type = 'IMAGE_EDITOR'
        new_area.spaces.active.mode = 'UV'

        new_area.spaces.active.image = None
        
        return {'FINISHED'}

def are_normals_different(normal_a, normal_b, threshold_angle_degrees=5.0):
    threshold_cosine = math.cos(math.radians(threshold_angle_degrees))
    dot_product = normal_a.dot(normal_b)
    return dot_product < threshold_cosine


def generate_random_color(face_id):
    return (random.random(), random.random(), random.random(), 1.0)  # RGBA


mode_map = {
    'EDIT_MESH': 'EDIT',
    'EDIT_CURVE': 'EDIT',
    'EDIT_SURFACE': 'EDIT',
    'EDIT_TEXT': 'EDIT',
    'EDIT_ARMATURE': 'EDIT',
    'EDIT_METABALL': 'EDIT',
    'EDIT_LATTICE': 'EDIT',
    'POSE': 'EDIT',
}


def map_mode(context_mode):
    return mode_map.get(context_mode, context_mode)
