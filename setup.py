from setuptools import setup, find_packages

setup(
    name="floating-eye",
    version="1.0.0",
    description="窗口活动监控工具 - 浮空之眼",
    author="Floating Eye Team",
    packages=find_packages(),
    install_requires=[
        "PySide6>=6.6.0",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "floating-eye=main:main",
        ],
    },
)
