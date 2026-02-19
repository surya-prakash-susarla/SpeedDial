import os
from setuptools import setup

VERSION = open(os.path.join(os.path.dirname(__file__), "VERSION")).read().strip()

APP = ["speeddial.py"]

OPTIONS = {
    "argv_emulation": False,
    "packages": [],
    "plist": {
        "LSUIElement": True,
        "CFBundleName": "SpeedDial",
        "CFBundleDisplayName": "SpeedDial",
        "CFBundleIdentifier": "com.suryaprakash.speeddial",
        "CFBundleVersion": VERSION,
        "CFBundleShortVersionString": VERSION,
        "NSHighResolutionCapable": True,
        "NSAccessibilityUsageDescription": "SpeedDial needs Accessibility access to capture global hotkeys and switch between windows.",
    },
}

setup(
    name="SpeedDial",
    app=APP,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
