login:
	docker login -u $(DOCKER_LOGIN) -p $(DOCKER_TOKEN)

build:
	docker build -t statusmoney/release-tool:latest -f docker/Dockerfile .

push:
	docker push statusmoney/release-tool:latest

shell:
	# to run bash shell inside release-tool docker container
	bash examples/release shell
