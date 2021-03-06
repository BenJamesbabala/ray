cmake_minimum_required(VERSION 2.8)

project(plasma)

# Recursively include common
include(${CMAKE_CURRENT_LIST_DIR}/../common/cmake/Common.cmake)

if(APPLE)
  SET(CMAKE_SHARED_LIBRARY_SUFFIX ".so")
endif(APPLE)

include_directories("${PYTHON_INCLUDE_DIRS}" thirdparty)

set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} --std=c99 -D_XOPEN_SOURCE=500 -D_POSIX_C_SOURCE=200809L")

# Compile flatbuffers

set(PLASMA_FBS_SRC "${CMAKE_CURRENT_LIST_DIR}/format/plasma.fbs")
set(OUTPUT_DIR ${CMAKE_CURRENT_LIST_DIR}/format/)

add_custom_target(gen_plasma_fbs ALL)

add_custom_command(
  TARGET gen_plasma_fbs
  COMMAND ${FLATBUFFERS_COMPILER} -a -c -o ${OUTPUT_DIR} ${PLASMA_FBS_SRC}
  DEPENDS ${FBS_DEPENDS}
  COMMENT "Running flatc compiler on ${PLASMA_FBS_SRC}"
  VERBATIM)

if(UNIX AND NOT APPLE)
  link_libraries(rt)
endif()

include_directories("${CMAKE_CURRENT_LIST_DIR}/")
include_directories("${CMAKE_CURRENT_LIST_DIR}/../")

add_library(plasma SHARED
  plasma.c
  plasma_extension.c
  plasma_protocol.c
  plasma_client.c
  thirdparty/xxhash.c
  fling.c)

add_dependencies(plasma gen_plasma_fbs)

get_filename_component(PYTHON_SHARED_LIBRARY ${PYTHON_LIBRARIES} NAME)
if(APPLE)
  add_custom_command(TARGET plasma
                     POST_BUILD COMMAND ${CMAKE_INSTALL_NAME_TOOL} -change ${PYTHON_SHARED_LIBRARY} ${PYTHON_LIBRARIES} libplasma.so)
endif(APPLE)

target_link_libraries(plasma ${COMMON_LIB} ${PYTHON_LIBRARIES} ${FLATBUFFERS_STATIC_LIB})

set_source_files_properties(thirdparty/dlmalloc.c PROPERTIES COMPILE_FLAGS -Wno-all)

add_executable(plasma_store
  plasma_store.c
  plasma.c
  plasma_protocol.c
  eviction_policy.c
  fling.c
  malloc.c)

add_dependencies(plasma_store hiredis gen_plasma_fbs)

target_link_libraries(plasma_store common ${FLATBUFFERS_STATIC_LIB})

add_library(plasma_lib STATIC
  plasma_client.c
  plasma.c
  plasma_protocol.c
  fling.c
  thirdparty/xxhash.c)

target_link_libraries(plasma_lib common ${FLATBUFFERS_STATIC_LIB})
add_dependencies(plasma_lib gen_plasma_fbs)

add_executable(plasma_manager
  plasma_manager.c)

target_link_libraries(plasma_manager common plasma_lib ${FLATBUFFERS_STATIC_LIB})

add_library(plasma_client SHARED plasma_client.c)

target_link_libraries(plasma_client common plasma_lib ${FLATBUFFERS_STATIC_LIB})

define_test(client_tests plasma_lib)
define_test(manager_tests plasma_lib plasma_manager.c)
define_test(serialization_tests plasma_lib)
