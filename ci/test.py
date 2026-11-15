"""在 Synology GLIBC 2.20 根目录中测试最终 SPK，模拟 DSM 套件中心调用。"""
import hashlib
import http.cookiejar
import json
import os
import pathlib
import shutil
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

dist, sysroot, qt_probe = map(pathlib.Path, sys.argv[1:])
spk, = dist.glob("*.spk")
target = "/volume1/@appstore/qBittorrent"
store = "/volume1/@appdata/qBittorrent-native"
profile = store + "/Profile/qBittorrent"
config = profile + "/config/qBittorrent.conf"

def run(*args):
    subprocess.run(args, check=True)

def wait_for(check, seconds=60):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        try:
            result = check()
            if result:
                return result
        except (urllib.error.URLError, ConnectionError):
            pass
        time.sleep(1)
    raise AssertionError(f"等待超时：{check}")

def bencode(value):
    if isinstance(value, int):
        return f"i{value}e".encode()
    if isinstance(value, bytes):
        return str(len(value)).encode() + b":" + value
    return b"d" + b"".join(bencode(key) + bencode(value[key]) for key in sorted(value)) + b"e"

class Client:
    def __init__(self, port):
        self.origin = f"http://127.0.0.1:{port}"
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def request(self, path, fields=None, files=None):
        data = None
        headers = {"Referer": self.origin + "/", "Origin": self.origin}
        if files:
            boundary = "DSMIntegrationCheck421"
            fields = {**(fields or {}), **files}
            body = []
            for key, value in fields.items():
                head = f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"'
                if isinstance(value, bytes):
                    head += '; filename="test.torrent"\r\nContent-Type: application/x-bittorrent'
                body.extend([head.encode(), b"\r\n\r\n", value if isinstance(value, bytes) else value.encode(), b"\r\n"])
            data = b"".join(body) + f"--{boundary}--\r\n".encode()
            headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
        elif fields is not None:
            data = urllib.parse.urlencode(fields).encode()
        request = urllib.request.Request(self.origin + path, data=data, headers=headers)
        with self.opener.open(request, timeout=5) as response:
            return response.read()

    def login(self, password):
        assert b"Ok." == self.request("/api/v2/auth/login", {"username": "admin", "password": password})

    def torrents(self):
        return {item["hash"]: item for item in json.loads(self.request("/api/v2/torrents/info"))}

    def preferences(self, **changes):
        return self.request("/api/v2/app/setPreferences", {"json": json.dumps(changes)})

