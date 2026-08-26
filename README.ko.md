# Document Converter

[English](README.md) | [한국어](README.ko.md) | [简体中文](README.zh-CN.md)

로컬 PDF를 편집 가능한 DOCX 또는 Markdown 파일로 변환합니다. 한국어와 영어 OCR을 선택적으로 사용할 수 있습니다.
문서는 컴퓨터 밖으로 전송되지 않으며, 문서의 텍스트도 기록하지 않습니다.

## 설치 전 라이선스 안내

이 저장소의 코드는 MIT 라이선스를 따릅니다. 변환 의존성 체인은 `pdf2docx`를 통해 PyMuPDF를 사용합니다. PyMuPDF는 상용 라이선스를 취득하지 않은 경우 AGPL 라이선스가 적용됩니다. 결합된 애플리케이션을 재배포하기 전에 [PyMuPDF 라이선스](https://github.com/pymupdf/PyMuPDF)를 검토하세요. 자세한 내용은 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)를 참조하세요.

## Docker로 빠르게 시작하기

Tesseract, 한국어/영어 언어 데이터, CJK 폰트가 포함되어 있으므로 Docker 사용을 권장합니다.

```sh
git clone <repository-url> document-convert
cd document-convert
./run.sh input.pdf output.md
```

입력 디렉터리는 읽기 전용으로 마운트됩니다. 컨테이너 안에서 쓸 수 있는 곳은 출력 디렉터리뿐입니다.

## CLI

```sh
dc INPUT.pdf [-o OUTPUT.docx|OUTPUT.md]
```

옵션:

- `--lang kor+eng`은 OCR 언어를 설정합니다(기본값: `kor+eng`).
- `--no-ocr`은 이미 신뢰할 수 있는 텍스트가 있는 PDF의 OCR을 건너뜁니다.
- `--overwrite`는 기존 출력 파일과 Markdown 에셋 디렉터리를 덮어씁니다.
- `--timeout 300`은 단계별 제한 시간을 초 단위로 설정합니다.

변환은 먼저 OCRmyPDF를 `--skip-text`와 함께 실행하여 텍스트 페이지를 보존합니다. DOCX 출력은 이어서 `pdf2docx`로 변환하고, 작성자·제목·회사·사용자 지정 문서 속성이 제거되었는지 OOXML로 검사합니다. Markdown 출력은 로컬 PyMuPDF의 텍스트, 표, 이미지 추출을 사용합니다. 이미지는 `<output>_assets/`에 문서와 나란히 저장되고 상대 경로로 연결됩니다.

## Docker 없이 실행하기

Python 3.11 이상과 한국어·영어 언어 데이터가 포함된 Tesseract를 설치한 뒤 실행하세요.

```sh
python -m venv .venv
. .venv/bin/activate
pip install -e '.[ocr]'
dc input.pdf -o output.docx
```

- macOS: `brew install tesseract tesseract-lang`
- Ubuntu/WSL: `sudo apt install tesseract-ocr tesseract-ocr-kor tesseract-ocr-eng ghostscript qpdf`
- Windows: `kor` 및 `eng` 데이터가 포함된 Tesseract와 Ghostscript를 설치한 후, 두 설치 디렉터리를 `PATH`에 추가하세요. PowerShell에서 가상 환경을 활성화하고 동일한 `pip`/CLI 명령을 실행하세요.

다른 언어는 해당 Tesseract `traineddata` 파일을 설치하고 `--lang`에 언어 코드를 전달하세요. 예: `--lang deu+eng`.

## 제한 사항 및 문제 해결

PDF는 고정 레이아웃 형식입니다. 복잡한 다단 구성, 특이한 글꼴, 표, 도형, 손글씨는 DOCX를 수동으로 정리해야 할 수 있습니다. OCR 품질은 스캔 해상도와 원본 언어에 따라 달라집니다. 깨끗한 디지털 PDF에는 `--no-ocr`을 사용하세요.

언어 누락 오류가 발생하면 해당 Tesseract 언어 데이터를 설치하세요. 제한 시간이 초과되면 더 작은 PDF를 사용하거나 `--timeout` 값을 늘리거나 Docker를 사용해 로컬 의존성이 갖춰졌는지 확인하세요. 암호로 보호되었거나 손상된 PDF는 기존 출력 파일을 수정하지 않고 거부됩니다.

`requirements.lock`에는 Python 3.12 Linux Docker 대상에 대해 수집한, 완전히 고정된 전이 의존성 제약이 들어 있습니다. 해시 잠금도 아니고 플랫폼 간 호환도 보장하지 않습니다. 운영체제와 Python 버전에 따라 네이티브 휠이 달라지므로, 가장 재현성 높은 실행 환경으로는 Docker를 사용하세요.
요청된 최신 `pdf2docx`, PyMuPDF, OCRmyPDF 버전은 구성된 패키지 인덱스에서 사용할 수 없어, 잠금 파일에는 해당 인덱스에서 해결 가능한 최신 릴리스를 사용했습니다. PyMuPDF는 실험적으로 호환되는 `1.25.5` 버전으로 고정되어 있습니다.

CI Docker 스모크 테스트는 합성 디지털·스캔·혼합 PDF를 생성하고, 영어와 한국어 텍스트가 각 DOCX에서 모두 편집 가능한지 확인합니다.

## 기여 시 개인정보 보호

실제 원본 문서, OCR 결과물, 렌더링된 페이지, 연락처 정보를 커밋하지 마세요. 합성 픽스처만 사용하세요. 변경 사항을 게시하기 전에 `python scripts/privacy_scan.py`를 실행하세요. 자세한 내용은 [CONTRIBUTING.md](CONTRIBUTING.md)와 [SECURITY.md](SECURITY.md)를 참조하세요.

비공개 사전 게시 검사에서는 조직별 용어를 실행 시에만 제공하세요. `DOCUMENT_CONVERT_FORBIDDEN_TERMS='term-one,term-two' python scripts/privacy_scan.py`와 같이 실행할 수 있습니다. 해당 값은 이 저장소에 저장되지 않습니다.

게시하기 전에 쉼표로 구분된 이전 이름 또는 계정 식별자가 담긴 저장소 시크릿 `DOCUMENT_CONVERT_FORBIDDEN_TERMS`를 생성하세요. GitHub에서 시크릿을 사용할 수 있는 경우에만 CI가 주입합니다. 포크에서 열린 풀 리퀘스트는 저장소 시크릿을 받을 수 없지만, 일반 이메일·바이너리·아티팩트 검사는 계속 수행됩니다.
