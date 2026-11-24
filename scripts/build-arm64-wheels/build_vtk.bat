@echo off
rem Build a VTK wheel for Windows ARM64 (no win_arm64 wheel is published on PyPI).
rem Uses VTK's own wheel CI configuration (.gitlab/ci/configure_wheel.cmake), restricted to the default
rem module set (no "build all modules", examples or tests) to shorten the build.
rem Usage: build_vtk.bat <python prefix (arm64 base install)> <VTK source dir> <build dir> <output wheel dir>
setlocal
set PYTHON_PREFIX=%~1
set VTK_SRC=%~2
set VTK_BUILD=%~3
set OUT=%~4
set CMAKE_CONFIGURATION=wheel_windows312_arm64
set CMAKE_BUILD_TYPE=Release

call "C:\Program Files\Microsoft Visual Studio\18\Community\VC\Auxiliary\Build\vcvarsarm64.bat" || exit /b 1
set PATH=C:\Program Files\Microsoft Visual Studio\18\Community\Common7\IDE\CommonExtensions\Microsoft\CMake\Ninja;%PATH%

rem -D options come before -C so they take precedence over the CI cache script
cmake -S "%VTK_SRC%" -B "%VTK_BUILD%" -G Ninja ^
  -DVTK_BUILD_ALL_MODULES:BOOL=OFF -DVTK_BUILD_EXAMPLES:BOOL=OFF -DVTK_BUILD_TESTING:STRING=OFF ^
  -DVTK_USE_LARGE_DATA:BOOL=OFF -DVTK_LINKER_FATAL_WARNINGS:BOOL=OFF -DVTK_ENABLE_CATALYST:BOOL=OFF ^
  -DCMAKE_C_COMPILER_LAUNCHER:STRING= -DCMAKE_CXX_COMPILER_LAUNCHER:STRING= -DVTK_WRAP_SERIALIZATION:BOOL=OFF -DVTK_EXTRA_COMPILER_WARNINGS:BOOL=OFF ^
  -DVTK_ENABLE_EXTRA_BUILD_WARNINGS:BOOL=OFF -DVTK_ENABLE_EXTRA_BUILD_WARNINGS_EVERYTHING:BOOL=OFF ^
  -DVTK_MODULE_ENABLE_VTK_RenderingOpenXR:STRING=NO -DVTK_BUILD_PYI_FILES:BOOL=OFF ^
  -C "%VTK_SRC%\.gitlab\ci\configure_wheel.cmake" || exit /b 1
cmake --build "%VTK_BUILD%" || exit /b 1

cd /d "%VTK_BUILD%"
if not exist wheel-venv "%PYTHON_PREFIX%\python.exe" -m venv wheel-venv
wheel-venv\Scripts\python.exe -m pip install -q setuptools wheel || exit /b 1
wheel-venv\Scripts\python.exe setup.py bdist_wheel || exit /b 1
copy /y dist\*.whl "%OUT%" || exit /b 1
