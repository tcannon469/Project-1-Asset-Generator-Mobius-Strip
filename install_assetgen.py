# -*- coding: utf-8 -*-
# ##############################################
#          Install shelf button
# Execute it once to install and set the button on the Script Editor
#     import sys
#     sys.path.append("YOURPATH/AssetGen")
#     import install_assetgen
#     install_assetgen.install_assetgenButton()    
##############################################
import os
import maya.cmds as cmds
ProjectFolder = r"C:\Users\Mili\Downloads\AssetGen"
AssetGenFile = os.path.join(ProjectFolder, "assetgen.py")
Icon = os.path.join(ProjectFolder, "icons", "infinity_icon.png")


def install_assetgenButton():
    if not os.path.exists(AssetGenFile):
        cmds.error("Could not find script file:\n{}".format(AssetGenFile))
        return

    g_shelf_top = mel_eval("$tmpVar=$gShelfTopLevel")
    current_shelf = cmds.tabLayout(g_shelf_top, query=True, selectTab=True)
        
    command = f'''
import sys
import importlib

tool_path = r"{ProjectFolder}"
if tool_path not in sys.path:
    sys.path.append(tool_path)

import assetgen
importlib.reload(assetgen)
assetgen.show()
'''

    kwargs = {
        "parent": current_shelf,
        "label": "AssetGen",
        "command": command,
        "annotation": "Launch Asset Generator",
        "imageOverlayLabel": "∞",
        "sourceType": "python",
    }

    if os.path.exists(Icon):
        kwargs["image1"] = Icon

    cmds.shelfButton(**kwargs)
    print("Asset Generator shelf button installed.")


def mel_eval(command):
    import maya.mel as mel
    return mel.eval(command)


install_assetgenButton()