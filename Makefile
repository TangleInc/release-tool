docker-login:
	docker login -u $(DOCKER_LOGIN) -p $(DOCKER_TOKEN)

docker-build:
	docker build -t statusmoney/release-tool:latest -f docker/Dockerfile .

docker-push:
	docker push statusmoney/release-tool:latest

docker-shell:
	# to run bash shell inside docker container
	docker run -it --rm \
		--volume $(shell pwd):/app \
		--entrypoint bash \
		statusmoney/release-tool
