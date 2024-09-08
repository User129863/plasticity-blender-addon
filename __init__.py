import bpy
import json
import os
import bpy.app.handlers

from bpy.app.handlers import persistent
from . import operators, ui
from .client import PlasticityClient
from .handler import SceneHandler

bl_info = {
    "name": "Plasticity",
    "description": "A bridge to Plasticity",
    "author": "Nick Kallen, User129863",
    "version": (2, 1, 0),
    "blender": (4, 1, 0),
    "location": "View3D > Sidebar > Plasticity",
    "category": "Object",
}

handler = SceneHandler()
plasticity_client = PlasticityClient(handler)

addon_name = bl_info["name"].replace(" ", "_")  

base_path = bpy.utils.script_path_user()
presets_folder = os.path.join(base_path, 'presets', addon_name)

if not os.path.exists(presets_folder):
    os.makedirs(presets_folder)

PRESET_FILE_PATH = os.path.join(presets_folder, 'refacet_presets.json')

# Save Refacet presets
def save_presets():
    presets = []
    for preset in bpy.context.scene.refacet_presets:        
        preset_dict = preset.to_dict()        
        presets.append(preset_dict)
            
    with open(PRESET_FILE_PATH, 'w') as f:
        json.dump(presets, f)           

# Load refacet presets
@persistent
def load_presets(dummy):
    scene = bpy.context.scene

    # Clear existing presets
    scene.refacet_presets.clear()
    
    if scene is None or not os.path.exists(PRESET_FILE_PATH):        
        return
    with open(PRESET_FILE_PATH, 'r') as f:
        presets = json.load(f)    
    
    for preset_dict in presets:
        preset = scene.refacet_presets.add()
        preset.from_dict(preset_dict)            

def update_and_save_preset(self, context):
    save_presets()
    
def update_name(self, context):
    print("Name updated.")
    save_presets()    

# Custom UIList to catch the event of renaming a member of the list. Looks like it's not natively supported by the API (necessary in order to save the Refacet presets whenever an entry is renamed by double clicking on an entry and renaming it).
class OBJECT_UL_RefacetPresetsList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            layout.prop(item, "name", text="", emboss=False, icon_value=icon)
        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text="", icon_value=icon)    

# Refacet Preset Class    
class RefacetPreset(bpy.types.PropertyGroup):              
    name: bpy.props.StringProperty(name="Name", default="New Preset", update=update_name)
    
    # Basic settings
    tolerance: bpy.props.FloatProperty(name="Tolerance", default=0.01, min=0.0001, max=0.1, step=0.001, precision=6, update=update_and_save_preset)
    angle: bpy.props.FloatProperty(name="Angle", default=0.45, min=0.1, max=1.0, update=update_and_save_preset)
    
    # Advanced settings
    min_width: bpy.props.FloatProperty(name="Min Width", default=0.0, min=0, max=10, unit="LENGTH", update=update_and_save_preset)    
    max_width: bpy.props.FloatProperty(name="Max Width", default=0.0, min=0.0001, max=1000.0, step=0.01, soft_min=0.02, precision=6, unit="LENGTH", update=update_and_save_preset)
    Edge_chord_tolerance: bpy.props.FloatProperty(name="Edge chord tolerance", default=0.01, min=0.0001, step=0.01, max=1.0, precision=6, update=update_and_save_preset)
    Edge_Angle_tolerance: bpy.props.FloatProperty(name="Edge Angle tolerance", default=0.45, min=0.1, max=1.0, update=update_and_save_preset)
    Face_plane_tolerance: bpy.props.FloatProperty(name="Face plane tolerance", default=0.01, min=0.0001, step=0.01, max=1.0, precision=6, update=update_and_save_preset)
    Face_Angle_tolerance: bpy.props.FloatProperty(name="Face Angle tolerance", default=0.45, min=0.1, max=1.0, update=update_and_save_preset)     

    def to_dict(self):
        return {attr: getattr(self, attr) for attr in dir(self) 
                if not callable(getattr(self, attr)) 
                and not attr.startswith("__") 
                and isinstance(getattr(self, attr), (int, float, str))}

    def from_dict(self, preset_dict):
        for attr, value in preset_dict.items():
            setattr(self, attr, value)                 

