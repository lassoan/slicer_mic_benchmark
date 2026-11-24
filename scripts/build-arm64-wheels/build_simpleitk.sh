#!/bin/bash
# Build a SimpleITK wheel for Windows ARM64 (no win_arm64 wheel is published on PyPI).
# Same recipe as Slicer's External_python-SimpleITK.cmake: SimpleITK superbuild (ITK + SimpleITK + SWIG),
# then build the wheel with scikit-build using the superbuild results.
# Usage: build_simpleitk.sh <python.exe (arm64)> <build dir> <output wheel dir> [version]
set -euo pipefail
PY=$1
BUILD=$2
OUT=$3
VER=${4:-2.5.5}
GEN="Visual Studio 18 2026"

mkdir -p "$BUILD" "$OUT"
cd "$BUILD"
if [ ! -d src ]; then
  "$PY" -m pip download --no-deps --no-binary :all: "simpleitk==$VER" -d sdist
  mkdir -p src && tar -xzf sdist/simpleitk-$VER.tar.gz -C src --strip-components=1
  # SimpleITK's superbuild calls sitk_ExternalProject_Add_Empty with one argument, which fails with this CMake version
  cmake -DSOURCE_DIR="$BUILD/src" -P "$(dirname "$0")/patch_simpleitk.cmake"
fi
SRC_W=$(cygpath -m "$BUILD/src")
SB_W=$(cygpath -m "$BUILD/sb")
cmake -S "$SRC_W/SimpleITK/SuperBuild" -B "$SB_W" -G "$GEN" -A ARM64 \
  -DBUILD_EXAMPLES=OFF -DBUILD_TESTING=OFF -DBUILD_DOXYGEN=OFF -DWRAP_DEFAULT=OFF \
  -DSimpleITK_BUILD_STRIP=ON -DSimpleITK_BUILD_DISTRIBUTE=ON -DSimpleITK_GIT_PROTOCOL=https -DSKBUILD=ON
cmake --build "$SB_W" --config Release -- -m

export CMAKE_GENERATOR="$GEN"
export CMAKE_GENERATOR_PLATFORM=ARM64
export SKBUILD_CONFIGURE_OPTIONS="-DSimpleITK_DIR:PATH=$SB_W/SimpleITK-build -DITK_DIR:PATH=$SB_W/ITK-prefix/lib/cmake/ITK -DSWIG_EXECUTABLE:FILEPATH=$SB_W/swigwin/swig.exe -DSimpleITK_PYTHON_USE_LIMITED_API:BOOL=OFF"
cd "$BUILD/src"
"$PY" -m pip wheel . --no-deps --wheel-dir "$(cygpath -m "$OUT")"
ls -la "$OUT"
