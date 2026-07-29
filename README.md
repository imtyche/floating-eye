## 简介
浮空之眼（Floating Eye）是一个基于 PySide6 的桌面窗口活动监控与捕获工具，带有动态“眼睛”动画作为前端交互。它用于监控窗口切换、截屏/摄像头拍照并记录历史，适合需要本地桌面活动可视化与审计的个人或小型团队使用。

### 技术栈
- Language(s): Python (主要)，少量 Batchfile（打包脚本）
- Framework / runtime: PySide6（桌面 GUI）
- Notable libraries: PySide6（UI）、（项目中有 setup.py / requirements.txt 用于声明依赖），其余依赖请参见 requirements.txt

## 目录结构
```
floating-eye/
├── README.md                  # 项目说明（这里可以替换为更详细的说明）
├── requirements.txt           # 运行时依赖（用于 pip install -r requirements.txt）
├── setup.py                   # 打包 / 安装脚本（可通过 python setup.py install 或 pip install .）
├── package.bat                # Windows 打包/发布辅助脚本
├── config/                    # 配置与主题定义
│   ├── __init__.py
│   └── themes.py              # 主题色、样式变量与主题枚举（UI 主题配置入口）
├── core/                      # 核心后台逻辑与配置
│   ├── __init__.py
│   ├── database.py            # 活动记录数据库接口（持久化层）
│   └── settings.py            # 全局设置与常量（应用默认配置、路径等）
├── capture/                   # 捕获相关实现
│   ├── __init__.py
│   └── screenshot.py          # 屏幕截图与摄像头拍照实现（捕获逻辑入口）
├── ui/                        # 界面相关（基于 PySide6）
│   ├── __init__.py
│   ├── theme_style.py         # UI 风格 / 样式表生成与应用
│   ├── dialogs.py             # 各类对话框（设置、历史查看、关于等）
│   └── eye_widget.py          # 主界面/悬浮“眼睛”窗口（FloatingEye 类，应用入口 UI 组件）
├── monitoring/                # 监控线程 / 侦测逻辑
│   ├── __init__.py
│   └── monitor_thread.py      # 监控主循环 / 线程（检测窗口切换并触发捕获）
└── main.py                    # 程序入口（创建 QApplication 并显示 FloatingEye）
```

## 怎么安装:
- 运行时由 main.py 启动：创建 QApplication 实例并实例化 ui.eye_widget.FloatingEye（主 UI）。
- FloatingEye（ui/eye_widget.py）负责主界面、主题应用（依赖 config/themes.py 与 ui/theme_style.py）并与监控模块（monitoring/monitor_thread.py）和捕获模块（capture/screenshot.py）交互以执行截屏或拍照动作。
- monitoring/monitor_thread.py 在后台线程或计时器中检测窗口活动并在满足条件时调用 capture.screenshot.py 的接口进行捕获，同时将记录写入 core/database.py 管理的持久化存储。核心配置（采样间隔、主题、保存路径等）由 core/settings.py 管理。

## 主要文件说明（便于 README 中补充的更详细条目）
- main.py
    - 程序入口。已知符号：main()；导入 FloatingEye 并调用 app.exec()。
- ui/eye_widget.py
    - 主界面组件文件，包含 FloatingEye 类（主窗体/悬浮窗口）。负责显示“眼睛”动画，接收用户交互（设置、启动/停止监控等）。
- ui/dialogs.py
    - 定义设置窗口、历史记录查看对话框、确认/提示框等 UI 对话组件。
- ui/theme_style.py & config/themes.py
    - 主题与样式定义：三种主题（暗色/亮色/血色）与三种眼睛颜色（血红/天使蓝/恶魔紫），处理 QSS 或样式表构建与应用的逻辑点。
- monitoring/monitor_thread.py
    - 监控运行循环与线程：检测前台窗口变化、调度截屏、写入数据库或通知 UI。
- capture/screenshot.py
    - 屏幕截图与摄像头拍照实现。应包含截图保存、文件命名与多显示器或 DPI 处理的接口（建议在 README 中说明支持/限制）。
- core/settings.py
    - 默认配置项（例如采样/捕获间隔、保存目录、是否开机自启等），README 中应列出可配置项及默认值。
- core/database.py
    - 事件/历史记录持久化接口（可能使用 SQLite 或本地文件存储），README 中应说明数据库位置、表/字段（若有 schema）与导出/清理方法。
- setup.py / requirements.txt / package.bat
    - 安装与打包说明：如何安装依赖、如何打包为 Windows 可执行（package.bat），以及如何通过 setup.py 安装到系统。

## 如何运行
最短运行路径（基于仓库现有文件）：
1. 创建并激活 Python 虚拟环境（可选，但推荐）
2. 安装依赖
   ```
   python -m venv venv
   venv\Scripts\activate    # Windows
   # 或: source venv/bin/activate  # macOS / Linux
   pip install -r requirements.txt
   ```
3. 启动程序
   ```
   python main.py
   ```
4. 打包（Windows）参考仓库顶层的 package.bat（双击或在 cmd 中运行 package.bat）。

或者使用 setup.py 安装（可选）：
```
pip install .
# 然后仍可通过 python main.py 启动，或按 setup.py 中定义的入口（若有）启动
```

### 注意/环境提示：
- 需要安装 PySide6（确保 requirements.txt 中包含正确版本）
- 在 Windows 上运行可能需要额外权限以访问摄像头或保存截图目录