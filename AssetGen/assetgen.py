# -*- coding: utf-8 -*-
###############################################
#         Asset Loop Generator for May
"""
Features:
- Procedural Asset curve generation
- Curve-only or tube generation
- Width / Height / Depth / Resolution controls
- Orientation control
- Twist control
- Repeat count / spacing
- Update / Reset / Delete tools
- Designed to be launched from a Maya shelf button

Usage:
    import Asset_generator
    Asset_generator.show()
"""
###############################################

import math
import maya.cmds as cmds
from maya import OpenMayaUI as omui

try:
    from shiboken2 import wrapInstance
except ImportError:
    from shiboken6 import wrapInstance

from PySide6 import QtCore, QtWidgets


WINDOW_OBJECT_NAME = "AssetGeneratorWindow"
WINDOW_TITLE = "Asset Generator"
ROOT_GROUP_NAME = "assetGen_grp"


def maya_main_window():
    ptr = omui.MQtUtil.mainWindow()
    if ptr is not None:
        return wrapInstance(int(ptr), QtWidgets.QWidget)
    return None


def delete_if_exists(node):
    if node and cmds.objExists(node):
        cmds.delete(node)


def get_unique_name(base_name):
    if not cmds.objExists(base_name):
        return base_name

    index = 1
    while True:
        candidate = f"{base_name}{index}"
        if not cmds.objExists(candidate):
            return candidate
        index += 1


def ensure_root_group():
    if not cmds.objExists(ROOT_GROUP_NAME):
        return cmds.group(empty=True, name=ROOT_GROUP_NAME)
    return ROOT_GROUP_NAME


def rotate_point_for_plane(point, plane):
    x, y, z = point

    if plane == "XZ":
        return (x, y, z)
    if plane == "XY":
        return (x, z, y)
    if plane == "YZ":
        return (y, x, z)

    return (x, y, z)


class AssetGeneratorCore:
    @staticmethod
    def build_Asset_points(width=8.0, height=4.0, depth = 5.0, resolution=100, plane="XZ"):
        points = []
        resolution = max(16, int(resolution))

        for i in range(resolution + 1):
            t = (2.0 * math.pi) * (float(i) / resolution)

            x = width * math.sin(t)
            z = height * math.sin(t) * math.cos(t)
            y = depth * math.cos(2.0*t)
            points.append(rotate_point_for_plane((x, y, z), plane))

        return points

    @staticmethod
    def create_curve(width, height, depth, resolution, plane, name="AssetCurve"):
        points = AssetGeneratorCore.build_Asset_points(
            width=width,
            height=height,
            depth = depth,

            resolution=resolution,
            plane=plane
        )
        return cmds.curve(
            p=points,
            d=1,
            name=get_unique_name(name)
        )

    @staticmethod
    def create_profile(radius, plane, name="AssetProfile"):
        if plane == "XZ":
            normal = (0, 1, 0)
        elif plane == "XY":
            normal = (0, 0, 1)
        elif plane == "YZ":
            normal = (1, 0, 0)
        else:
            normal = (0, 1, 0)

        return cmds.circle(
            name=get_unique_name(name),
            radius=radius,
            normal=normal,
            sections=12
        )[0]

    @staticmethod
    def create_material(material_type="Lambert"):
        shader_name = get_unique_name("AssetShader")

        if material_type == "Lambert":
            shader = cmds.shadingNode("lambert", asShader=True, name=shader_name)
            cmds.setAttr(shader + ".color", 0.3, 0.6, 1.0, type="double3")
        elif material_type == "Gold":
            shader = cmds.shadingNode("blinn", asShader=True, name=shader_name)
            cmds.setAttr(shader + ".color", 0.92, 0.75, 0.18, type="double3")
            cmds.setAttr(shader + ".specularColor", 1.0, 0.85, 0.3, type="double3")
            cmds.setAttr(shader + ".eccentricity", 0.08)
            cmds.setAttr(shader + ".specularRollOff", 0.9)
        elif material_type == "Neon":
            shader = cmds.shadingNode("lambert", asShader=True, name=shader_name)
            cmds.setAttr(shader + ".color", 0.1, 0.7, 1.0, type="double3")
            cmds.setAttr(shader + ".incandescence", 0.3, 0.8, 1.0, type="double3")

        else:
            shader = cmds.shadingNode("lambert", asShader=True, name=shader_name)
            cmds.setAttr(shader + ".color", 0.7, 0.7, 0.7, type="double3")

        sg = cmds.sets(renderable=True, noSurfaceShader=True, empty=True, name=get_unique_name(shader + "SG"))
        cmds.connectAttr(shader + ".outColor", sg + ".surfaceShader", force=True)

        return shader, sg

    @staticmethod
    def assign_material(obj, shading_group):
        shapes = cmds.listRelatives(obj, shapes=True, fullPath=True) or []
        for shape in shapes:
            cmds.sets(shape, edit=True, forceElement=shading_group)

    
    @staticmethod
    def create_motion_path(curve, plane, duration=120):
        locator = cmds.spaceLocator(name=get_unique_name("AssetMotion_loc"))[0]
        motion_path = cmds.pathAnimation(
            locator,
            curve=curve,
            follow=True,
            followAxis="x",
            upAxis="y",
            worldUpType="vector",
            worldUpVector=(0, 1, 0),
            startTimeU=1,
            endTimeU=duration
        )

        if plane == "XY":
            cmds.rotate(0, 0, 0, locator, absolute=True)
        elif plane == "YZ":
            cmds.rotate(0, 90, 0, locator, absolute=True)

        return locator, motion_path

    @staticmethod
    def generate(settings):
        width = settings["width"]
        height = settings["height"]
        depth = settings["depth"]
        
        resolution = settings["resolution"]
        plane = settings["plane"]
        geometry_mode = settings["geometry_mode"]
        thickness = settings["thickness"]
        repeat_count = settings["repeat_count"]
        spacing = settings["spacing"]
        material_type = settings["material_type"]
        animate = settings["animate"]
        animation_length = settings["animation_length"]

        root_group = ensure_root_group()
        asset_group = cmds.group(empty=True, name=get_unique_name("AssetAsset_grp"), parent=root_group)

        shading_group = None
        if geometry_mode == "Tube":
            _, shading_group = AssetGeneratorCore.create_material(material_type)

        for i in range(repeat_count):
            curve = AssetGeneratorCore.create_curve(
                width=width,
                height=height,
                depth = depth,
                resolution = resolution,
                plane=plane
            )
            cmds.parent(curve, asset_group)

            if plane == "XZ":
                cmds.move(0, i * spacing, 0, curve, relative=True)
            elif plane == "XY":
                cmds.move(0, 0, i * spacing, curve, relative=True)
            elif plane == "YZ":
                cmds.move(i * spacing, 0, 0, curve, relative=True)

            if geometry_mode == "Tube":
                profile = AssetGeneratorCore.create_profile(thickness, plane)
                start_point = cmds.pointPosition(curve + ".cv[0]", world=True)
                cmds.xform(profile, worldSpace=True, translation=start_point)

                surface, extrude_node = cmds.extrude(
                    profile,
                    curve,
                    ch=True,
                    rn=False,
                    po=1,
                    et=2,
                    ucp=1,
                    fpt=1,
                    upn=1,
                    rotation=0,
                    scale=1
                )

                cmds.parent(profile, asset_group)
                cmds.parent(surface, asset_group)

                AssetGeneratorCore.assign_material(surface, shading_group)
                

            if animate:
                locator, _ = AssetGeneratorCore.create_motion_path(
                    curve,
                    plane=plane,
                    duration=animation_length
                )
                cmds.parent(locator, asset_group)

        return asset_group


