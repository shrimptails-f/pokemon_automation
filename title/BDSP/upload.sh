#!/bin/sh
set -eu
if [ "$#" -ne 1 ]; then
  echo "Usage: $0 /dev/ttyACM0" >&2
  exit 1
fi
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
build_dir=$(mktemp -d)
trap 'rm -rf "$build_dir"' EXIT HUP INT TERM
arduino-cli compile --fqbn arduino:avr:micro \
  --build-property build.vid=0x0F0D \
  --build-property build.pid=0x0092 \
  --build-property 'build.usb_product="POKKEN CONTROLLER"' \
  --build-property 'build.usb_manufacturer="HORI CO.,LTD."' \
  --build-property 'build.extra_flags={build.usb_flags}' \
  --output-dir "$build_dir" "$here/controller"
arduino-cli upload --fqbn arduino:avr:micro --port "$1" --input-dir "$build_dir" "$here/controller"
