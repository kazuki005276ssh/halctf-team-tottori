.PHONY: install dev test lint fmt run demo build clean

install:
	python3 -m pip install -e .

dev:
	python3 -m pip install -e ".[dev]"

test:
	python3 -m pytest -q

lint:
	python3 -m ruff check .

fmt:
	python3 -m ruff format .

# モック標的 + モックモデルでローカル end-to-end（外部 API 不要）
demo:
	HALCTF_USE_MOCK=true python3 -m halctf.cli --demo

# 実 API に対して 1 チャレンジを走らせる（.env を読む）
run:
	python3 -m halctf.cli

# OCI イメージをビルドして docker save の tarball を出力
build:
	bash packaging/build.sh

clean:
	rm -rf packaging/out .pytest_cache .ruff_cache **/__pycache__
