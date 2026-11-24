file(READ "${SOURCE_DIR}/CMakeLists.txt" content)
string(REGEX REPLACE "sitk_ExternalProject_Add_Empty\\(([ \t\r\n]*)SimpleITK-superbuild([ \t\r\n]*)\\)"
  "sitk_ExternalProject_Add_Empty(\\1SimpleITK-superbuild \"\"\\2)" content "${content}")
file(WRITE "${SOURCE_DIR}/CMakeLists.txt" "${content}")