class AssetGeneratorUI(QtWidgets.QDialog):
    def __init__(self, parent=maya_main_window()):
        super(AssetGeneratorUI, self).__init__(parent)

        self.setObjectName(WINDOW_OBJECT_NAME)
        self.setWindowTitle(WINDOW_TITLE)
        self.setMinimumWidth(430)
        self.setWindowFlags(self.windowFlags() ^ QtCore.Qt.WindowContextHelpButtonHint)

        self.last_created = None

        self.create_widgets()
        self.create_layout()
        self.create_connections()
        self.reset_defaults()

    def create_widgets(self):
        self.width_spin = QtWidgets.QDoubleSpinBox()
        self.width_spin.setRange(0.1, 1000.0)
        self.width_spin.setDecimals(2)

        self.height_spin = QtWidgets.QDoubleSpinBox()
        self.height_spin.setRange(0.1, 1000.0)
        self.height_spin.setDecimals(2)

        self.depth_spin = QtWidgets.QDoubleSpinBox()
        self.depth_spin.setRange(0.1, 1000.0)
        self.depth_spin.setDecimals(2)

        self.resolution_spin = QtWidgets.QSpinBox()
        self.resolution_spin.setRange(16, 500)

        self.plane_combo = QtWidgets.QComboBox()
        self.plane_combo.addItems(["XZ", "XY", "YZ"])

        self.geometry_combo = QtWidgets.QComboBox()
        self.geometry_combo.addItems(["Curve Only", "Tube"])

        self.thickness_spin = QtWidgets.QDoubleSpinBox()
        self.thickness_spin.setRange(0.01, 100.0)
        self.thickness_spin.setDecimals(3)

        self.repeat_spin = QtWidgets.QSpinBox()
        self.repeat_spin.setRange(1, 50)

        self.spacing_spin = QtWidgets.QDoubleSpinBox()
        self.spacing_spin.setRange(0.0, 100.0)
        self.spacing_spin.setDecimals(2)

        self.material_combo = QtWidgets.QComboBox()
        self.material_combo.addItems(["Lambert", "Gold", "Neon"])

        #self.animate_checkbox = QtWidgets.QCheckBox("Create motion-path locator")

        self.animation_length_spin = QtWidgets.QSpinBox()
        self.animation_length_spin.setRange(10, 2000)

        self.generate_btn = QtWidgets.QPushButton("Generate")
        self.update_btn = QtWidgets.QPushButton("Update Selected")
        self.delete_btn = QtWidgets.QPushButton("Delete Previous")
        self.reset_btn = QtWidgets.QPushButton("Reset")

    def create_layout(self):
        main_layout = QtWidgets.QVBoxLayout(self)

        shape_group = QtWidgets.QGroupBox("Shape Settings")
        shape_form = QtWidgets.QFormLayout(shape_group)
        shape_form.addRow("Width:", self.width_spin)
        shape_form.addRow("Height:", self.height_spin)
        shape_form.addRow("Depth:", self.depth_spin)
        shape_form.addRow("Resolution:", self.resolution_spin)
        shape_form.addRow("Plane:", self.plane_combo)

        geo_group = QtWidgets.QGroupBox("Geometry Settings")
        geo_form = QtWidgets.QFormLayout(geo_group)
        geo_form.addRow("Mode:", self.geometry_combo)
        geo_form.addRow("Thickness:", self.thickness_spin)
        geo_form.addRow("Material:", self.material_combo)

        extras_group = QtWidgets.QGroupBox("Extras")
        extras_form = QtWidgets.QFormLayout(extras_group)
        extras_form.addRow("Repeat Count:", self.repeat_spin)
        extras_form.addRow("Repeat Spacing:", self.spacing_spin)
        #extras_form.addRow(self.animate_checkbox)
        #extras_form.addRow("Animation Length:", self.animation_length_spin)

        buttons_layout = QtWidgets.QGridLayout()
        buttons_layout.addWidget(self.generate_btn, 0, 0)
        buttons_layout.addWidget(self.update_btn, 0, 1)
        buttons_layout.addWidget(self.delete_btn, 1, 0)
        buttons_layout.addWidget(self.reset_btn, 1, 1)

        main_layout.addWidget(shape_group)
        main_layout.addWidget(geo_group)
        main_layout.addWidget(extras_group)
        main_layout.addLayout(buttons_layout)

    def create_connections(self):
        self.generate_btn.clicked.connect(self.on_generate)
        self.update_btn.clicked.connect(self.on_update_selected)
        self.delete_btn.clicked.connect(self.on_delete_previous)
        self.reset_btn.clicked.connect(self.reset_defaults)
        self.geometry_combo.currentTextChanged.connect(self.on_geometry_changed)

    def reset_defaults(self):
        self.width_spin.setValue(8.0)
        self.height_spin.setValue(4.0)
        self.depth_spin.setValue(5.0)
        
        self.resolution_spin.setValue(100)
        self.plane_combo.setCurrentText("XZ")
        self.geometry_combo.setCurrentText("Tube")
        self.thickness_spin.setValue(0.25)
        self.repeat_spin.setValue(1)
        self.spacing_spin.setValue(2.5)
        self.material_combo.setCurrentText("'Lambert'")
       # self.animate_checkbox.setChecked(False)
        self.animation_length_spin.setValue(120)
        self.on_geometry_changed(self.geometry_combo.currentText())

    def on_geometry_changed(self, mode):
        is_tube = (mode == "Tube")
        self.thickness_spin.setEnabled(is_tube)
        self.material_combo.setEnabled(is_tube)

    def get_settings(self):
        return {
            "width": self.width_spin.value(),
            "height": self.height_spin.value(),
            "depth": self.depth_spin.value(),
            "resolution": self.resolution_spin.value(),
            "plane": self.plane_combo.currentText(),
            "geometry_mode": self.geometry_combo.currentText(),
            "thickness": self.thickness_spin.value(),
            "repeat_count": self.repeat_spin.value(),
            "spacing": self.spacing_spin.value(),
            "material_type": self.material_combo.currentText(),
            "animate": True, # self.animate_checkbox.isChecked(),
            "animation_length": self.animation_length_spin.value(),
        }

    def on_generate(self):
        settings = self.get_settings()
        result = AssetGeneratorCore.generate(settings)
        self.last_created = result
        cmds.select(result)

    def on_update_selected(self):
        selected = cmds.ls(selection=True, long=True) or []
        if not selected:
            cmds.warning("Select a generated asset group to replace, or click Generate.")
            return

        target = selected[0]
        parent = None
        parents = cmds.listRelatives(target, parent=True, fullPath=True) or []
        if parents:
            parent = parents[0]

        delete_if_exists(target)

        result = AssetGeneratorCore.generate(self.get_settings())
        self.last_created = result

        if parent and cmds.objExists(parent):
            try:
                cmds.parent(result, parent)
            except Exception:
                pass

        cmds.select(result)

    def on_delete_previous(self):
        if self.last_created and cmds.objExists(self.last_created):
            delete_if_exists(self.last_created)
            self.last_created = None
        elif cmds.objExists(ROOT_GROUP_NAME):
            delete_if_exists(ROOT_GROUP_NAME)


def close_existing():
    for widget in QtWidgets.QApplication.allWidgets():
        if widget.objectName() == WINDOW_OBJECT_NAME:
            try:
                widget.close()
                widget.deleteLater()
            except Exception:
                pass


def show():
    close_existing()
    window = AssetGeneratorUI()
    window.show()
    return window