IMAGE_NAME ?= ollama-qwen3-proto
PORT ?= 8000

.PHONY: up run stop

up:
	docker build -t $(IMAGE_NAME) .

run:
	docker run --rm -p $(PORT):8000 $(IMAGE_NAME)

stop:
	@docker ps -q --filter "ancestor=$(IMAGE_NAME)" | xargs -r docker stop