class AddRefacetPresetOperator(bpy.types.Operator):
    bl_idname = "refacet_preset.add"
    bl_label = "Add Refacet Preset"
    
    def execute(self, context):
        preset = context.scene.refacet_presets.add()
        preset.name = "New Preset"
        save_presets()
        return {'FINISHED'}

class RemoveRefacetPresetOperator(bpy.types.Operator):
    bl_idname = "refacet_preset.remove"
    bl_label = "Remove Refacet Preset"
    
    def execute(self, context):
        index = context.scene.active_refacet_preset_index
        context.scene.refacet_presets.remove(index)
        save_presets()

        if len(context.scene.refacet_presets) > 0:
            context.scene.active_refacet_preset_index = min(max(0, index - 1), len(context.scene.refacet_presets) - 1)
        else:
            context.scene.active_refacet_preset_index = -1

        return {'FINISHED'}

def select_similar(self, context):
    self.layout.operator(operators.SelectByFaceIDOperator.bl_idname)   

def register():
    print("Registering Plasticity client")

    bpy.utils.register_class(ui.ConnectButton)
    bpy.utils.register_class(ui.DisconnectButton)
    bpy.utils.register_class(ui.ListButton)
    bpy.utils.register_class(ui.SubscribeAllButton)
    bpy.utils.register_class(ui.UnsubscribeAllButton)
    bpy.utils.register_class(ui.RefacetButton)

    bpy.utils.register_class(RefacetPreset)
    bpy.types.Scene.refacet_presets = bpy.props.CollectionProperty(type=RefacetPreset)
    bpy.types.Scene.active_refacet_preset_index = bpy.props.IntProperty(name="Active Preset", default=0)
    bpy.utils.register_class(AddRefacetPresetOperator)
    bpy.utils.register_class(RemoveRefacetPresetOperator) 
   
    bpy.utils.register_class(ui.PlasticityPanel)
    bpy.utils.register_class(operators.SelectByFaceIDOperator)
    bpy.utils.register_class(operators.SelectByFaceIDEdgeOperator)
    bpy.utils.register_class(operators.AutoMarkEdgesOperator)
    bpy.utils.register_class(operators.MergeUVSeams)
    bpy.utils.register_class(operators.PaintPlasticityFacesOperator)
    bpy.utils.register_class(operators.SimilarGeometrySelector)
    bpy.utils.register_class(operators.SelectedJoiner)
    bpy.utils.register_class(operators.SelectedUnjoiner)    
    bpy.utils.register_class(operators.NonOverlappingMeshesMerger)   
    bpy.utils.register_class(operators.OpenUVEditorOperator) 

    bpy.types.VIEW3D_MT_edit_mesh_select_similar.append(select_similar)

    bpy.types.Scene.prop_plasticity_server = bpy.props.StringProperty(name="Server", default="localhost:8980")
    bpy.types.Scene.prop_plasticity_facet_tolerance = bpy.props.FloatProperty(name="Tolerance", default=0.01, min=0.0001, max=0.1, step=0.001, precision=6)
    bpy.types.Scene.prop_plasticity_facet_angle = bpy.props.FloatProperty(name="Angle", default=0.45, min=0.1, max=1.0)
    bpy.types.Scene.prop_plasticity_list_only_visible = bpy.props.BoolProperty(name="List only visible", default=False)
    bpy.types.Scene.prop_plasticity_facet_tri_or_ngon = bpy.props.EnumProperty(
        items=[
            ("TRI", "Tri", "Tri"),
            ("NGON", "Ngon", "Ngon"),
        ],
        name="Facet Type",
        default="TRI",
    )
    bpy.types.Scene.prop_plasticity_ui_show_advanced_facet = bpy.props.BoolProperty(name="Advanced", default=False)
    bpy.types.Scene.prop_plasticity_facet_min_width = bpy.props.FloatProperty(name="Min Width", default=0.0, min=0, max=10, unit="LENGTH")
    bpy.types.Scene.prop_plasticity_facet_max_width = bpy.props.FloatProperty(name="Max Width", default=0.0, min=0.0001, max=1000.0, step=0.01, soft_min=0.02, precision=6, unit="LENGTH")
    bpy.types.Scene.prop_plasticity_unit_scale = bpy.props.FloatProperty(name="Unit Scale", default=1.0, min=0.0001, max=1000.0)
    bpy.types.Scene.prop_plasticity_curve_chord_tolerance = bpy.props.FloatProperty(name="Edge chord tolerance", default=0.01, min=0.0001, step=0.01, max=1.0, precision=6)
    bpy.types.Scene.prop_plasticity_curve_angle_tolerance = bpy.props.FloatProperty(name="Edge Angle tolerance", default=0.45, min=0.1, max=1.0)
    bpy.types.Scene.prop_plasticity_surface_plane_tolerance = bpy.props.FloatProperty(name="Face plane tolerance", default=0.01, min=0.0001, step=0.01, max=1.0, precision=6)
    bpy.types.Scene.prop_plasticity_surface_angle_tolerance = bpy.props.FloatProperty(name="Face Angle tolerance", default=0.45, min=0.1, max=1.0)
    bpy.types.Scene.mark_seam = bpy.props.BoolProperty(name="Mark Seam")
    bpy.types.Scene.mark_sharp = bpy.props.BoolProperty(name="Mark Sharp") 
        
    bpy.utils.register_class(OBJECT_UL_RefacetPresetsList)  

    bpy.app.handlers.load_post.append(load_presets)    
    
    print("Plasticity client registered")

