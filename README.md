# AC Overlay

神力科莎 (Assetto Corsa) 实时遥测数据显示插件，支持 RaceChrono 导入分析。

![Windows](https://img.shields.io/badge/platform-Windows-blue)
![Python](https://img.shields.io/badge/python-3.10+-green)
![License](https://img.shields.io/badge/license-MIT-yellow)

## 功能

- 🎮 **实时显示** - 油门/刹车曲线、G力表、转速、挡位、速度
- 📝 **数据录制** - 自动/手动录制遥测数据
- 📊 **RaceChrono 兼容** - CSV 格式可直接导入 RaceChrono 分析
- 🪟 **透明悬浮窗** - 无边框窗口，可拖拽定位

## 快速开始

### 直接使用

下载 [ACOverlay.exe](https://github.com/yourname/ACOverlay/releases) (~25MB)，双击运行。

### 从源码运行

```bash
pip install -r requirements.txt
python main.py
```

## 快捷键

| 按键 | 功能 |
|------|------|
| F9 | 显示/隐藏窗口 |
| F10 | 切换自动显隐 |
| F11 | 开始/停止录制 |
| F12 | 切换自动录制 |

## 数据录制

- **日志位置**: `logs/` 文件夹
- **文件格式**: `时间_赛道_车辆.csv`
- **采样率**: 25Hz

### RaceChrono 导入

生成的 CSV 可直接导入 RaceChrono Pro，包含以下数据：

| 数据项 | 说明 |
|--------|------|
| Time | 时间戳 |
| Speed | 速度 (km/h) |
| Throttle/Brake | 油门/刹车 |
| Steering angle | 方向盘角度 |
| Gear / RPM | 挡位 / 转速 |
| Lateral/Longitudinal acceleration | G力 |
| X/Y position | 位置坐标 |

## 打包

```bash
pip install pyinstaller
pyinstaller ACOverlay.spec --noconfirm
```

## 技术说明

通过读取 AC 共享内存接口获取数据：
- `acpmf_physics` - 物理数据
- `acpmf_graphics` - 图形数据  
- `acpmf_static` - 静态数据

## 许可证

MIT License

## 致谢

- Assetto Corsa 共享内存 API 文档
- PyQt6 社区
- RaceChrono 数据格式规范