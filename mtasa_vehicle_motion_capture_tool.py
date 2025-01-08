from os import path
from bpy.types import (
    Operator,
    Panel,
    PropertyGroup,
)
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    PointerProperty,
    StringProperty,
)
import bpy
import json
from mathutils import Euler
from math import radians, pi, floor
from datetime import timedelta

bl_info = {
    "name": "MTA:SA Vehicle Motion Capture Tool",
    "author": "Matthew Chow <theportugueseplayer@gmail.com>",
    "version": (0, 1, 1),
    "blender": (2, 80, 0),
    "location": "View3D > Sidebar > Animate Tab > MTA VehMocap Tool",
    "description": "Parse the animation data from the JSON files generated by the Vehicle Motion Capture (VehMocap for short) resource for MTA:SA",
    "doc_url": "https://github.com/ThePortuguesePlayer/VehMocap-Importer-For-Blender",
    "category": "Animation",
    "support": "COMMUNITY",
}


class MTAVEHMOCAP_OT_RunAction(Operator):
    bl_idname = "object.mta_vehmocap"
    bl_label = "Parse JSON from VehMocap"
    bl_description = "Get the animation from the selected VehMocap JSON file"
    bl_options = {'REGISTER', 'UNDO'}

    rawdata: StringProperty()
    vehindex: IntProperty() = 0

    def execute(self, context):
        scene = context.scene
        data = json.loads(self.rawdata)[self.vehindex]
        # Add compatibility with the other vehicle types. -- TO DO
        dummies: dict
        if data["i"]["vT"] == "Automobile":
            dummies = {
                "veh": bpy.data.objects[scene.mta_vehmocap.veh_dummy],
                "lf": self.get_dummy(scene.mta_vehmocap.wheel_lf_dummy, scene, "lf"),
                "rf": self.get_dummy(scene.mta_vehmocap.wheel_rf_dummy, scene, "rf"),
                "lb": self.get_dummy(scene.mta_vehmocap.wheel_lb_dummy, scene, "lb"),
                "rb": self.get_dummy(scene.mta_vehmocap.wheel_rb_dummy, scene, "rb"),
            }
        for dummy in dummies:
            dummies[dummy].rotation_mode = "XYZ"
        camera = self.create_camera(
            data["i"]["vN"] + "-" + str(data["i"]["fC"]), scene)
        if True == True:  # THINK ABOUT THIS
            fpsscale = 1000 / scene.render.fps
            self.parseanimation(data, fpsscale, dummies,
                                camera, scene.frame_current)
            return {'FINISHED'}
        else:
            return {'CANCELED'}

    def get_dummy(self, dummyname: str, scene, key: str):
        if not dummyname:
            possibilities = {
                "lf": "wheel_lf_dummy",
                "rf": "wheel_rf_dummy",
                "lb": "wheel_lb_dummy",
                "rb": "wheel_rb_dummy",
            }
            dummyname = possibilities[key]
        if bpy.data.objects[dummyname] in bpy.data.objects[scene.mta_vehmocap.veh_dummy].children:
            return bpy.data.objects[dummyname]
        dummy = bpy.data.objects.new(dummyname, None)
        bpy.data.objects[scene.mta_vehmocap.veh_dummy].users_collection[0].objects.link(
            dummy)
        dummy.empty_display_type = "CUBE"
        dummy.empty_display_size = 0.05
        dummy.parent = bpy.data.objects[scene.mta_vehmocap.veh_dummy]
        return dummy

    def get_wheel_radius(self, dummies):
        wheels = {}
        for dummy in dummies:
            if dummies[dummy]:
                if len(dummies[dummy].children) == 1:
                    wheels[dummy] = dummies[dummy].children[0]
                    print("Got to len() check #1")
                elif dummy != "veh" and len(dummies[dummy].children) > 1:
                    chosen = None
                    size = 0.0
                    for child in dummies[dummy].children:
                        if abs(child.dimensions.y - child.dimensions.z) < 0.01 and child.dimensions.y > size:
                            chosen = child
                    wheels[dummy] = chosen
        print("Printing wheel objects found in dummies:")
        print(wheels)
        if len(wheels) == 1:
            print("Found 1 wheel object")
            for wheel in wheels:
                if wheels[wheel].dimensions.y <= wheels[wheel].dimensions.z:
                    size = wheels[wheel].dimensions.y * 0.5
                    return {"front": size, "back": size}
                else:
                    size = wheels[wheel].dimensions.z * 0.5
                    return {"front": size, "back": size}
        elif len(wheels) > 1:
            print("Found " + str(len(wheels)) + " wheel objects")
            sizes = {}
            for wheel in wheels:
                if wheel[1] == "f":
                    if wheels[wheel].dimensions.y <= wheels[wheel].dimensions.z:
                        sizes["front"] = wheels[wheel].dimensions.y * 0.5
                    else:
                        sizes["front"] = wheels[wheel].dimensions.z * 0.5
                elif wheel[1] == "b":
                    if wheels[wheel].dimensions.y <= wheels[wheel].dimensions.z:
                        sizes["back"] = wheels[wheel].dimensions.y * 0.5
                    else:
                        sizes["back"] = wheels[wheel].dimensions.z * 0.5
            return sizes
        else:
            print("Found no wheel objects. Radius set to the default of 0.34.")
            return {"front": 0.34, "back": 0.34}

    def parseanimation(self, data, fpsscale, dummies, camera, time):
        # Wheel Radius defaults to 0.34 if no model is found.
        wheelradius = self.get_wheel_radius(dummies)
        length = data["i"]["fC"]
        baseformat = {
            "angle_offset_x": 0.0,
            "angle_offset_y": 0.0,
            "angle_offset_z": 0.0,
            "x_history": 0.0,
            "y_history": 0.0,
            "z_history": 0.0,
        }
        rothistory = {
            "vehicle": dict(baseformat),
            "wheel_lf_dummy": dict(baseformat),
            "wheel_rf_dummy": dict(baseformat),
            "wheel_lb_dummy": dict(baseformat),
            "wheel_rb_dummy": dict(baseformat),
            "position": [0.0, 0.0, 0.0],
        }
        keyframe_counter = 1
        print("There are " + str(length) + " keyframes to set.")
        for _ in range(length):
            framedata = data[str(keyframe_counter)]
            print(str(keyframe_counter) + " at " + str(time))
            self.setkeyframes(dummies, framedata, time,
                              rothistory, camera, wheelradius)
            keyframe_counter += 1
            if keyframe_counter <= length:
                time += (framedata["fT"] / fpsscale)

    def create_camera(self, cam_name, scene):
        camera = bpy.data.cameras.new(cam_name)
        camobj = bpy.data.objects.new(cam_name, camera)
        bpy.data.objects[scene.mta_vehmocap.veh_dummy].users_collection[0].objects.link(
            camobj)
        target = bpy.data.objects.new("Target " + cam_name, None)
        bpy.data.objects[scene.mta_vehmocap.veh_dummy].users_collection[0].objects.link(
            target)
        target.empty_display_type = "PLAIN_AXES"
        target.empty_display_size = 0.35
        holder = bpy.data.objects.new("Holder " + cam_name, None)
        bpy.data.objects[scene.mta_vehmocap.veh_dummy].users_collection[0].objects.link(
            holder)
        holder.empty_display_type = "CUBE"
        camobj.parent = holder
        holder.constraints.new(type="TRACK_TO")
        holder.constraints["Track To"].target = target
        return {
            "camera": camera,
            "camobj": camobj,
            "holder": holder,
            "target": target,
        }

    def setkeyframes(self, dummies, framedata, attime, rothistory, camera, wheelradius):
        dist = dist = self.getvehicletraveldistance(framedata)
        self.setcomponentkeyframe(framedata["v"],
                                  dummies["veh"], attime, rothistory["vehicle"], rothistory["position"])
        self.setcomponentkeyframe(framedata["lf"],
                                  dummies["lf"], attime, rothistory["wheel_lf_dummy"], rothistory["position"], dist, wheelradius["front"])
        self.setcomponentkeyframe(framedata["rf"],
                                  dummies["rf"], attime, rothistory["wheel_rf_dummy"], rothistory["position"], dist, wheelradius["front"])
        self.setcomponentkeyframe(framedata["lb"],
                                  dummies["lb"], attime, rothistory["wheel_lb_dummy"], rothistory["position"], dist, wheelradius["back"])
        self.setcomponentkeyframe(framedata["rb"],
                                  dummies["rb"], attime, rothistory["wheel_rb_dummy"], rothistory["position"], dist, wheelradius["back"])
        self.setcamerakeyframe(camera, framedata, attime)

    def setcamerakeyframe(self, camera, framedata, attime):
        data = framedata["c"]
        camera["holder"].location[0] = data["cX"]
        camera["holder"].location[1] = data["cY"]
        camera["holder"].location[2] = data["cZ"]
        camera["holder"].keyframe_insert(data_path="location", frame=attime)
        camera["target"].location[0] = data["tX"]
        camera["target"].location[1] = data["tY"]
        camera["target"].location[2] = data["tZ"]
        camera["target"].keyframe_insert(data_path="location", frame=attime)
        camera["camobj"].rotation_euler = Euler(
            (radians(0.0), radians(0.0), radians(data["r"])), "XYZ")
        camera["camobj"].keyframe_insert(
            data_path="rotation_euler", frame=attime)
        camera["camera"].angle = radians(data["fov"])
        camera["camera"].keyframe_insert(data_path="lens", frame=attime)

    def setcomponentkeyframe(self, framedata, obj, attime, hodict, lastpos, dist=0.0, wheelradius=0.34):
        obj.location[0] = framedata["pX"]
        obj.location[1] = framedata["pY"]
        obj.location[2] = framedata["pZ"]
        obj.keyframe_insert(
            data_path="location", frame=attime)
        rX = framedata["rX"]
        rY = self.offsetrotationy(framedata["rY"], hodict)
        rZ = self.offsetrotationz(framedata["rZ"], hodict)
        if obj.name.startswith("wheel_l"):
            rX = self.offsetrotationwheel(True, rX, hodict, dist, wheelradius)
        elif obj.name.startswith("wheel_r"):
            rX = self.offsetrotationwheel(False, rX, hodict, dist, wheelradius)
        elif obj.name.startswith("wheel"):
            rX = self.offsetrotationwheel(True, rX, hodict, dist, wheelradius)
        else:
            rX = self.offsetrotationx(rX, hodict)
        obj.rotation_euler = Euler(
            (radians(rX), radians(
                rY), radians(rZ)),
            'XYZ')
        obj.keyframe_insert(
            data_path="rotation_euler", frame=attime)

    def getvehicletraveldistance(self, framedata):
        base = 0.02  # It's 1/50 seconds
        velocity = framedata["V"]  # Distance traveled in 0.02 seconds.
        frametime = framedata["fT"] * 0.001  # Frame time converted to seconds.
        # Returns distance traveled in [frametime].
        return frametime * velocity / base

    def offsetrotationz(self, val, dic):
        lastval = dic["z_history"]
        if (val + 90.0) < lastval:
            dic["angle_offset_z"] += 360.0
        elif (val - 90.0) > lastval:
            dic["angle_offset_z"] -= 360.0
        dic["z_history"] = val
        return val + dic["angle_offset_z"]

    def offsetrotationy(self, val, dic):
        lastval = dic["y_history"]
        if (val + 90.0) < lastval:
            dic["angle_offset_y"] += 360.0
        elif (val - 90.0) > lastval:
            dic["angle_offset_y"] -= 360.0
        dic["y_history"] = val
        return val + dic["angle_offset_y"]

    def offsetrotationx(self, val, dic):
        lastval = dic["x_history"]
        if (val + 180.0) < lastval:
            dic["angle_offset_x"] += 360.0
        elif (val - 180.0) > lastval:
            dic["angle_offset_x"] -= 360.0
        dic["x_history"] = val
        return val + dic["angle_offset_x"]

    def getwheelrotations(self, dist, radius):
        circonference = 2 * pi * radius
        return dist / circonference

    def oldoffsetrotationwheel(self, val, dic, dist, wheelradius):
        rotations = self.getwheelrotations(dist, wheelradius)
        tfr = rotations
        lastval = dic["x_history"]
        # This condition assumes the vehicle can't move fast enough in reverse to make a full wheel turn within a frame.
        if abs(rotations) >= 1.0:
            dic["angle_offset_x"] += (360.0 * floor(rotations))
            rotations -= floor(rotations)
        if (lastval + lastval*rotations) < val - 45:
            dic["angle_offset_x"] -= 360.0
        elif (lastval + lastval*rotations) > val + 45:
            dic["angle_offset_x"] += 360.0
        dic["x_history"] = val
        print([tfr, rotations, val, lastval, dic["x_history"]])
        return val + dic["angle_offset_x"]

    def offsetrotationwheel(self, isleftside, val, dic, dist, wheelradius):
        rotations = self.getwheelrotations(dist, wheelradius)
        lastval = dic["x_history"]
        if abs(rotations) >= 1.0:
            dic["angle_offset_x"] += (360.0 * floor(rotations))
            rotations -= floor(rotations)
        if dist >= 0:
            if val > lastval:
                dic["angle_offset_x"] += (val - lastval)
            elif val < lastval:
                dic["angle_offset_x"] += 360.0 + (val - lastval)
        elif dist < 0:
            if val > lastval:
                dic["angle_offset_x"] -= (val - lastval)
            elif val < lastval:
                dic["angle_offset_x"] -= (360.0 + (val - lastval))
        dic["x_history"] = val
        if isleftside:
            return dic["angle_offset_x"]
        else:
            return -dic["angle_offset_x"]


