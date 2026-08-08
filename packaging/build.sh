#!/usr/bin/env bash
# OCI イメージをビルドし、docker save で tarball を出力する。
# 各 run ごとにユニークなビルドが要る想定なので、タグに連番＋短ハッシュを付ける。
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

OUT_DIR="packaging/out"
mkdir -p "$OUT_DIR"

# ユニークタグ: ビルド番号（out 内の連番） + git 短ハッシュ（無ければ nogit）
BUILD_NO=$(( $(ls "$OUT_DIR"/halctf-*.tar 2>/dev/null | wc -l | tr -d ' ') + 1 ))
GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo nogit)
TAG="halctf-agent:b${BUILD_NO}-${GIT_SHA}"
TARBALL="${OUT_DIR}/halctf-b${BUILD_NO}-${GIT_SHA}.tar"

# 主催クラスタ(gce-gpu-cluster)は linux/amd64。Mac(arm64)で普通にビルドすると
# arm64 イメージになり向こうで動かないので、必ず amd64 を明示する。
# provenance/sbom を切ると docker save の tarball が単一マニフェストで綺麗になる。
echo "==> building ${TAG} (linux/amd64)"
docker build --platform linux/amd64 --provenance=false --sbom=false \
  -f packaging/Dockerfile -t "${TAG}" .

echo "==> verify arch"
ARCH=$(docker image inspect "${TAG}" --format '{{.Os}}/{{.Architecture}}')
echo "    ${ARCH}"
[ "${ARCH}" = "linux/amd64" ] || { echo "!! amd64 でない: ${ARCH}" >&2; exit 1; }

echo "==> docker save -> ${TARBALL}"
docker save "${TAG}" -o "${TARBALL}"

SIZE_MB=$(( $(wc -c < "${TARBALL}") / 1024 / 1024 ))
echo "==> done: ${TARBALL} (${SIZE_MB} MB)"
if [ "${SIZE_MB}" -gt 2500 ]; then
  echo "!! 警告: 2.5GB (2500MB) 制約を超過しています (${SIZE_MB} MB)" >&2
  exit 1
fi
