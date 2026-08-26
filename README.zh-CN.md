# Document Converter

[English](README.md) | [한국어](README.ko.md) | [简体中文](README.zh-CN.md)

将本地 PDF 转换为可编辑的 DOCX 或 Markdown 文件，并可选择使用韩语和英语 OCR。
文档不会离开您的电脑，文档文本也不会被记录。

## 安装前的许可证说明

本仓库代码采用 MIT 许可证。转换依赖链通过 `pdf2docx` 使用 PyMuPDF；除非您获得其商业许可证，否则 PyMuPDF 采用 AGPL 许可证。在重新分发组合应用程序之前，请查看 [PyMuPDF 许可证](https://github.com/pymupdf/PyMuPDF)。详情请参阅 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

## 使用 Docker 快速开始

推荐使用 Docker，因为其中包含 Tesseract、韩语/英语语言数据和 CJK 字体。

```sh
git clone <repository-url> document-convert
cd document-convert
./run.sh input.pdf output.md
```

输入目录将以只读方式挂载。容器中只有输出目录可写。

## CLI

```sh
dc INPUT.pdf [-o OUTPUT.docx|OUTPUT.md]
```

选项：

- `--lang kor+eng` 设置 OCR 语言（默认值为 `kor+eng`）。
- `--no-ocr` 对已有可靠文本的 PDF 跳过 OCR。
- `--overwrite` 替换已有输出文件（以及 Markdown 资源目录）。
- `--timeout 300` 以秒为单位设置每个阶段的时限。

转换会先使用带有 `--skip-text` 的 OCRmyPDF，以保留已有文本的页面。DOCX 输出随后通过 `pdf2docx` 生成，并作为 OOXML 进行检查，以确保作者、标题、公司和自定义文档属性已被清除。Markdown 输出使用本地 PyMuPDF 提取文本、表格和图像；图像会写入文档旁的 `<output>_assets/`，并通过相对路径链接。

## 不使用 Docker 运行

安装 Python 3.11+，以及含韩语和英语语言数据的 Tesseract，然后执行：

```sh
python -m venv .venv
. .venv/bin/activate
pip install -e '.[ocr]'
dc input.pdf -o output.docx
```

- macOS：`brew install tesseract tesseract-lang`
- Ubuntu/WSL：`sudo apt install tesseract-ocr tesseract-ocr-kor tesseract-ocr-eng ghostscript qpdf`
- Windows：安装包含 `kor` 和 `eng` 数据的 Tesseract 与 Ghostscript，然后将两个安装目录加入 `PATH`。使用 PowerShell 激活虚拟环境，并运行相同的 `pip`/CLI 命令。

对于其他语言，请安装相应的 Tesseract `traineddata` 文件，并通过 `--lang` 传入语言代码，例如 `--lang deu+eng`。

## 限制与故障排除

PDF 是固定布局格式。复杂分栏、非常规字体、表格、图形和手写内容可能需要手动清理 DOCX。OCR 质量取决于扫描分辨率和源语言。对于干净的数字版 PDF，请使用 `--no-ocr`。

如果转换报告缺少语言，请安装相应的 Tesseract 语言数据。若超时，请使用更小的 PDF、增加 `--timeout`，或使用 Docker 确保本地依赖项可用。受密码保护或已损坏的 PDF 会被拒绝，且不会修改已有输出文件。

`requirements.lock` 包含针对 Python 3.12 Linux Docker 目标记录的、完全固定的传递依赖约束。它并非哈希锁定，也不跨平台：原生 wheel 会因操作系统和 Python 版本而异。若要获得最可复现的运行环境，请使用 Docker。
所请求的较新 `pdf2docx`、PyMuPDF 和 OCRmyPDF 版本在已配置的软件包索引中不可用，因此锁文件使用了该索引中可解析的最新版本；PyMuPDF 固定为经验证兼容的 `1.25.5` 版本。

CI Docker 冒烟测试会生成合成的数字、扫描和混合 PDF，并验证英语和韩语文本在每个 DOCX 中都保持可编辑。

## 贡献时的隐私保护

切勿提交真实源文档、OCR 导出文件、渲染页面或联系信息。仅使用合成夹具。发布变更前，请运行 `python scripts/privacy_scan.py`；详见 [CONTRIBUTING.md](CONTRIBUTING.md) 和 [SECURITY.md](SECURITY.md)。

如需进行私有的发布前检查，仅在运行时提供组织特定术语：`DOCUMENT_CONVERT_FORBIDDEN_TERMS='term-one,term-two' python scripts/privacy_scan.py`。这些值不会保存在本仓库中。

发布前，请创建仓库密钥 `DOCUMENT_CONVERT_FORBIDDEN_TERMS`，其中包含用逗号分隔的旧名称或帐户标识符。只有在 GitHub 提供密钥时，CI 才会注入它们。来自 fork 的拉取请求无法获得仓库密钥，但通用的电子邮件、二进制文件和工件检查仍会执行。
