# PyMOL 应用打包指南

将 PyMOL Open Source 打包为 **开箱即用** 的独立应用程序，无需用户手动安装 Python、Conda 或任何依赖。

## 产出物

| 平台 | 格式 | 文件 |
|------|------|------|
| **Windows** | 便携版 (ZIP) | `PyMOL-<version>-Windows-x86_64.zip` |
| **Windows** | 安装程序 (NSIS) | `PyMOL-<version>-Windows-x86_64-Setup.exe` |
| **macOS (Intel)** | 磁盘映像 (DMG) | `PyMOL-<version>-macOS-x86_64.dmg` |
| **macOS (Apple Silicon)** | 磁盘映像 (DMG) | `PyMOL-<version>-macOS-arm64.dmg` |

## 工作原理

```
PyMOL 源码  ──►  pip install  ──►  PyInstaller  ──►  独立包  ──►  安装程序
                                    │
                                    ├─ 内嵌 Python 解释器
                                    ├─ C 扩展 (_cmd, _champ)
                                    ├─ Qt GUI (PySide6)
                                    ├─ 所有数据文件 (shaders, icons, demo)
                                    └─ 系统库 (OpenGL, GLEW, freetype, libpng)
```

## 本地打包步骤

### 所有平台通用流程

```bash
# 1. 进入项目目录
cd pymol-open-source

# 2. 安装 PyMOL 及依赖
pip install .[dev]

# 3. 安装打包工具
pip install pyinstaller

# 4. 运行打包脚本
python packaging/build_package.py

# 5. 同时创建安装程序 (Windows NSIS / macOS DMG)
python packaging/build_package.py --installer
```

### Windows 详细步骤

**环境要求：**
- Windows 10+ (x86_64)
- Miniforge / Conda
- Visual Studio Build Tools (C++ compiler)
- NSIS 3.x (仅安装程序需要，可选)

```powershell
# 创建 conda 环境
conda create -n pymol_pkg -c conda-forge -c schrodinger --override-channels `
    python=3.12 pip freetype glew glm libpng libxml2-devel libnetcdf msgpack-c numpy pyside6

conda activate pymol_pkg

# 获取额外源码
git clone --depth 1 https://github.com/rcsb/mmtf-cpp.git
Copy-Item -Recurse -Path mmtf-cpp/include/* -Destination "$env:CONDA_PREFIX\Library\include"

# 编译 PyMOL
pip install -v .

# 打包
pip install pyinstaller
python packaging/build_package.py

# 创建安装程序 (需要安装 NSIS)
python packaging/build_package.py --installer
```

### macOS 详细步骤

**环境要求：**
- macOS 12.0+ (Intel 或 Apple Silicon)
- Xcode Command Line Tools
- Miniforge / Conda

```bash
# 创建 conda 环境
conda create -n pymol_pkg -c conda-forge -c schrodinger --override-channels \
    python=3.12 pip freetype glew glm libpng libxml2-devel libnetcdf msgpack-c numpy pyside6

conda activate pymol_pkg

# 获取额外源码
git clone --depth 1 https://github.com/rcsb/mmtf-cpp.git
cp -R mmtf-cpp/include/* ${CONDA_PREFIX}/include/

# 编译 PyMOL
export MACOSX_DEPLOYMENT_TARGET=12.0
pip install -v .

# 打包
pip install pyinstaller
python packaging/build_package.py

# 创建 DMG
python packaging/build_package.py --installer

# 代码签名 (可选，需要 Apple Developer ID)
# codesign --deep --force --verify --verbose --sign "Developer ID" \
#     --entitlements packaging/entitlements.plist \
#     dist/PyMOL.app
```

## CI/CD 自动构建

推送 tag 或手动触发 `.github/workflows/build-packages.yml` 即可自动构建：

```bash
git tag v3.2.0
git push origin v3.2.0
```

构建产物可在 GitHub Actions Artifacts 中下载 (保留 30 天)。

## 输出目录结构

### Windows 便携版

```
PyMOL/
├── PyMOL.exe              ← 双击启动
├── _internal/             ← 运行时文件
│   ├── pymol/             ← Python 模块 + C 扩展
│   │   └── pymol_path/    ← 数据文件
│   ├── PySide6/           ← Qt 库
│   ├── numpy/             ← NumPy
│   └── ...
└── ...
```

### macOS App Bundle

```
PyMOL.app/
└── Contents/
    ├── MacOS/
    │   └── PyMOL           ← 可执行文件
    ├── Resources/          ← 图标等
    └── Frameworks/         ← 内嵌框架
```

## 配置文件说明

| 文件 | 用途 |
|------|------|
| `pymol.spec` | PyInstaller 规格文件，定义入口、依赖、数据文件 |
| `pymol_launcher.py` | 启动脚本，设置 PYMOL_PATH 环境变量 |
| `build_package.py` | 跨平台构建脚本，编排 PyInstaller → 验证 → 打包 |
| `installer.nsi` | NSIS Windows 安装程序脚本 |
| `entitlements.plist` | macOS 代码签名权限配置 |

## 故障排除

**PyInstaller 找不到 pymol._cmd:**
```bash
pip install -e .   # 确保 PyMOL 以 editable 模式安装
```

**Qt 插件缺失 (启动时 "No Qt platform plugin"):**
```bash
pip install PySide6 --force-reinstall
```

**macOS "app is damaged" 错误:**
```bash
# 移除 quarantine 属性
xattr -cr dist/PyMOL.app

# 或进行代码签名
codesign --deep --force --verify --verbose --sign - dist/PyMOL.app
```

**文件过大 (>500MB):**
```bash
# 排除不常用的模块可以减少体积
# 编辑 pymol.spec 中的 excludes 列表:
#   'matplotlib', 'scipy', 'pandas', 'IPython' 等
```
