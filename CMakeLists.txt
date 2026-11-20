cmake_minimum_required(VERSION 3.21)

if(NOT DEFINED CMAKE_TOOLCHAIN_FILE AND DEFINED ENV{VCPKG_ROOT})
    set(CMAKE_TOOLCHAIN_FILE "$ENV{VCPKG_ROOT}/scripts/buildsystems/vcpkg.cmake" CACHE FILEPATH "vcpkg toolchain file")
endif()

project(test_libcurl_email LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 23)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU" AND CMAKE_CXX_COMPILER_VERSION VERSION_LESS 16)
    message(FATAL_ERROR "GCC 16 or newer is required, found ${CMAKE_CXX_COMPILER_VERSION}")
endif()

find_package(CURL CONFIG REQUIRED)

add_executable(send_email src/send_email.cpp)
target_link_libraries(send_email PRIVATE CURL::libcurl)

# no runtime dependency on the libstdc++/libgcc of the build machine
if(MINGW)
    target_link_options(send_email PRIVATE -static -static-libgcc -static-libstdc++)
    # std::print's Windows console support lives in libstdc++exp on MinGW
    target_link_libraries(send_email PRIVATE stdc++exp)
else()
    target_link_options(send_email PRIVATE -static-libgcc -static-libstdc++)
endif()

install(TARGETS send_email RUNTIME DESTINATION bin)
