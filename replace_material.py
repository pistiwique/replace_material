import bpy
import re

from bpy.types import Panel, Operator, PropertyGroup
from bpy.props import BoolProperty, PointerProperty, StringProperty

bl_info = {
    "name": "replace_material",
    "description": "Replaces selected material with selected one",
    "author": "Legigan Jeremy AKA pistiwique from a mareck request",
    "version": (0, 0, 1),
    "blender": (2, 78, 0),
    "location": "Properties => Material",
    "category": "Material"}


def update_material_preview(self, context):

    # not an elegant way to force the update of the preview, but it works...
    bpy.context.object.active_material = bpy.context.object.active_material


class REPLACEMAT_OT_select_object_from_mat(Operator):
    ''' Selects the objects with the mat to replace material '''
    bl_idname = 'replace_mat.select_from_mat'
    bl_label = "Select from Mat"
    bl_options = {'REGISTER'}

    def execute(self, context):
        replace = context.window_manager.replace_mat
        valid_obj = False
        obj_count = 0

        for obj in context.scene.objects:
            if obj.material_slots.get(replace.mat_to_replace):
                if not valid_obj:
                    bpy.ops.object.select_all(action='DESELECT')
                    valid_obj = True

                obj.select = True
                obj_count += 1

        if not valid_obj:
            bpy.ops.object.select_all(action='DESELECT')
            self.report({'WARNING'}, "No object with \"%s\" material"
                        %replace.mat_to_replace
                        )

        else:
            self.report({'INFO'}, "%i %s found" %(obj_count, "object" if
            obj_count == 1 else "objects")
                        )

        return {'FINISHED'}


class REPLACEMAT_OT_replace(Operator):
    '''  '''
    bl_idname = 'replace_mat.replace'
    bl_label = "Replace material"
    bl_options = {'REGISTER'}

    props = ['color_space', 'interpolation', 'projection',
             'projection_blend', 'extension']

    @classmethod
    def poll(cls, context):
        replace = context.window_manager.replace_mat
        return replace.mat_to_assign and \
               replace.mat_to_replace != replace.mat_to_assign or \
               replace.mat_to_replace == replace.mat_to_assign and \
               replace.duplicate_mat

    def copy_textures(self, old_mat, new_mat):
        MAT = bpy.data.materials
        loc_x = 0.0
        loc_y = 0.0
        offset = 200

        for node in MAT[old_mat].node_tree.nodes:
            if node.type == 'TEX_IMAGE':
                if node.image:
                    copy_node = MAT[new_mat].node_tree.nodes.new(type='ShaderNodeTexImage')
                    copy_node.location = (loc_x, loc_y)
                    loc_x += offset
                    copy_node.image = node.image
                    for p in self.props:
                        setattr(copy_node, p, getattr(node, p))

    def get_increment(self, mat_name):
        if re.search("\d+$", mat_name):
            return re.search("\d+$", mat_name).group()

    def get_valid_increment(self, name, increment):

        base_name = name[:-len(increment)]
        incremented = str(int(increment) + 1)
        if len(increment) > len(incremented):
            incremented = "0" * (len(increment) - len(incremented)) + \
                          str(incremented)

        new_name = base_name + incremented
        if not new_name in bpy.data.materials:
            return new_name

        return self.get_valid_increment(new_name, self.get_increment(name))

    def assign_mat(self, to_assign, mat, replace):
        if replace.duplicate_mat:
            mat_copy = to_assign.copy()
            increment_value = self.get_increment(to_assign.name)
            if increment_value and not to_assign.name.endswith\
                            (".%s" %increment_value):

                new_name = self.get_valid_increment(to_assign.name,
                                                    increment_value
                                                    )
                mat.material = mat_copy
                mat.material.name = new_name

            else:
                mat.material = mat_copy
        else:
            mat.material = to_assign

        if replace.copy_textures:
            self.copy_textures(replace.mat_to_replace, mat_copy.name if
            replace.duplicate_mat else replace.mat_to_assign
                               )

    def execute(self, context):
        replace = context.window_manager.replace_mat

        for obj in context.scene.objects:
            if obj.type == 'MESH' and (not replace.only_selected_objects or (
                        replace.only_selected_objects and obj.select)):
                if getattr(obj, 'active_material'):
                    if obj.material_slots.get(replace.mat_to_replace):
                        for mat in obj.material_slots:
                            if mat.name == replace.mat_to_replace:
                                to_assign = bpy.data.materials.get(replace.mat_to_assign)
                                if to_assign:
                                    self.assign_mat(to_assign, mat, replace)

        if replace.remove_mat:
            bpy.data.materials.remove(bpy.data.materials[replace.mat_to_replace],
                                      do_unlink=True)
            replace.mat_to_replace = context.object.active_material.name

        return {'FINISHED'}


class CyclesButtonsPanel:
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "render"
    COMPAT_ENGINES = {'CYCLES'}

    @classmethod
    def poll(cls, context):
        rd = context.scene.render
        return rd.engine in cls.COMPAT_ENGINES


class REPLACEMAT_panel(CyclesButtonsPanel, Panel):
    bl_label = "Replace material"
    bl_context = "material"
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        return context.material and CyclesButtonsPanel.poll(context)

    def draw(self, context):
        replace = context.window_manager.replace_mat
        layout = self.layout
        row = layout.row(align=True)
        if replace.mat_from_active:
            row.prop_search(replace, 'mat_to_replace', bpy.context.object,
                            'material_slots')
        else:
            row.prop_search(replace, 'mat_to_replace', bpy.data, 'materials')
        row.operator('replace_mat.select_from_mat', text="", icon='MOD_ARRAY')

        if replace.mat_to_replace:
            row = layout.row(align=True)
            row.prop(replace, 'mat_from_active')
            row.prop(replace, 'remove_mat')
            layout.separator()
            layout.template_preview(bpy.data.materials[replace.mat_to_replace])
            layout.separator()
            layout.prop_search(replace, 'mat_to_assign', bpy.data, 'materials')
            row = layout.row(align=True)
            row.prop(replace, 'only_selected_objects')
            row.prop(replace, 'duplicate_mat')
            layout.prop(replace, 'copy_textures')

            layout.operator('replace_mat.replace')


class ReplaceMaterialCollectrionGroup(PropertyGroup):

    mat_to_replace = StringProperty(
            name="Mat To Replace",
            default="",
            update=update_material_preview,
            )

    mat_to_assign = StringProperty(
            name="Mat To Assign",
            default="",
            )

    only_selected_objects = BoolProperty(
            name="On Selected Objects",
            default=False,
            description="Change materials only from selected objects",
            )

    remove_mat = BoolProperty(
            name="Remove material",
            default=False,
            description="Remove old material after replaced",
            )

    mat_from_active = BoolProperty(
            name="Mat From Active",
            default=False,
            description="Display only active object materials",
            )

    copy_textures = BoolProperty(
            name="Copy Textures",
            default=True,
            description="Copies the textures from the old material to the "
                        "new one"
            )

    duplicate_mat = BoolProperty(
            name="Duplicate Mat",
            default=False,
            description="Replace the mat to replace by a copy of the mat to "
                        "assign"
            )


def register():
    bpy.utils.register_module(__name__)
    bpy.types.WindowManager.replace_mat = PointerProperty(
            type=ReplaceMaterialCollectrionGroup)


def unregister():
    del bpy.types.WindowManager.replace_mat
    bpy.utils.unregister_module(__name__)


if __name__ == "__main__":
    register()