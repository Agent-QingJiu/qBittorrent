import pathlib
import re
import shutil
import subprocess
import sys

payload, sysroot, prefix, gcc = map(pathlib.Path, sys.argv[1:])
lib = payload / "lib"
lib.mkdir(exist_ok=True)
system = {
    "ld-linux-x86-64.so.2", "libc.so.6", "libpthread.so.0", "librt.so.1",
    "libdl.so.2", "libm.so.6", "libresolv.so.2", "libutil.so.1",
}
providers = [prefix / "lib", prefix / "lib64", gcc]

def readelf(flag, file):
    return subprocess.check_output(["readelf", flag, file], text=True)

pending = list((payload / "bin").glob("qbt*"))
pending.extend((payload / "bin").glob("qbittorrent-nox"))
pending.extend((payload / "plugins").rglob("*.so"))
checked = set()
while pending:
    file = pending.pop(0)
    if file in checked:
        continue
    checked.add(file)
    header = readelf("-hW", file)
    if "ELF64" not in header or "Advanced Micro Devices X86-64" not in header:
        raise SystemExit(f"不兼容的 ELF 架构：{file}")
    properties = readelf("-nW", file)
    if re.search(r"x86 ISA needed:.*x86-64-v[34]", properties):
        raise SystemExit(f"ELF 要求 Sandy Bridge 不支持的指令集：{file}")
    interpreter = re.search(r"Requesting program interpreter: (.*?)\]", readelf("-lW", file))
    if interpreter and interpreter[1] != "/lib64/ld-linux-x86-64.so.2":
        raise SystemExit(f"不兼容的加载器：{file}: {interpreter[1]}")
    versions = re.findall(r"Name: GLIBC_([\w.]+)", readelf("-VW", file))
    for version in versions:
        if not re.fullmatch(r"\d+(\.\d+)+", version) or tuple(map(int, version.split("."))) > (2, 20):
            raise SystemExit(f"超出 DSM GLIBC 2.20：{file}: GLIBC_{version}")
    needed = re.findall(r"\(NEEDED\).*?\[(.*?)\]", readelf("-dW", file))
    print(file.relative_to(payload), "=>", " ".join(needed), flush=True)
    for name in needed:
        if name in system:
            if not any((sysroot / path / name).exists() for path in ("lib", "lib64", "usr/lib")):
                raise SystemExit(f"目标系统缺少运行库：{name}")
            continue
        if "/" in name:
            raise SystemExit(f"非法运行库名称：{name}")
        destination = lib / name
        if not destination.is_file():
            source = next((directory / name for directory in providers if (directory / name).is_file()), None)
            if source is None:
                raise SystemExit(f"缺少受控运行库：{file}: {name}")
            shutil.copyfile(source, destination)
            destination.chmod(0o755)
        pending.append(destination)
    depth = len(file.relative_to(payload).parts) - 1
    relative = "../" * depth + "lib"
    subprocess.run(["patchelf", "--force-rpath", "--set-rpath", f"$ORIGIN/{relative}", file], check=True)
