IMAGE_NAME ?= ollama-qwen3-proto
PORT ?= 8000

.PHONY: build run

build:
	docker build -t $(IMAGE_NAME) .

run:
	docker run --rm -p $(PORT):8000 $(IMAGE_NAME)
