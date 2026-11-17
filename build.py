#!/usr/bin/env python3
import argparse
import os
import shutil
import subprocess
from pathlib import Path


SOURCE_DIR = Path(__file__).resolve().parent


def run(args, *, env=None):
    print("+ " + " ".join(str(a) for a in args), flush=True)
    subprocess.run([str(a) for a in args], check=True, env=env)


def parse_args():
    parser = argparse.ArgumentParser(description="Build test_libcurl_email with vcpkg.")
    parser.add_argument("--vcpkg-prefix", type=Path, help="Use an existing vcpkg root instead of bootstrapping <build-dir>/vcpkg.")
    parser.add_argument("--build-dir", type=Path, default=Path.cwd(), help="Local build root. Defaults to the current directory.")
    parser.add_argument("--fresh", action="store_true", help="Delete <build-dir>/build before configuring.")
    parser.add_argument("--triplet", default="x64-linux", help="VCPKG_TARGET_TRIPLET.")
    parser.add_argument("--c-compiler", default="gcc-16", help="C compiler for vcpkg ports and the project.")
    parser.add_argument("--cxx-compiler", default="g++-16", help="C++ compiler for vcpkg ports and the project.")
    parser.add_argument("--build-type", default="Release", help="CMAKE_BUILD_TYPE.")
    parser.add_argument("--parallel", type=int, help="Number of parallel jobs.")
    return parser.parse_args()


def bootstrap_vcpkg(vcpkg_root):
    if not vcpkg_root.exists():
        run(["git", "clone", "https://github.com/microsoft/vcpkg.git", vcpkg_root])
    if not (vcpkg_root / "vcpkg").is_file():
        run([vcpkg_root / "bootstrap-vcpkg.sh", "-disableMetrics"])


def main():
    args = parse_args()
    build_root = args.build_dir.expanduser().resolve()
    cmake_build_dir = build_root / "build"
    install_prefix = build_root / "install"
    build_root.mkdir(parents=True, exist_ok=True)

    if args.vcpkg_prefix:
        vcpkg_root = args.vcpkg_prefix.expanduser().resolve()
    else:
        vcpkg_root = build_root / "vcpkg"
        bootstrap_vcpkg(vcpkg_root)

    if args.fresh:
        shutil.rmtree(cmake_build_dir, ignore_errors=True)

    # CC/CXX are inherited by vcpkg port builds, so curl/openssl/zlib also use gcc-16
    env = os.environ.copy()
    env["CC"] = shutil.which(args.c_compiler) or args.c_compiler
    env["CXX"] = shutil.which(args.cxx_compiler) or args.cxx_compiler
    if args.parallel:
        env["VCPKG_MAX_CONCURRENCY"] = str(args.parallel)

    run([
        "cmake",
        "-S", SOURCE_DIR,
        "-B", cmake_build_dir,
        f"-DCMAKE_BUILD_TYPE={args.build_type}",
        f"-DCMAKE_TOOLCHAIN_FILE={vcpkg_root / 'scripts/buildsystems/vcpkg.cmake'}",
        f"-DVCPKG_TARGET_TRIPLET={args.triplet}",
        f"-DVCPKG_INSTALLED_DIR={cmake_build_dir / 'vcpkg_installed'}",
        f"-DCMAKE_CXX_COMPILER={env['CXX']}",
        f"-DCMAKE_INSTALL_PREFIX={install_prefix}",
        "-DCMAKE_EXPORT_COMPILE_COMMANDS=ON",
    ], env=env)

    build_args = ["cmake", "--build", cmake_build_dir, "--parallel"]
    if args.parallel:
        build_args.append(str(args.parallel))
    run(build_args, env=env)
    run(["cmake", "--install", cmake_build_dir], env=env)

    print(f"Done: {install_prefix / 'bin/send_email'}", flush=True)


if __name__ == "__main__":
    main()
