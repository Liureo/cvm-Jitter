# cvm Jitter

`cvm Jitter` 是一个面向 **Apex Legends** 的 2PC 硬件 Jitter 后座力抵消项目。程序在控制电脑上运行，通过 MAKCU 或 Ferrum 硬件向游戏电脑发送鼠标移动指令，并同时提供本地桌面 UI 与局域网 WebUI。

## 功能

- 2PC 双电脑硬件控制架构
- 支持 MAKCU
- 支持 Ferrum Serial
- 支持 Ferrum Net（UDP）
- 支持本地 UI，可直接在控制电脑上完成连接、调参与控制
- 支持 WebUI，可由同一局域网内的手机或其他电脑访问
- 多种 Jitter 轨迹：左上、右上、水平、左下、右下、画圈
- 可调移动幅度和每步延迟
- 可选垂直下压，并可独立设置幅度与间隔
- 支持按住触发、切换触发和始终运行
- 支持鼠标左键、右键、中键及两个侧键触发
- 自动保存配置
- 提供硬件测试移动
- 提供局域网 WebUI
- 支持简体中文、繁体中文和英文
- 支持自定义桌面 UI 与 WebUI 配色

## 2PC 工作方式

```text
游戏电脑 ── 游戏与鼠标输入
   │
   └── MAKCU 或 Ferrum 硬件 ◀── 控制电脑运行 cvm Jitter
```

控制电脑负责运行 `cvm Jitter` 和生成 Jitter 移动序列。硬件设备接收串口或网络命令，再将鼠标移动输出到游戏电脑。本项目仅设计用于双电脑环境。

## 系统要求

- Windows 10 或 Windows 11
- Python 3.10 或更高版本
- Python Launcher（`py` 命令）
- MAKCU 或 Ferrum 兼容硬件
- 可用 USB 串口；Ferrum Net 模式需要控制电脑与设备网络互通

主要 Python 依赖：

- PySide6
- pyserial
- Flask

## 安装

1. 下载或解压项目。
2. 双击 `setup.bat`。
3. 脚本会创建 `.venv` 虚拟环境并安装依赖。
4. 安装完成后双击 `start.bat` 启动。

也可以在 PowerShell 中手动执行：

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

## 硬件连接

### MAKCU

1. 将 MAKCU 连接到控制电脑和游戏电脑。
2. 打开 `cvm Jitter`，选择 `MAKCU`。
3. 选择设备对应的 COM 端口和当前波特率。
4. 点击“连接硬件”。
5. 连接成功后点击“测试移动”确认输出。

### Ferrum Serial

1. 选择 `Ferrum`。
2. 连接模式选择 `Serial`。
3. 选择 COM 端口与正确波特率。
4. 点击“连接硬件”并执行测试移动。

### Ferrum Net

1. 选择 `Ferrum`。
2. 连接模式选择 `Net`。
3. 填写设备 IP、UDP 端口和设备显示的 8 位十六进制 UUID。
4. 确认控制电脑可以访问设备所在网络。
5. 点击“连接硬件”。

## 使用方法

1. 在“硬件”页面连接设备并执行“测试移动”。
2. 在“设置”页面选择 Jitter 轨迹。
3. 设置移动幅度和每步延迟。
4. 选择触发模式与触发按键。
5. 如有需要，在“高级”页面启用垂直下压。
6. 点击“启用抖动”进入等待触发状态。
7. 按所选触发方式运行；结束时点击“停止”。

建议先使用较小幅度和较长延迟测试，再逐步调整。不同灵敏度、DPI、武器和配件需要不同参数。

## 参数说明

| 参数 | 说明 |
| --- | --- |
| 硬件 | 选择 MAKCU 或 Ferrum |
| 连接模式 | Ferrum 可选择 Serial 或 Net |
| COM 端口 | 硬件在 Windows 中对应的串口 |
| 波特率 | 使用设备当前波特率；程序不会自动切换为 4M |
| Jitter 方式 | 鼠标循环移动的轨迹 |
| 幅度 | 每一步移动的像素量 |
| 每步延迟 | 相邻 Jitter 步骤之间的时间 |
| 垂直下压 | Jitter 运行时额外加入向下移动 |
| 下压幅度 | 每次向下移动的像素量 |
| 下压间隔 | 两次向下移动之间的时间 |
| 触发模式 | 按住、切换或不使用触发键 |
| 触发按键 | 从已连接硬件读取的鼠标按键 |

