cmake_minimum_required(VERSION 3.20)
project(gbm_renderer C)
set(CMAKE_C_STANDARD 11)
set(CMAKE_MSVC_RUNTIME_LIBRARY "MultiThreaded$<$<CONFIG:Debug>:Debug>")
set(MGBA_SOURCE "${CMAKE_CURRENT_SOURCE_DIR}/../../third_party/mgba-source/mgba-e31759b" CACHE PATH "Pinned mGBA source")
add_library(gbm_renderer SHARED renderer.c
 "${MGBA_SOURCE}/src/gba/renderers/common.c"
 "${MGBA_SOURCE}/src/gba/renderers/video-software.c"
 "${MGBA_SOURCE}/src/gba/renderers/software-bg.c"
 "${MGBA_SOURCE}/src/gba/renderers/software-mode0.c"
 "${MGBA_SOURCE}/src/gba/renderers/software-obj.c")
target_include_directories(gbm_renderer PRIVATE "${MGBA_SOURCE}/include" "${MGBA_SOURCE}/src")
target_compile_definitions(gbm_renderer PRIVATE BUILD_STATIC COLOR_16_BIT COLOR_5_6_5 NDEBUG DISABLE_THREADING _CRT_SECURE_NO_WARNINGS)
