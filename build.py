#!/usr/bin/env python3
import argparse
import os
import platform
import shutil
import subprocess
from pathlib import Path


SOURCE_DIR = Path(__file__).resolve().parent


def run(args, *, env=None):
    print("+ " + " ".join(str(a) for a in args), flush=True)
    subprocess.run([str(a) for a in args], check=True, env=env)


def is_windows():
    return platform.system() == "Windows" or platform.system().startswith(("MINGW", "MSYS", "CYGWIN"))


def is_mingw():
    # MSYS2 shells (UCRT64, MINGW64, CLANG64, ...) export MSYSTEM
    return bool(os.environ.get("MSYSTEM")) or platform.system().startswith(("MINGW", "MSYS"))


def default_triplet():
    if is_mingw():
        return "x64-mingw-static"
    return "x64-linux"


def parse_args():
    mingw = is_mingw()
    parser = argparse.ArgumentParser(description="Build test_libcurl_email with vcpkg.")
    parser.add_argument("--vcpkg-prefix", type=Path, help="Use an existing vcpkg root instead of bootstrapping <build-dir>/vcpkg.")
    parser.add_argument("--build-dir", type=Path, default=Path.cwd(), help="Local build root. Defaults to the current directory.")
    parser.add_argument("--fresh", action="store_true", help="Delete <build-dir>/build before configuring.")
    parser.add_argument("--triplet", help="VCPKG_TARGET_TRIPLET. Defaults to x64-linux, or x64-mingw-static in an MSYS2 shell.")
    parser.add_argument("--host-triplet", help="VCPKG_HOST_TRIPLET. Defaults to the target triplet for MinGW.")
    parser.add_argument("--c-compiler", default=None if mingw else "gcc-16",
                        help="C compiler. Defaults to gcc-16 on Linux, MSYS2's gcc on MinGW.")
    parser.add_argument("--cxx-compiler", default=None if mingw else "g++-16",
                        help="C++ compiler. Defaults to g++-16 on Linux, MSYS2's g++ on MinGW.")
    parser.add_argument("--build-type", default="Release", help="CMAKE_BUILD_TYPE.")
    parser.add_argument("--parallel", type=int, help="Number of parallel jobs.")
    return parser.parse_args()


def bootstrap_vcpkg(vcpkg_root):
    if not vcpkg_root.exists():
        run(["git", "clone", "https://github.com/microsoft/vcpkg.git", vcpkg_root])

    if is_windows():
        if not (vcpkg_root / "vcpkg.exe").is_file():
            run([os.environ.get("COMSPEC") or "cmd", "/c", vcpkg_root / "bootstrap-vcpkg.bat", "-disableMetrics"])
    elif not (vcpkg_root / "vcpkg").is_file():
        run([vcpkg_root / "bootstrap-vcpkg.sh", "-disableMetrics"])


def main():
    args = parse_args()
    build_root = args.build_dir.expanduser().resolve()
    cmake_build_dir = build_root / "build"
    install_prefix = build_root / "install"
    build_root.mkdir(parents=True, exist_ok=True)

    triplet = args.triplet or os.environ.get("VCPKG_DEFAULT_TRIPLET") or default_triplet()
    host_triplet = args.host_triplet or os.environ.get("VCPKG_DEFAULT_HOST_TRIPLET")
    if not host_triplet and "mingw" in triplet:
        # otherwise vcpkg picks x64-windows as host triplet, which needs MSVC
        host_triplet = triplet

    if args.vcpkg_prefix:
        vcpkg_root = args.vcpkg_prefix.expanduser().resolve()
    else:
        vcpkg_root = build_root / "vcpkg"
        bootstrap_vcpkg(vcpkg_root)

    if args.fresh:
        shutil.rmtree(cmake_build_dir, ignore_errors=True)

    # CC/CXX are inherited by vcpkg port builds, so curl/openssl/zlib also use the same compiler
    env = os.environ.copy()
    if args.c_compiler:
        env["CC"] = shutil.which(args.c_compiler) or args.c_compiler
    if args.cxx_compiler:
        env["CXX"] = shutil.which(args.cxx_compiler) or args.cxx_compiler
    if args.parallel:
        env["VCPKG_MAX_CONCURRENCY"] = str(args.parallel)

    configure_args = [
        "cmake",
        "-S", SOURCE_DIR,
        "-B", cmake_build_dir,
        f"-DCMAKE_BUILD_TYPE={args.build_type}",
        f"-DCMAKE_TOOLCHAIN_FILE={vcpkg_root / 'scripts/buildsystems/vcpkg.cmake'}",
        f"-DVCPKG_TARGET_TRIPLET={triplet}",
        f"-DVCPKG_INSTALLED_DIR={cmake_build_dir / 'vcpkg_installed'}",
        f"-DCMAKE_INSTALL_PREFIX={install_prefix}",
        "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON",
    ]
    if host_triplet:
        configure_args.append(f"-DVCPKG_HOST_TRIPLET={host_triplet}")
    if "CXX" in env and args.cxx_compiler:
        configure_args.append(f"-DCMAKE_CXX_COMPILER={env['CXX']}")
    run(configure_args, env=env)

    build_args = ["cmake", "--build", cmake_build_dir, "--config", args.build_type, "--parallel"]
    if args.parallel:
        build_args.append(str(args.parallel))
    run(build_args, env=env)
    run(["cmake", "--install", cmake_build_dir, "--config", args.build_type], env=env)

    exe_name = "send_email.exe" if "mingw" in triplet or "windows" in triplet else "send_email"
    print(f"Done: {install_prefix / 'bin' / exe_name}", flush=True)


if __name__ == "__main__":
    main()
