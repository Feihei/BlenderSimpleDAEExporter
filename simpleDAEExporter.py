bl_info = {
    "name": "Simple Collada DAE Exporter",
    "author": "Feihei & AI",
    "version": (0, 1, 0),
    "blender": (5, 0, 0),
    "location": "File > Export",
    "description": "Export selected meshes to Collada DAE format",
    "category": "Import-Export",
}

import bpy
import bmesh
import os
import xml.etree.ElementTree as ET
from xml.dom import minidom
from bpy_extras.io_utils import ExportHelper
from bpy.props import BoolProperty, StringProperty, EnumProperty
from bpy.types import Operator
from mathutils import Matrix


class DAEExporter(Operator, ExportHelper):
    bl_idname = "export_scene.simple_dae"
    bl_label = "Export DAE (Simple)"
    bl_options = {'PRESET'}

    filename_ext = ".dae"
    filter_glob: StringProperty(default="*.dae", options={'HIDDEN'})

    use_selection: BoolProperty(
        name="Selection Only",
        description="Export selected objects only",
        default=True,
    )

    apply_modifiers: BoolProperty(
        name="Apply Modifiers",
        description="Apply modifiers before exporting",
        default=True,
    )

    export_materials: BoolProperty(
        name="Export Materials",
        description="Export basic materials and textures",
        default=True,
    )

    export_normals: BoolProperty(
        name="Export Normals",
        description="Export vertex normals",
        default=True,
    )

    export_uv: BoolProperty(
        name="Export UVs",
        description="Export texture coordinates",
        default=True,
    )

    triangulate: BoolProperty(
        name="Triangulate",
        description="Convert all faces to triangles",
        default=True,
    )

    def execute(self, context):
        try:
            self.export_dae(context)
            self.report({'INFO'}, f"Successfully exported {self.filepath}")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Export failed: {str(e)}")
            return {'CANCELLED'}

    def export_dae(self, context):
        # Create root element
        root = ET.Element("COLLADA")
        root.set("xmlns", "http://www.collada.org/2005/11/COLLADASchema")
        root.set("version", "1.4.1")

        # Asset info
        asset = ET.SubElement(root, "asset")
        contributor = ET.SubElement(asset, "contributor")
        author = ET.SubElement(contributor, "author")
        author.text = "Blender Simple DAE Exporter"
        created = ET.SubElement(asset, "created")
        created.text = "2024-01-01T00:00:00"
        modified = ET.SubElement(asset, "modified")
        modified.text = "2024-01-01T00:00:00"
        unit = ET.SubElement(asset, "unit")
        unit.set("name", "meter")
        unit.set("meter", "1")
        up_axis = ET.SubElement(asset, "up_axis")
        up_axis.text = "Z_UP"  # Blender uses Z-up

        libraries = {
            'images': ET.SubElement(root, "library_images"),
            'materials': ET.SubElement(root, "library_materials"),
            'effects': ET.SubElement(root, "library_effects"),
            'geometries': ET.SubElement(root, "library_geometries"),
            'visual_scenes': ET.SubElement(root, "library_visual_scenes"),
        }

        scene = ET.SubElement(libraries['visual_scenes'], "visual_scene")
        scene.set("id", "Scene")
        scene.set("name", "Scene")

        # Get objects to export
        if self.use_selection:
            objects = [obj for obj in context.selected_objects if obj.type == 'MESH']
        else:
            objects = [obj for obj in context.scene.objects if obj.type == 'MESH']

        if not objects:
            raise Exception("No mesh objects found to export")

        base_path = os.path.dirname(self.filepath)
        exported_materials = {}  # Track exported materials to avoid duplicates
        exported_images = {}     # Track exported images

        for obj in objects:
            self.export_object(
                obj, libraries, scene, base_path,
                exported_materials, exported_images
            )

        # Instance scene
        scene_node = ET.SubElement(root, "scene")
        instance = ET.SubElement(scene_node, "instance_visual_scene")
        instance.set("url", "#Scene")

        # Write file with pretty formatting
        xml_str = ET.tostring(root, encoding='unicode')
        pretty_xml = minidom.parseString(xml_str).toprettyxml(indent="  ")
        
        # Clean up empty lines
        lines = [line for line in pretty_xml.split('\n') if line.strip()]
        
        with open(self.filepath, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

    def export_object(self, obj, libraries, scene, base_path, 
                      exported_materials, exported_images):
        mesh = obj.to_mesh()
        
        if mesh is None:
            return

        # Apply modifiers if requested
        if self.apply_modifiers:
            depsgraph = bpy.context.evaluated_depsgraph_get()
            eval_obj = obj.evaluated_get(depsgraph)
            mesh = eval_obj.to_mesh()
        else:
            mesh = obj.data.copy()

        # Triangulate if requested
        if self.triangulate:
            bm = bmesh.new()
            bm.from_mesh(mesh)
            bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method='BEAUTY', ngon_method='BEAUTY')
            bm.to_mesh(mesh)
            bm.free()

        # Calculate normals
        # mesh.calc_normals_split()

        obj_name = obj.name.replace(" ", "_")
        geom_id = f"{obj_name}-mesh"
        geometry = ET.SubElement(libraries['geometries'], "geometry")
        geometry.set("id", geom_id)
        geometry.set("name", obj_name)

        mesh_node = ET.SubElement(geometry, "mesh")

        # Positions
        positions = []
        for v in mesh.vertices:
            # Apply world matrix to keep world origin
            co = obj.matrix_world @ v.co
            positions.extend([co.x, co.y, co.z])

        self.add_source(mesh_node, "positions", "XYZ", positions, 
                       f"{geom_id}-positions", "float")

        # Normals
        if self.export_normals:
            normals = []
            for loop in mesh.loops:
                no = obj.matrix_world.to_3x3() @ loop.normal
                normals.extend([no.x, no.y, no.z])
            self.add_source(mesh_node, "normals", "XYZ", normals,
                          f"{geom_id}-normals", "float")

        # UVs
        uv_layer = None
        if self.export_uv and mesh.uv_layers:
            uv_layer = mesh.uv_layers.active
            if uv_layer and len(uv_layer.data) == len(mesh.loops):
                uvs = []
                for i, loop in enumerate(mesh.loops):
                    uv = uv_layer.data[i].uv
                    uvs.extend([uv.x, uv.y])
                self.add_source(mesh_node, "uvs", "ST", uvs,
                              f"{geom_id}-uvs", "float")

        # Vertices
        vertices_node = ET.SubElement(mesh_node, "vertices")
        vertices_node.set("id", f"{geom_id}-vertices")
        input_pos = ET.SubElement(vertices_node, "input")
        input_pos.set("semantic", "POSITION")
        input_pos.set("source", f"#{geom_id}-positions")

        # Triangles or Polylist
        triangles = None
        if self.triangulate:
            triangles = ET.SubElement(mesh_node, "triangles")
            triangles.set("count", str(len(mesh.polygons)))
        else:
            # Use polylist for quads/ngons
            triangles = ET.SubElement(mesh_node, "polylist")
            triangles.set("count", str(len(mesh.polygons)))
            vcount = ET.SubElement(triangles, "vcount")
            vcount.text = ' '.join([str(len(p.loop_indices)) for p in mesh.polygons])

        # 收集并导出所有使用的材质
        material_map = {}  # material_index -> mat_name
        if self.export_materials and obj.material_slots:
            for slot_idx, slot in enumerate(obj.material_slots):
                if slot.material:
                    mat_name = slot.material.name.replace(" ", "_")
                    material_map[slot_idx] = mat_name
                    self.export_material(
                        slot.material, libraries, base_path,
                        exported_materials, exported_images
                    )

        # 按材质索引分组多边形
        polys_by_mat = {}
        for poly in mesh.polygons:
            mat_idx = poly.material_index
            if mat_idx not in polys_by_mat:
                polys_by_mat[mat_idx] = []
            polys_by_mat[mat_idx].append(poly)

        # 为每个材质组创建独立的triangles元素
        # 如果对象没有材质，创建一个默认的无材质triangles
        if not material_map:
            self.create_triangles_element(
                mesh_node, mesh, geom_id, "default", None,
                mesh.polygons, uv_layer
            )
        else:
            for mat_idx, mat_name in material_map.items():
                polys = polys_by_mat.get(mat_idx, [])
                if polys:  # 只导出实际有面的材质组
                    self.create_triangles_element(
                        mesh_node, mesh, geom_id, mat_name, f"{mat_name}-material",
                        polys, uv_layer
                    )

        # Clean up temp mesh
        if self.apply_modifiers or not self.apply_modifiers:
            # Always clean up if we copied
            pass
        obj.to_mesh_clear()

        # Visual scene node
        node = ET.SubElement(scene, "node")
        node.set("id", obj_name)
        node.set("name", obj_name)
        node.set("type", "NODE")

        # Since we baked world matrix into vertices, use identity matrix here
        matrix = ET.SubElement(node, "matrix")
        matrix.set("sid", "transform")
        # Identity matrix as string (4x4)
        matrix.text = "1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"

        instance_geom = ET.SubElement(node, "instance_geometry")
        instance_geom.set("url", f"#{geom_id}")
        
        if material_map:
            bind_material = ET.SubElement(instance_geom, "bind_material")
            technique = ET.SubElement(bind_material, "technique_common")
            
            # 为每个使用的材质创建绑定
            for mat_idx, mat_name in material_map.items():
                instance_mat = ET.SubElement(technique, "instance_material")
                instance_mat.set("symbol", f"{mat_name}-material")
                instance_mat.set("target", f"#{mat_name}-material")

    # 创建一个triangles元素，包含指定多边形的几何数据 create triangles element containing specified polygons geometry
    def create_triangles_element(self, parent, mesh, geom_id, mat_name, 
                                material_symbol, polygons, uv_layer):
        
        # decide using triangles or polylist
        is_triangulated = all(len(p.loop_indices) == 3 for p in polygons)
        
        if is_triangulated:
            elem = ET.SubElement(parent, "triangles")
            elem.set("count", str(len(polygons)))
        else:
            elem = ET.SubElement(parent, "polylist")
            elem.set("count", str(len(polygons)))
            vcount = ET.SubElement(elem, "vcount")
            vcount.text = ' '.join([str(len(p.loop_indices)) for p in polygons])
        
        if material_symbol:
            elem.set("material", material_symbol)
        
        # add input source reference
        offset = 0
        
        input_vertex = ET.SubElement(elem, "input")
        input_vertex.set("semantic", "VERTEX")
        input_vertex.set("source", f"#{geom_id}-vertices")
        input_vertex.set("offset", str(offset))
        offset += 1
        
        input_normal = ET.SubElement(elem, "input")
        input_normal.set("semantic", "NORMAL")
        input_normal.set("source", f"#{geom_id}-normals")
        input_normal.set("offset", str(offset))
        offset += 1
        
        if uv_layer:
            input_uv = ET.SubElement(elem, "input")
            input_uv.set("semantic", "TEXCOORD")
            input_uv.set("source", f"#{geom_id}-uvs")
            input_uv.set("offset", str(offset))
            input_uv.set("set", "0")
            offset += 1

        # 收集索引 collect indices
        indices = []
        for poly in polygons:
            loop_start = poly.loop_start
            loop_total = poly.loop_total
            
            for i in range(loop_total):
                loop_idx = loop_start + i
                vertex_idx = mesh.loops[loop_idx].vertex_index
                
                idx_parts = [str(vertex_idx)]
                
                # 法线索引（使用loop索引）
                idx_parts.append(str(loop_idx))
                
                # UV索引（使用loop索引）
                if uv_layer:
                    idx_parts.append(str(loop_idx))
                
                indices.append(' '.join(idx_parts))
        
        p = ET.SubElement(elem, "p")
        p.text = ' '.join(indices)

    def add_source(self, parent, name, components, data, id_str, data_type):
        source = ET.SubElement(parent, "source")
        source.set("id", id_str)
        source.set("name", name)
        
        float_array = ET.SubElement(source, "float_array")
        float_array.set("id", f"{id_str}-array")
        float_array.set("count", str(len(data)))
        float_array.text = ' '.join([str(f) for f in data])
        
        technique = ET.SubElement(source, "technique_common")
        accessor = ET.SubElement(technique, "accessor")
        accessor.set("source", f"#{id_str}-array")
        accessor.set("count", str(len(data) // len(components)))
        accessor.set("stride", str(len(components)))
        
        for comp in components:
            param = ET.SubElement(accessor, "param")
            param.set("name", comp)
            param.set("type", data_type)

    def export_material(self, mat, libraries, base_path, 
                       exported_materials, exported_images):
        mat_name = mat.name.replace(" ", "_")
        
        if mat_name in exported_materials:
            return f"#{mat_name}-material"
        
        exported_materials[mat_name] = True

        # Material
        material = ET.SubElement(libraries['materials'], "material")
        material.set("id", f"{mat_name}-material")
        material.set("name", mat_name)
        
        instance_effect = ET.SubElement(material, "instance_effect")
        instance_effect.set("url", f"#{mat_name}-effect")

        # Effect
        effect = ET.SubElement(libraries['effects'], "effect")
        effect.set("id", f"{mat_name}-effect")
        effect.set("name", mat_name)
        
        profile_common = ET.SubElement(effect, "profile_COMMON")
        
        # Check for image texture
        image_path = None
        image_name = None
        
        if mat.use_nodes and mat.node_tree:
            for node in mat.node_tree.nodes:
                if node.type == 'TEX_IMAGE' and node.image:
                    image = node.image
                    if image.filepath:
                        # Get absolute path
                        img_path = bpy.path.abspath(image.filepath)
                        if os.path.exists(img_path):
                            image_path = img_path
                            image_name = image.name.replace(" ", "_")
                            break
        
        # Newparam for sampler if we have image
        if image_name and image_name not in exported_images:
            exported_images[image_name] = True
            
            # Image library
            img_elem = ET.SubElement(libraries['images'], "image")
            img_elem.set("id", f"{image_name}-image")
            img_elem.set("name", image_name)
            init_from = ET.SubElement(img_elem, "init_from")
            # Relative path for portability
            rel_path = os.path.relpath(image_path, base_path) if base_path else image_path
            init_from.text = rel_path.replace("\\", "/")

            # Newparam
            newparam = ET.SubElement(profile_common, "newparam")
            newparam.set("sid", f"{image_name}-surface")
            surface = ET.SubElement(newparam, "surface")
            surface.set("type", "2D")
            init_from_surf = ET.SubElement(surface, "init_from")
            init_from_surf.text = f"{image_name}-image"
            
            newparam2 = ET.SubElement(profile_common, "newparam")
            newparam2.set("sid", f"{image_name}-sampler")
            sampler2d = ET.SubElement(newparam2, "sampler2D")
            source = ET.SubElement(sampler2d, "source")
            source.text = f"{image_name}-surface"

        # Technique
        technique = ET.SubElement(profile_common, "technique")
        technique.set("sid", "common")
        
        lambert = ET.SubElement(technique, "lambert")  # Simple shading model
        
        # Diffuse
        diffuse = ET.SubElement(lambert, "diffuse")
        
        if image_name:
            texture = ET.SubElement(diffuse, "texture")
            texture.set("texture", f"{image_name}-sampler")
            texture.set("texcoord", "UVMap")
        else:
            color = ET.SubElement(diffuse, "color")
            color.set("sid", "diffuse")
            # Get diffuse color from principled or diffuse shader
            rgb = correct_color([0.8, 0.8, 0.8, 1.0])  # Default color with gamma correction
            if mat.use_nodes and mat.node_tree:
                principled = None
                for node in mat.node_tree.nodes:
                    if node.type == 'BSDF_PRINCIPLED':
                        principled = node
                        break
                if principled:
                    base_color = principled.inputs['Base Color'].default_value
                    rgb = correct_color(list(base_color)) # Principled color with gamma correction
                else:
                    rgb = correct_color([0.8, 0.8, 0.8, 1.0])
            
            color.text = f"{rgb[0]} {rgb[1]} {rgb[2]} {rgb[3] if len(rgb) > 3 else 1.0}"

        # Index of refraction
        index_of_refraction = ET.SubElement(lambert, "index_of_refraction")
        index_of_refraction.set("sid", "ior")
        index_of_refraction.text = "1.0"

        return f"#{mat_name}-material"


def menu_func_export(self, context):
    self.layout.operator(DAEExporter.bl_idname, text="Collada DAE (.dae)")

# Linear to sRGB (Gamma correction)
def linear_to_srgb(c):

    if c <= 0.0031308:
        return 0.0 if c < 0 else c * 12.92
    else:
        return 1.055 * (c ** (1.0 / 2.4)) - 0.055

# RGB color Gamma correction，keep Alpha
def correct_color(linear_rgb):

    if len(linear_rgb) >= 3:
        r, g, b = linear_rgb[0], linear_rgb[1], linear_rgb[2]
        a = linear_rgb[3] if len(linear_rgb) > 3 else 1.0
        return [
            linear_to_srgb(r),
            linear_to_srgb(g), 
            linear_to_srgb(b),
            a
        ]
    return linear_rgb

def register():
    bpy.utils.register_class(DAEExporter)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)


def unregister():
    bpy.utils.unregister_class(DAEExporter)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)


if __name__ == "__main__":
    register()