#!/usr/bin/env python3
"""Automated build, test, version bump, and release pipeline for Lucent.

Usage:
    python tools/build_release.py [--bump {patch,minor,major}] [--version X.Y.Z] [--no-release] [--push]

Options:
    --bump {patch,minor,major}  Automatically bump version in lucent/config.py
    --version X.Y.Z             Set explicit version
    --no-release                Build binaries and run tests without creating a GitHub release
    --push                      Push git commit and tag to origin remote
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def run_cmd(cmd, cwd=ROOT, check=True):
    print(f"--> Executing: {cmd}")
    res = subprocess.run(cmd, shell=True, cwd=cwd)
    if check and res.returncode != 0:
        print(f"Error: Command failed with exit code {res.returncode}: {cmd}", file=sys.stderr)
        sys.exit(res.returncode)
    return res.returncode


def get_current_version() -> str:
    config_path = os.path.join(ROOT, "lucent", "config.py")
    with open(config_path, "r", encoding="utf-8") as f:
        content = f.read()
    match = re.search(r'APP_VERSION\s*=\s*["\']([^"\']+)["\']', content)
    if not match:
        raise RuntimeError("Could not find APP_VERSION in lucent/config.py")
    return match.group(1)


def bump_version_string(curr: str, bump_type: str) -> str:
    parts = [int(p) for p in curr.split(".")]
    while len(parts) < 3:
        parts.append(0)
    if bump_type == "patch":
        parts[2] += 1
    elif bump_type == "minor":
        parts[1] += 1
        parts[2] = 0
    elif bump_type == "major":
        parts[0] += 1
        parts[1] = 0
        parts[2] = 0
    return ".".join(str(p) for p in parts)


def set_version(new_ver: str):
    config_path = os.path.join(ROOT, "lucent", "config.py")
    with open(config_path, "r", encoding="utf-8") as f:
        content = f.read()
    new_content = re.sub(r'APP_VERSION\s*=\s*["\']([^"\']+)["\']', f'APP_VERSION = "{new_ver}"', content)
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"Updated APP_VERSION in lucent/config.py to {new_ver}")


def run_tests():
    print("\n=== Running Test Suite ===")
    py_exec = sys.executable
    run_cmd(f'"{py_exec}" -m pytest -v tests/')
    print("=== All Tests Passed ===\n")


def build_binaries():
    print("\n=== Building Application Bundle & Installers ===")
    dist_dir = os.path.join(ROOT, "dist")
    os.makedirs(dist_dir, exist_ok=True)

    # 1. Build core Lucent folder distribution
    run_cmd("pyinstaller --noconfirm Lucent.spec")

    # 2. Package Lucent-Portable.zip
    portable_zip = os.path.join(dist_dir, "Lucent-Portable.zip")
    if os.path.exists(portable_zip):
        os.remove(portable_zip)

    print("Compressing dist/Lucent into Lucent-Portable.zip...")
    with zipfile.ZipFile(portable_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(os.path.join(dist_dir, "Lucent")):
            for file in files:
                full_path = os.path.join(root, file)
                arcname = os.path.relpath(full_path, os.path.join(dist_dir, "Lucent"))
                zipf.write(full_path, arcname)
    print(f"Generated Lucent-Portable.zip ({os.path.getsize(portable_zip)} bytes)")

    # 3. Build LucentInstaller-Lite.exe
    run_cmd("pyinstaller --noconfirm LucentInstaller-Lite.spec")

    # 4. Build Full LucentInstaller.exe
    run_cmd("pyinstaller --noconfirm LucentInstaller.spec")

    print("=== Binary Build Complete ===\n")


def main():
    parser = argparse.ArgumentParser(description="Lucent automated build and release tool.")
    parser.add_argument("--bump", choices=["patch", "minor", "major"], help="Bump version by component")
    parser.add_argument("--version", help="Explicit version string (e.g. 0.9.1)")
    parser.add_argument("--no-release", action="store_true", help="Skip creating a GitHub release")
    parser.add_argument("--push", action="store_true", help="Push commit and tags to git remote")
    args = parser.parse_args()

    curr_ver = get_current_version()
    print(f"Current version: v{curr_ver}")

    target_ver = curr_ver
    if args.version:
        target_ver = args.version.lstrip("v")
    elif args.bump:
        target_ver = bump_version_string(curr_ver, args.bump)

    if target_ver != curr_ver:
        print(f"Bumping version from v{curr_ver} -> v{target_ver}")
        set_version(target_ver)

    # 1. Verification & Testing
    run_tests()

    # 2. Build All Artifacts
    build_binaries()

    # 3. Git commit & tag if version changed
    tag_name = f"v{target_ver}"
    if target_ver != curr_ver:
        run_cmd(f'git add lucent/config.py installer.py lucent/hub.py main.py')
        run_cmd(f'git commit -m "Bump version to v{target_ver}"')
        run_cmd(f'git tag -a {tag_name} -m "Lucent {tag_name} release"')

    if args.push:
        run_cmd("git push origin main")
        if target_ver != curr_ver:
            run_cmd(f"git push origin {tag_name}")

    # 4. GitHub Release
    if not args.no_release:
        dist_dir = os.path.join(ROOT, "dist")
        installer = os.path.join(dist_dir, "LucentInstaller.exe")
        lite_installer = os.path.join(dist_dir, "LucentInstaller-Lite.exe")
        portable_zip = os.path.join(dist_dir, "Lucent-Portable.zip")

        notes_file = os.path.join(ROOT, "README.md")
        title = f"Lucent {tag_name}"

        # Check if tag already released
        check_release = subprocess.run(f"gh release view {tag_name}", shell=True, capture_output=True)
        if check_release.returncode == 0:
            print(f"Release {tag_name} already exists. Uploading/replacing assets...")
            run_cmd(f'gh release upload {tag_name} "{installer}" "{lite_installer}" "{portable_zip}" --clobber')
        else:
            print(f"Creating GitHub release {tag_name}...")
            run_cmd(
                f'gh release create {tag_name} "{installer}" "{lite_installer}" "{portable_zip}" '
                f'--title "{title}" --notes-file "{notes_file}"'
            )

    print(f"\n[SUCCESS] Completed build and release pipeline for {tag_name}!")


if __name__ == "__main__":
    main()
