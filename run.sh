#!/usr/bin/env sh
set -eu

if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
  echo "Usage: ./run.sh INPUT.pdf [OUTPUT.docx]" >&2
  exit 2
fi

input=$1
case "$input" in
  *.pdf|*.PDF) ;;
  *) echo "Input must be a PDF file." >&2; exit 2 ;;
esac
if [ ! -f "$input" ]; then
  echo "Input PDF does not exist." >&2
  exit 2
fi

if [ "$#" -eq 2 ]; then output=$2; else output="${input%.*}.docx"; fi
case "$output" in
  *.docx|*.DOCX) ;;
  *) echo "Output must use the .docx extension." >&2; exit 2 ;;
esac
if [ -e "$output" ]; then
  echo "Output already exists; choose another path." >&2
  exit 2
fi

input_dir=$(cd "$(dirname "$input")" && pwd)
input_name=$(basename "$input")
output_dir=$(dirname "$output")
mkdir -p "$output_dir"
output_dir=$(cd "$output_dir" && pwd)
output_name=$(basename "$output")
stage_dir=$(mktemp -d "$output_dir/.document-convert.XXXXXX")
trap 'rm -rf "$stage_dir"' EXIT HUP INT TERM

docker build -t document-convert:local .
docker run --rm \
  --network none \
  --cap-drop ALL \
  --security-opt no-new-privileges:true \
  --read-only \
  --tmpfs /tmp:rw,noexec,nosuid,size=512m \
  --pids-limit 256 \
  --memory 2g \
  --cpus 2 \
  --user "$(id -u):$(id -g)" \
  --env HOME=/tmp \
  --env XDG_CACHE_HOME=/tmp \
  --mount "type=bind,src=$input_dir,dst=/input,readonly" \
  --mount "type=bind,src=$stage_dir,dst=/output" \
  document-convert:local \
  "/input/$input_name" -o "/output/$output_name"

if ! ln "$stage_dir/$output_name" "$output_dir/$output_name"; then
  echo "Output already exists; conversion result was not published." >&2
  exit 2
fi