def unregister():
    print("Unregistering Plasticity client")

    bpy.utils.unregister_class(ui.PlasticityPanel)
    bpy.utils.unregister_class(ui.DisconnectButton)
    bpy.utils.unregister_class(ui.ConnectButton)
    bpy.utils.unregister_class(ui.ListButton)
    bpy.utils.unregister_class(ui.SubscribeAllButton)
    bpy.utils.unregister_class(ui.UnsubscribeAllButton)
    bpy.utils.unregister_class(ui.RefacetButton)
    
    bpy.utils.unregister_class(RefacetPreset)
    bpy.utils.unregister_class(AddRefacetPresetOperator)
    bpy.utils.unregister_class(RemoveRefacetPresetOperator)
    del bpy.types.Scene.refacet_presets
    del bpy.types.Scene.active_refacet_preset_index 
          
    bpy.utils.unregister_class(operators.SelectByFaceIDOperator)
    bpy.utils.unregister_class(operators.SelectByFaceIDEdgeOperator)
    bpy.utils.unregister_class(operators.AutoMarkEdgesOperator)
    bpy.utils.unregister_class(operators.MergeUVSeams)
    bpy.utils.unregister_class(operators.PaintPlasticityFacesOperator)
    bpy.utils.unregister_class(operators.SimilarGeometrySelector)
    bpy.utils.unregister_class(operators.SelectedJoiner) 
    bpy.utils.unregister_class(operators.SelectedUnjoiner)     
    bpy.utils.unregister_class(operators.NonOverlappingMeshesMerger)
    bpy.utils.unregister_class(operators.OpenUVEditorOperator)  

    bpy.types.VIEW3D_MT_edit_mesh_select_similar.remove(select_similar)
    
    bpy.utils.unregister_class(OBJECT_UL_RefacetPresetsList)    
    
    bpy.app.handlers.load_post.remove(load_presets)

    del bpy.types.Scene.prop_plasticity_server
    del bpy.types.Scene.prop_plasticity_facet_tolerance
    del bpy.types.Scene.prop_plasticity_facet_angle
    del bpy.types.Scene.prop_plasticity_facet_tri_or_ngon
    del bpy.types.Scene.prop_plasticity_list_only_visible
    del bpy.types.Scene.prop_plasticity_ui_show_advanced_facet
    del bpy.types.Scene.prop_plasticity_facet_min_width
    del bpy.types.Scene.prop_plasticity_facet_max_width
    del bpy.types.Scene.prop_plasticity_unit_scale
    del bpy.types.Scene.prop_plasticity_surface_angle_tolerance
    del bpy.types.Scene.mark_seam
    del bpy.types.Scene.mark_sharp             

if __name__ == "__main__":
    register()
