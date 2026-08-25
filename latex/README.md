# 项目文档（LaTeX）

本目录是 STM32F407 裸机工程的 LaTeX 手册，使用 **ctex + xelatex** 编译。

## 目录结构

```
latex/
├── main.tex                 # 主文件（\input 各章节）
├── chapters/
│   ├── 01-intro.tex         # 项目简介
│   ├── 02-directory.tex     # 目录结构及使用
│   ├── 03-modifications.tex # 本项目修改记录
│   ├── 04-restructure.tex   # 目录优化：User/Core 分离
│   ├── 05-build-unix.tex    # macOS/Linux 构建
│   ├── 06-build-windows.tex # Windows 构建
│   ├── 07-cmake.tex         # CMake 说明
│   ├── 08-c-language.tex    # C 语言要点
│   ├── 09-embedded.tex      # 嵌入式开发要点
│   ├── 10-vscode.tex        # VS Code 开发与烧录配置
│   └── 11-memory-ota.tex    # 存储器/内存管理与 OTA 升级
└── README.md                # 本文件
```

## 编译

需要 TeX Live / MacTeX（含 xelatex 与 ctex 宏包）。

```bash
cd latex
xelatex main.tex            # 编译两次以生成目录/交叉引用
xelatex main.tex
```

或使用 latexmk 自动处理：

```bash
cd latex
latexmk -xelatex main.tex
```

生成 `main.pdf`。清理中间文件：`latexmk -C`。

## 说明

- 文档语言为中文，依赖 `ctex` 宏包与系统中文字体（macOS/Windows/Linux 均会自动匹配）。
- 代码片段使用 `listings` 宏包，无需外部依赖。