with tempfile.TemporaryDirectory(prefix="qb-dsm-test-") as temporary:
    root = pathlib.Path(temporary)
    root.chmod(0o755)
    def inside(path):
        return root / path.lstrip("/")
    required = {"INFO", "package.tgz", "scripts", "conf", "WIZARD_UIFILES",
                "PACKAGE_ICON.PNG", "PACKAGE_ICON_256.PNG"}
    with tarfile.open(spk) as archive:
        assert {pathlib.PurePosixPath(name).parts[0] for name in archive.getnames()} == required
        archive.extractall(root / "spk", filter="data")
    scripts = "/spk/scripts/"
    def unpack():
        inside(target).mkdir(parents=True)
        with tarfile.open(root / "spk/package.tgz") as archive:
            archive.extractall(inside(target), filter="data")
        assert os.access(inside(target + "/bin/qbittorrent-nox"), os.X_OK)
        assert os.access(inside(target + "/bin/qbt-service"), os.X_OK)

    shutil.copytree(sysroot / "lib", root / "lib", symlinks=True, ignore_dangling_symlinks=True)
    (root / "lib64").symlink_to("lib")
    for name in ("bin", "dev", "proc", "etc", "tmp", "volume1", "volume2", "usr/syno/sbin"):
        (root / name).mkdir(parents=True, exist_ok=True)
    (root / "tmp").chmod(0o1777)
    shutil.copyfile(shutil.which("busybox"), root / "bin/busybox")
    (root / "bin/busybox").chmod(0o755)
    for command in ("sh", "awk", "cat", "chown", "chmod", "dirname", "head", "id", "install", "mkdir",
                    "mktemp", "mv", "od", "readlink", "rm", "sed", "sleep", "stat", "tr"):
        (root / "bin" / command).symlink_to("busybox")
    (root / "etc/passwd").write_text("root:x:0:0:root:/root:/bin/sh\n")
    (root / "etc/group").write_text("root:x:0:\nusers:x:100:\n")
    (root / "etc/nsswitch.conf").write_text("passwd: files\ngroup: files\nhosts: files\n")
    (root / "etc/hosts").write_text("127.0.0.1 localhost\n")
    (root / "usr/syno/sbin/synouser").write_text(
        "#!/bin/sh\n[ \"$1\" = --add ] || exit 1\n"
        "printf '%s:x:19081:100:qBittorrent:/nonexistent:/bin/false\\n' \"$2\" >> /etc/passwd\n")
    (root / "usr/syno/sbin/synouser").chmod(0o755)

    mounted = []
    def in_root(*args):
        run("chroot", root, *args)
    def lifecycle(name, *args):
        in_root(scripts + name, *args)
    seeder = None
    try:
        for device in ("null", "urandom", "random"):
            source = "/dev/" + device
            inside(source).touch()
            run("mount", "--bind", source, inside(source))
            mounted.append(inside(source))
        run("mount", "-t", "proc", "proc", root / "proc")
        mounted.append(root / "proc")
        unpack()
        in_root(target + "/bin/qbittorrent-nox", "--version")
        probe = target + "/bin/qt-runtime-check"
        shutil.copyfile(qt_probe, inside(probe))
        inside(probe).chmod(0o755)
        in_root(probe)
        inside(probe).unlink()
        lifecycle("preinst")
        lifecycle("postinst")
        password_file = next(inside(store).glob("*.txt"))
        password = password_file.read_text().splitlines()[1].split("：", 1)[1]
        assert password_file.stat().st_mode & 0o777 == 0o600
        lifecycle("start-stop-status", "start")
        lifecycle("start-stop-status", "status")
        client = Client(8080)
        wait_for(lambda: client.request("/"))
        try:
            client.request("/api/v2/app/version")
        except urllib.error.HTTPError as error:
            assert error.code in (401, 403)
        else:
            raise AssertionError("认证保护未生效")
        client.login(password)
        assert client.request("/api/v2/app/version") == b"v5.2.4"

        paths = ("/volume1/分享 空格 #", "/volume2/未完成 +", "/volume2/单独保存 [1]", "/volume1/做种目录")
        for path in paths:
            inside(path).mkdir()
            os.chown(inside(path), 19081, 100)
        client.preferences(save_path=paths[0], temp_path=paths[1], temp_path_enabled=True,
                           dht=False, pex=False, lsd=False, upnp=False)
        prefs = json.loads(client.request("/api/v2/app/preferences"))
        assert prefs["save_path"].rstrip("/") == paths[0]
        assert prefs["temp_path"].rstrip("/") == paths[1] and prefs["temp_path_enabled"]

        second = inside("/volume1/seeder/qBittorrent/config")
        second.mkdir(parents=True)
        second.joinpath("qBittorrent.conf").write_text(
            inside(config).read_text().replace("Port=8080", "Port=18080").replace("Port=6881", "Port=16881"))
        for item in [inside("/volume1/seeder"), second.parent, second, *second.iterdir()]:
            os.chown(item, 19081, 100)
        seeder = subprocess.Popen(["chroot", str(root), target + "/bin/qbt-service", "run",
                                   "qbittorrentspk", "/volume1/seeder", "/volume1/seeder/log",
                                   target + "/bin/qbittorrent-nox"], start_new_session=False)
        seed = Client(18080)
        wait_for(lambda: seed.request("/"))
        seed.login(password)
        seed.preferences(dht=False, pex=False, lsd=False, upnp=False, temp_path_enabled=False,
                         save_path=paths[3])

        def create_torrent(name, data):
            filename = name.encode()
            size = 16384
            info = {b"name": filename, b"length": len(data), b"piece length": size,
                    b"pieces": b"".join(hashlib.sha1(data[i:i+size]).digest() for i in range(0, len(data), size))}
            torrent_hash = hashlib.sha1(bencode(info)).hexdigest()
            file = inside(paths[3]) / name
            file.write_bytes(data)
            os.chown(file, 19081, 100)
            torrent = bencode({b"info": info})
            assert seed.request("/api/v2/torrents/add", {"savepath": paths[3], "autoTMM": "false"},
                                {"torrents": torrent}) == b"Ok."
            wait_for(lambda: seed.torrents().get(torrent_hash, {}).get("progress") == 1)
            seed.request("/api/v2/torrents/recheck", {"hashes": torrent_hash})
            return torrent_hash, torrent

        content = b"qBittorrent integration data\n" * 6000
        torrent_hash, torrent = create_torrent("校验 文件.bin", content)
        client.request("/api/v2/torrents/add", {"savepath": paths[2], "stopped": "true", "autoTMM": "false"},
                       {"torrents": torrent})
        wait_for(lambda: client.torrents().get(torrent_hash, {}).get("state") == "stoppedDL")
        client.request("/api/v2/torrents/start", {"hashes": torrent_hash})
        client.request("/api/v2/torrents/addPeers", {"hashes": torrent_hash, "peers": "127.0.0.1:16881"})
        wait_for(lambda: client.torrents().get(torrent_hash, {}).get("progress") == 1)
        assert (inside(paths[2]) / "校验 文件.bin").read_bytes() == content

        magnet_hash, _ = create_torrent("磁力 文件.bin", content)
        client.request("/api/v2/torrents/add", {"urls": f"magnet:?xt=urn:btih:{magnet_hash}",
                       "autoTMM": "false"})
        wait_for(lambda: magnet_hash in client.torrents())
        client.request("/api/v2/torrents/addPeers", {"hashes": magnet_hash, "peers": "127.0.0.1:16881"})
        wait_for(lambda: client.torrents().get(magnet_hash, {}).get("progress") == 1)
        assert (inside(paths[0]) / "磁力 文件.bin").read_bytes() == content

        lifecycle("preupgrade")
        original = inside(config).read_bytes()
        assert list(inside(profile + "/data").rglob("*.fastresume"))
        shutil.rmtree(inside(target))
        unpack()
        lifecycle("postupgrade")
        assert inside(config).read_bytes() == original
        lifecycle("start-stop-status", "start")
        client.login(password)
        assert {torrent_hash, magnet_hash} <= client.torrents().keys()
        lifecycle("preuninst")
        lifecycle("postuninst")
        original = inside(config).read_bytes()
        shutil.rmtree(inside(target))
        lifecycle("preinst")
        unpack()
        lifecycle("postinst")
        assert inside(config).read_bytes() == original
        assert (inside(paths[2]) / "校验 文件.bin").read_bytes() == content
        lifecycle("start-stop-status", "start")
        client.login(password)
        assert {torrent_hash, magnet_hash} <= client.torrents().keys()
        lifecycle("start-stop-status", "restart")
        client.login(password)
        assert {torrent_hash, magnet_hash} <= client.torrents().keys()
        print("通过 DSM GLIBC 2.20、网页认证、本地种子和磁力传输、自选路径及模拟生命周期测试。")
    finally:
        for path in (store + "/Logs/console.log", "/volume1/seeder/log"):
            if inside(path).is_file():
                print(inside(path).read_text(errors="replace"))
        if inside(store + "/service.pid").is_file() and mounted:
            lifecycle("start-stop-status", "stop")
        if seeder and seeder.poll() is None:
            seeder.terminate()
            seeder.wait(timeout=90)
        for path in reversed(mounted):
            run("umount", path)
