# test_libcurl_email

Minimal sample that sends an email over SMTPS with libcurl (from vcpkg), built with CMake and gcc-16/g++-16.

## Build

Build out-of-tree, like mir2x. `build.py` clones and bootstraps vcpkg into `<build-dir>/vcpkg`,
builds curl/openssl/zlib with `gcc-16`/`g++-16` (via `CC`/`CXX`), then builds and installs `send_email`.

```sh
mkdir -p ~/b_test_libcurl_email && cd ~/b_test_libcurl_email
~/test_libcurl_email/build.py            # add --fresh for a clean configure
```

Options: `--vcpkg-prefix <existing vcpkg root>`, `--build-dir`, `--build-type`, `--parallel N`,
`--c-compiler`, `--cxx-compiler` (default `gcc-16` / `g++-16`).

Output: `<build-dir>/install/bin/send_email`

### MinGW (Windows, MSYS2 UCRT64)

In an MSYS2 UCRT64 shell with GCC 16 (`pacman -S mingw-w64-ucrt-x86_64-{toolchain,cmake,ninja,python,git}`):

```sh
python3 /path/to/test_libcurl_email/build.py --build-dir ~/b_test_libcurl_email
```

`build.py` detects MSYS2 (`MSYSTEM`) and uses triplet `x64-mingw-static` (also as host triplet) with MSYS2's `gcc`/`g++`.
The resulting `send_email.exe` is fully static (only Windows system DLLs) and uses Schannel, so TLS uses the Windows certificate store.

### GitHub Actions

`.github/workflows/build.yml` builds on Ubuntu (gcc-16) and Windows MSYS2 UCRT64 on every push,
and uploads `send_email-linux` / `send_email-windows` artifacts.

## Send with QQ mail

QQ mail requires an **authorization code** (QQ邮箱 → 设置 → 账户 → 开启 POP3/SMTP 服务 → 生成授权码),
not your QQ login password.

```sh
export SMTP_PASSWORD='<authorization code>'
./install/bin/send_email you@qq.com friend@example.com "测试 subject" "hello 你好"

# multiple recipients: comma-separated
./install/bin/send_email you@qq.com a@example.com,b@example.org "subject" "body"
```

Environment variables:

| Variable        | Description                                              |
|-----------------|----------------------------------------------------------|
| `SMTP_PASSWORD` | Required. SMTP password / QQ authorization code          |
| `SMTP_URL`      | Optional. Default `smtps://smtp.qq.com:465`              |
| `SMTP_VERBOSE`  | Optional. Set to any value to print the SMTP session     |
