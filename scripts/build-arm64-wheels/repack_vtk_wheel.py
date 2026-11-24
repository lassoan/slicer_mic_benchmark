"""Add VTK's DLLs to a VTK wheel built with `setup.py bdist_wheel`, using the same layout as the official wheels.

Official VTK wheels are repaired with delvewheel (DLLs in vtk.libs/, and a patch at the top of
vtkmodules/__init__.py that adds that directory to the DLL search path). delvewheel 1.x fails on Windows ARM64
because it tries to resolve API-set DLLs (ext-ms-win-*), so do the same steps directly.

Usage: python repack_vtk_wheel.py <unpacked wheel dir> <VTK build bin dir> <MSVC CRT dir> <output dir>
Then: python -m wheel pack <unpacked wheel dir> -d <output dir>
"""

import shutil
import sys
from pathlib import Path

PATCH = '''
# start delvewheel-style patch (added by repack_vtk_wheel.py)
def _vtk_libs_patch():
    import os
    libs_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, 'vtk.libs'))
    if os.path.isdir(libs_dir):
        os.add_dll_directory(libs_dir)


_vtk_libs_patch()
del _vtk_libs_patch
# end patch
'''


def main():
    wheel_dir, bin_dir, crt_dir = (Path(a) for a in sys.argv[1:4])
    libs = wheel_dir / "vtk.libs"
    libs.mkdir(exist_ok=True)
    for dll in list(bin_dir.glob("*.dll")) + [crt_dir / "msvcp140.dll", crt_dir / "vcruntime140_1.dll"]:
        shutil.copy2(dll, libs / dll.name)
    init = wheel_dir / "vtkmodules" / "__init__.py"
    text = init.read_text()
    if "_vtk_libs_patch" not in text:
        marker = "from __future__ import absolute_import\n"
        text = text.replace(marker, marker + PATCH, 1)
        init.write_text(text)
    print(f"Added {len(list(libs.glob('*.dll')))} DLLs to {libs}")


if __name__ == "__main__":
    main()