class MTAVEHMOCAP_Props(PropertyGroup):

    f_path: StringProperty(
        name="JSON File",
        subtype="FILE_PATH",
        default="C:/Program Files (x86)/MTA San Andreas 1.5/mods/deathmatch/resources/motiontracker/logs/",
        description="The JSON file, generated from the Vehicle Motion Capture MTA:SA resource, to process",
    )
    veh_index: IntProperty(
        name="Select Vehicle",
        description="Vehicle selection for when more than one vehicle was captured in a single file",
        default=1,
        # hard_min=1,
    )
    veh_dummy: StringProperty(
        name="Vehicle Dummy",
        description="The object to be animated",
    )
    wheel_lf_dummy: StringProperty(
        name="wheel_lf_dummy",
        description="Select the Front-Left wheel object to animate",
    )
    wheel_rf_dummy: StringProperty(
        name="wheel_rf_dummy",
        description="Select the Front-Right wheel object to animate",
    )
    wheel_lb_dummy: StringProperty(
        name="wheel_lb_dummy",
        description="Select the Back-Left wheel object to animate",
    )
    wheel_rb_dummy: StringProperty(
        name="wheel_rb_dummy",
        description="Select the Back-Right wheel object to animate",
    )


class MTAVEHMOCAP_PT_ui(Panel):
    bl_label = "MTA VehMocap Tool"
    bl_idname = "MTA_VEHMOCAP_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Animate"
    bl_context = "objectmode"
    bl_options = {'DEFAULT_CLOSED'}

    file_path: str
    file_vehname: list[str]
    file_vehtype: list[str]
    file_nominalkfps: list[int]
    file_duration: list[float]
    file_framecount: list[int]
    file_rawdata: str

    def draw(self, context):
        layout = self.layout
        # layout.use_property_split = True
        layout.use_property_decorate = False
        scene = context.scene

        col = layout.column(align=True)
        col.prop(scene.mta_vehmocap, "f_path")
        self.update_panel(scene, col, layout)

    def update_panel(self, scene, col, layout):
        validated = self.validate_file(scene)
        if validated == "VALIDATED":
            box = col.box()
            veh_count = len(self.file_vehname)
            # The vehicle selector needs a better solution.
            if veh_count > 1:
                box.prop(scene.mta_vehmocap, "veh_index")
            index: int
            if scene.mta_vehmocap.veh_index > veh_count:
                index = veh_count - 1
            elif scene.mta_vehmocap.veh_index <= 0:
                index = 0
            else:
                index = scene.mta_vehmocap.veh_index - 1
            sub = box.column(align=True)
            infostring = self.get_info_string(index)
            # Might need to improve this to make it look visually better.
            for infoline in infostring.split("\n"):
                row = sub.row(align=False)
                row.alignment = 'CENTER'
                row.label(text=infoline)
            box = layout.box()
            col = box.column(align=True)
            col.prop_search(scene.mta_vehmocap, "veh_dummy",
                            bpy.data, "objects", text="Vehicle")
            if scene.mta_vehmocap.veh_dummy and bpy.data.objects[scene.mta_vehmocap.veh_dummy]:
                if self.file_vehtype[index] == "Automobile":
                    col.prop_search(scene.mta_vehmocap, "wheel_lf_dummy",
                                    bpy.data, "objects", text="wheel_lf_dummy")
                    col.prop_search(scene.mta_vehmocap, "wheel_rf_dummy",
                                    bpy.data, "objects", text="wheel_rf_dummy")
                    col.prop_search(scene.mta_vehmocap, "wheel_lb_dummy",
                                    bpy.data, "objects", text="wheel_lb_dummy")
                    col.prop_search(scene.mta_vehmocap, "wheel_rb_dummy",
                                    bpy.data, "objects", text="wheel_rb_dummy")
                # Only spawning operator if at least the main object is selected.
                prop = layout.operator(
                    "object.mta_vehmocap", text="Import Animation", icon="GRAPH")
                prop.rawdata = self.file_rawdata
                prop.vehindex = index
        else:
            col.label(text=validated)

    def validate_file(self, scene):
        abspath = bpy.path.abspath(scene.mta_vehmocap.f_path)
        if path.isfile(abspath):
            self.file_path = abspath
            if path.splitext(abspath)[1] == ".json" or path.splitext(abspath)[1] == ".vmc":
                success = self.process_json_file()
                if success:
                    return "VALIDATED"
                return "This is not a VehMocap JSON file."
            return "This file type is not supported."
        return "Select a JSON file to process."

    def get_info_string(self, index: int):
        return \
            "Vehicle: " + str(self.file_vehname[index]) + "\n" + \
            "Keyframes Per Second: " + str(self.file_nominalkfps[index]) + "\n" + \
            "Duration: " + str(timedelta(seconds=self.file_duration[index])).rstrip("0").replace(":", "{}").format("h ", "m ") + "s\n" + \
            "Number of Keyframes: " + str(self.file_framecount[index])

    def process_json_file(self):
        data: dict
        with open(self.file_path, 'r') as jsonfile:
            self.file_rawdata = jsonfile.read()
            data = json.loads(self.file_rawdata)
        self.file_vehname = []
        self.file_nominalkfps = []
        self.file_framecount = []
        self.file_duration = []
        self.file_vehtype = []
        has_data = False
        for vehicle in data:
            if "i" in vehicle:
                self.file_vehname.append(vehicle["i"]["vN"])
                self.file_nominalkfps.append(vehicle["i"]["kfPS"])
                self.file_framecount.append(vehicle["i"]["fC"])
                self.file_duration.append(vehicle["i"]["d"])
                self.file_vehtype.append(vehicle["i"]["vT"])
                has_data = True
        return has_data

    def fetch_wheel_dummies(self, parentobj: str):
        children = {}
        for obj in bpy.data.objects[parentobj].children:
            if obj.name[:14] == "wheel_lf_dummy":
                children["lf"] = obj.name
            elif obj.name[:14] == "wheel_rf_dummy":
                children["rf"] = obj.name
            elif obj.name[:14] == "wheel_lb_dummy":
                children["lb"] = obj.name
            elif obj.name[:14] == "wheel_rb_dummy":
                children["rb"] = obj.name
        return children


classes = (
    MTAVEHMOCAP_OT_RunAction,
    MTAVEHMOCAP_PT_ui,
    MTAVEHMOCAP_Props
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.mta_vehmocap = PointerProperty(
        type=MTAVEHMOCAP_Props)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.mta_vehmocap


if __name__ == "__main__":
    register()
