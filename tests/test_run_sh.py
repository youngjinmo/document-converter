import os
import subprocess
from pathlib import Path


def _fake_docker(directory: Path) -> Path:
    docker = directory / 'docker'
    docker.write_text(
        '''#!/bin/sh
set -eu
if [ "$1" = build ]; then
  exit 0
fi
stage=
output=
for argument in "$@"; do
  case "$argument" in
    type=bind,src=*,dst=/output) stage=${argument#type=bind,src=}; stage=${stage%,dst=/output} ;;
    /output/*) output=${argument#/output/} ;;
  esac
done
mkdir -p "$stage/${output%.*}_assets"
printf '%s\\n' '# generated' > "$stage/$output"
printf '%s\\n' 'asset' > "$stage/${output%.*}_assets/page-001-image-001.png"
''',
        encoding='utf-8',
    )
    docker.chmod(0o755)
    return docker


def test_run_sh는_대소문자_확장자를_허용하고_markdown과_assets를_함께_게시한다(tmp_path):
    source = tmp_path / 'input.PDF'
    output = tmp_path / 'my report.Md'
    source.write_bytes(b'%PDF-test')
    fake_bin = tmp_path / 'bin'
    fake_bin.mkdir()
    _fake_docker(fake_bin)
    environment = os.environ.copy()
    environment['PATH'] = f'{fake_bin}:{environment["PATH"]}'

    result = subprocess.run(
        ['sh', 'run.sh', str(source), str(output)],
        cwd=Path(__file__).parents[1],
        env=environment,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert output.read_text(encoding='utf-8') == '# generated\n'
    assert (tmp_path / 'my report_assets/page-001-image-001.png').exists()


def test_run_sh는_대소문자_assets_충돌시_기존결과를_보존하고_실패한다(tmp_path):
    source = tmp_path / 'input.PDF'
    output = tmp_path / 'result.Md'
    assets = tmp_path / 'result_assets'
    source.write_bytes(b'%PDF-test')
    assets.mkdir()
    (assets / 'old.txt').write_text('old asset', encoding='utf-8')

    result = subprocess.run(
        ['sh', 'run.sh', str(source), str(output)],
        cwd=Path(__file__).parents[1],
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert not output.exists()
    assert (assets / 'old.txt').read_text(encoding='utf-8') == 'old asset'