## 局域网 WebUI

在桌面程序中启用“局域网 WebUI”后，服务监听 `0.0.0.0:8765`。界面会显示可访问的网址，同一局域网内的手机或电脑可打开该地址。

- WebUI 可以查看连接与运行状态。
- 修改设置后需要点击“保存设置”才会发送到桌面程序。
- 状态轮询不会覆盖尚未保存的表单内容。
- 不建议将 `8765` 端口直接暴露到公网。

## 配置文件

所有设置保存在项目根目录的 `config.json`。桌面界面中的大部分设置会在修改后自动保存。

需要恢复默认设置时，先关闭程序，再备份并删除 `config.json`。下次启动时程序会根据默认值重新创建配置。

## 项目结构

```text
.
├── main.py                    # Qt 应用入口
├── config.json                # 用户配置
├── requirements.txt           # Python 依赖
├── setup.bat                  # 首次安装
├── start.bat                  # 启动程序
└── app
    ├── core                   # 配置、主题、轨迹与工作线程
    ├── hardware               # MAKCU 与 Ferrum 驱动
    ├── i18n                   # 桌面界面多语言
    ├── ui                     # Qt 界面、样式与图标
    │   └── icon
    │       └── cvm.jpg
    └── web                    # Flask WebUI
```

## 常见问题

### 找不到 COM 端口

- 检查 USB 连接与设备供电。
- 在 Windows 设备管理器中确认串口是否存在。
- 点击程序中的“刷新”。
- 确认没有其他程序占用串口。

### 连接失败

- 确认硬件类型、COM 端口和波特率匹配。
- MAKCU/Ferrum Serial 使用设备当前波特率，程序不会自动切换波特率。
- Ferrum Net 需要正确的 IP、UDP 端口和 8 位十六进制 UUID。

### 测试移动正常，但效果不合适

- 调整 Jitter 幅度与每步延迟。
- 更换移动轨迹。
- 根据游戏灵敏度、鼠标 DPI、武器与配件分别调参。

### WebUI 无法访问

- 确认桌面程序已启用 WebUI。
- 确认访问设备与控制电脑处于同一局域网。
- 检查 Windows 防火墙是否允许 Python 访问专用网络。
- 使用界面显示的局域网地址，不要在其他设备上使用 `127.0.0.1`。

## License / 許可證

Copyright (c) 2025 asenyeroao-ct. All rights reserved.  
版權所有 (c) 2025 asenyeroao-ct。保留所有權利。

This project is licensed under a custom license. See [LICENSE](LICENSE) for details.  
此專案依據自訂授權條款提供使用許可。詳情請參見 [LICENSE](LICENSE) 檔案。

### Key Points / 重點

- Personal, non-commercial use is permitted.  
  允許個人非商業性使用。
- Modification and redistribution are allowed with proper attribution.  
  在正確標明出處的條件下，允許進行修改和再分配。
- Commercial use is prohibited without written permission.  
  未經書面許可，禁止商業化使用。
- Original author `asenyeroao-ct` must be credited in all distributions.  
  所有散佈方式都必須標明原作者 `asenyeroao-ct`。

## Disclaimer / 免責聲明

This project is for learning and testing purposes only. This program is designed for dual-PC setups only. The author is not responsible for any game account bans, penalties, or other consequences resulting from the use of this program, and no compensation will be provided. Users must bear the risks of use and understand the possible consequences. Users are responsible for ensuring compliance with applicable laws and terms of service of any software or games used with this tool.

此專案僅用於學習和測試目的。該程式僅適用於雙電腦的組態環境。作者不對因使用此程式而導致的任何遊戲帳號被封禁、受到處罰或其他後果負責，亦不會提供任何賠償。使用者必須自行承擔使用此程式的風險，並瞭解可能產生的後果。使用者有責任確保其使用此工具時遵守所有相關法律及所使用軟體或遊戲的服務條款。

## Contributing / 貢獻

Contributions are welcome! Please feel free to submit a Pull Request.

歡迎大家貢獻力量！請隨時提交 Pull Request。

## Support / 支援

Discord: Join our Discord server for community support, discussions, and updates.  
Discord：加入我們的 Discord 伺服器，以獲得社群支援、參與討論並獲知最新消息。

https://discord.com/invite/pJ8JkSBnMB
