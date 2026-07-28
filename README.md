# 浮空之眼 (Floating Eye)

一个使用 PySide6 开发的窗口活动监控工具，带有一个动态眼睛动画效果。

## 功能特性

- 🎯 实时监控窗口切换活动
- 📷 支持摄像头拍照和屏幕截图
- 🎨 三种主题：暗色、亮色、血色
- 👁 三种眼睛颜色：血红（默认）、天使蓝、恶魔紫
- ⚙️ 可配置的捕获间隔
- 📅 活动历史记录查看
- 🚀 支持开机自启动

## 安装
package.bat

## 目录结构
```
    floating-eye/
    ├── README.md
    ├── requirements.txt
    ├── setup.py
    ├── config/                     # 配置模块
    │   ├── __init__.py
    │   └── themes.py
    ├── core/                       # 核心模块
    │   ├── __init__.py
    │   ├── database.py
    │   └── settings.py
    ├── capture/                    # 捕获模块
    │   ├── __init__.py
    │   └── screenshot.py
    ├── ui/                         # UI模块
    │   ├── __init__.py
    │   ├── theme_style.py
    │   ├── dialogs.py
    │   └── eye_widget.py
    ├── monitoring/                 # 监控模块
    │   ├── __init__.py
    │   └── monitor_thread.py
    └── main.py                     # 主程序
```

