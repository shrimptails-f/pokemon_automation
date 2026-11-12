#!/bin/sh
set -eu
here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
# The same properties must be used for compile and upload.
set -- --fqbn arduino:avr:micro \
  --build-property build.vid=0x0F0D \
  --build-property build.pid=0x0092 \
  --build-property 'build.usb_product="POKKEN CONTROLLER"' \
  --build-property 'build.usb_manufacturer="HORI CO.,LTD."' \
  --build-property 'build.extra_flags={build.usb_flags}'
arduino-cli compile "$@" "$here/controller"
