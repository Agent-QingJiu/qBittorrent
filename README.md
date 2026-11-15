<p align="center"><img src="assets/qbittorrent.svg" width="88" alt="qBittorrent 官方图标"></p>

# 群晖 DSM 原生 qBittorrent

面向群晖 DS3615xs-j、DSM 6.2.3-25426 和 Bromolow（x86_64）的 qBittorrent-nox 套件。安装后使用官方 Web UI 管理磁力和 Torrent 下载、做种、分类、标签、Tracker、RSS、连接数和传输限速。

[最新正式版本及 SPK 下载](https://github.com/QiStore/qBittorrent/releases/latest) · [构建记录](https://github.com/QiStore/qBittorrent/actions/workflows/build.yml) · [套件构建源码](https://github.com/QiStore/qBittorrent) · [qBittorrent 官方项目](https://www.qbittorrent.org/)

当前源码套件版本为 **5.2.4-0003**，对应[上游 qBittorrent 5.2.4](https://github.com/qbittorrent/qBittorrent/tree/a1e4649cb8ae581925acc161dbab5cbc6584c542)。首次正式发布后的版本号与附件由上方下载入口显示。

## 支持平台与依赖

| 项目 | 版本或要求 |
| --- | --- |
| 目标设备 | DS3615xs-j，Intel Core i3-2120 |
| 系统和架构 | DSM 6.2.3-25426，Bromolow，x86_64 |
| 官方工具链 | Synology DSM 6.2 Bromolow SDK，GLIBC 2.20 |
| qBittorrent-nox | 5.2.4 |
| Qt | 6.8.3，Core、Network、SQL、XML，SQLite 插件；LinguistTools 用于构建官方翻译 |
| libtorrent-rasterbar | 2.0.11 |
| Boost | 1.84.0 |
| OpenSSL / zlib | 3.5.6 / 1.3.1 |
| C/C++ 编译器 | GCC 13.4.0，以官方 DSM SDK 为 sysroot 构建 |

官方 SDK 自带 GCC 4.9.3，Qt 6 和新版 qBittorrent 需要更新的 C++ 编译器。构建流程编译 GCC 13.4.0 和目标 C++ 运行库，仍使用群晖 SDK 的头文件、GLIBC 2.20 和系统 ABI。构建输入及 SHA256 见 [sources.lock](sources.lock)，图标来自同一个上游源码归档。Qt 含针对 GLIBC 2.20 的[插件退出兼容补丁](ci/patches/qt-glibc220-plugin-shutdown.patch)，用于正常关闭 TLS 和 SQLite 插件。许可证见 [COPYING](COPYING) 和 SPK 中的 `share/licenses/`。上游对应源码可由锁定文件中的官方地址获得。

## 下载、校验、安装

1. 从正式发布页面下载对应架构的 `.spk` 和 `SHA256SUMS`。保持文件名一致并放到同一目录。
2. Linux 或 macOS 执行 `shasum -a 256 -c SHA256SUMS`。Windows PowerShell 执行 `Get-FileHash .\qBittorrent-5.2.4-0003-DSM6.2.3-bromolow.spk -Algorithm SHA256`，与该版本的 `SHA256SUMS` 对照。
3. 登录 DSM，打开「套件中心 → 手动安装」，选择 SPK。安装卷选择 **volume1**。如果 DSM 拒绝未签名套件，在套件中心核对信任级别后允许手动安装。
4. 在套件中心启动服务。局域网浏览器访问 `http://NAS的局域网地址:8080/`。Web UI 使用官方简体中文翻译。允许局域网访问所用的管理端口，避免将管理端口直接映射到公网。

## 首次登录与密码

首次安装会生成账号 `admin` 的随机密码。用 DSM 管理员登录 SSH 后读取。

```sh
sudo cat /volume1/@appdata/qBittorrent-native/初始登录.txt
```

登录后在「工具 → 选项 → Web UI」中设置新的用户名或密码，保存后用新凭据重新登录。确认新密码生效后，可用 `sudo rm -- /volume1/@appdata/qBittorrent-native/初始登录.txt` 删除初始凭据文件。重装沿用已有密码。初始文件只记录首次安装时生成的密码。

## 使用与下载目录

1. 在 DSM「控制面板 → 共享文件夹 → 编辑 → 权限」中，给本地用户 `qbittorrentspk` 授权所选共享文件夹。下载及移动需要读写权限。单独做种目录可按实际操作授予读取或读写权限。目录和它的各级父目录需要允许该账号遍历。
2. 在 Web UI「工具 → 选项 → 下载」中填写默认保存路径。勾选未完成下载目录的选项后，可另外填写临时目录。使用 NAS 上的绝对路径，例如 `/volume2/影音 下载` 或 `/volume3/未完成 + BT`。
3. 使用左上角的添加链接或添加种子按钮打开添加任务的对话框。需要指定个别路径时，选择手动管理模式并填写相应的保存目录。
4. 要用已有文件继续做种，为任务填写正确的已有文件目录并选择暂停添加。核对名称及目录结构后使用「强制重新校验」，校验完成后恢复任务。删除任务时可自行选择是否同时删除下载文件。
5. 暂停、恢复、分类、标签、Tracker 和限速均可在 Web UI 中操作。DHT、PEX、LSD、加密协议、连接数和 RSS 选项在相应的设置页管理。

默认 Web UI 端口 **8080/TCP**，可在 Web UI 选项中修改。BT 默认使用 **6881/TCP 和 UDP**，可在「选项 → 连接」单独修改。两个端口用途不同。

## 路径、升级和恢复

| 用途 | 实际位置 |
| --- | --- |
| 套件程序及依赖 | `/volume1/@appstore/qBittorrent` |
| 持久化根目录 | `/volume1/@appdata/qBittorrent-native` |
| 主配置文件 | `/volume1/@appdata/qBittorrent-native/Profile/qBittorrent/config/qBittorrent.conf` |
| 任务、恢复信息及元数据 | `/volume1/@appdata/qBittorrent-native/Profile/qBittorrent/data/` |
| 进程日志 | `/volume1/@appdata/qBittorrent-native/Logs/console.log` |
| 下载文件 | Web UI 中选定的共享目录或当前配置的默认目录 |

套件中心可启动、停止、重启和查看日志。启用服务后由 DSM 管理开机启动。更新前可先在套件中心停止服务，再备份持久化根目录。覆盖安装新 SPK 后启动，核对任务和目录设置。卸载默认删除配置、任务记录、日志、初始凭据和专用账号。勾选「保留配置、任务记录和专用账号」后，重新安装到 volume1 可以继续使用原配置和任务。共享文件夹及其中的下载文件会保留。若使用套件内置默认下载目录，卸载时会将其移到 `/volume1/@appdata/qBittorrent-downloads.*` 下。若将下载路径自行设在套件数据目录内的其他位置，请先迁移文件或勾选保留。

如需将数据备份恢复到同一台 NAS，先停止套件，恢复持久化目录及原有所有权与权限，再启动。迁移到其他 NAS 时，服务账号的用户 ID 和共享目录 ACL 需要管理员核对，软件默认拒绝接管归属不匹配的持久化目录。

## 常见问题

- **网页打不开**。检查套件状态、进程日志及 DSM 防火墙，核对 8080 是否被其他服务占用。停服务后，可以由管理员修改主配置文件现有的 `WebUI\Port`，再启动。
- **网页可以打开，下载写入失败**。检查保存目录和未完成目录是否位于已挂载卷上，并给 `qbittorrentspk` 授予目标目录的权限。如果使用手动管理，检查任务自身的保存位置。
- **忘记密码**。停止套件并备份配置文件。管理员可删除当前 `WebUI\Password_PBKDF2` 配置行后启动，使用 qBittorrent 输出到进程日志的临时密码登录，再在网页设置新密码。有过自定义用户名时沿用该用户名。
- **升级显示仍在关闭**。等待校验或保存任务状态完成再重试。强制结束进程会跳过 qBittorrent 的状态保存流程。
- **其他 DSM 模型或平台**。本项目只针对表中列出的目标系统。套件中心安装、系统启动和图标效果须在实际 DSM 上验收。

## 构建及发布

主分支的程序、套件或构建文件有改动时，GitHub Actions 会下载并核验官方源码与工具链，从源码编译，检查 ELF 依赖和 GLIBC 版本，并打包。在官方 SDK 的 GLIBC 根目录中用最终 SPK 执行程序和 Web UI 测试，脚本模拟 DSM 套件中心的生命周期调用。Actions 保留完整日志和待验收的测试包。

验收者在目标 DSM 上安装该 Actions 产物后，可在同一工作流填写通过实机验收的构建编号和 SPK SHA256。工作流取回原构建产物、核对摘要和源码提交，创建对应 Tag 与简体中文 Release，并上传 SPK 和校验文件。已存在的正式版本保留原文件。正式版以 Releases 为下载渠道。

### 安装时授权共享文件夹

安装向导默认勾选列出的普通本地共享文件夹，可取消任意一项，也可以取消应用整页设置。勾选表示允许专用账号读、写和删除相应目录中的文件。填写新共享文件夹的名称可在 volume1 创建并授权。新建后仍可在 Web UI 中自由选择下载目录。升级及勾选保留后的重装沿用原账号及权限，可在 DSM 控制面板撤销。
