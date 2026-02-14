.PHONY: run format test docker_build docker_save manage_remote deploy

run:
	poetry run uvicorn main:app --host 0.0.0.0 --port 8070 --reload

format:
	poetry run ruff format .

test:
	poetry run pytest

docker_build:
	docker system prune -f
	docker build -t homarv3 .

docker_save:
	mkdir -p ./images
	rm -rf ./images/homarv3.tar
	docker save -o ./images/homarv3.tar homarv3

manage_remote:
	ssh 192.168.50.30 "mkdir -p /home/domin/images /home/domin/homarv3"
	ssh 192.168.50.30 "rm -rf ./images/homarv3.tar"
	scp ./images/homarv3.tar domin@192.168.50.30:/home/domin/images
	scp ./docker-compose.yml domin@192.168.50.30:/home/domin/homarv3/
	scp ./.env domin@192.168.50.30:/home/domin/homarv3/
	ssh 192.168.50.30 "cd /home/domin/homarv3; docker-compose stop"
	ssh 192.168.50.30 "cd /home/domin/homarv3; docker-compose down"
	ssh 192.168.50.30 "docker load -i /home/domin/images/homarv3.tar"
	ssh 192.168.50.30 "docker image prune -f"
	ssh 192.168.50.30 "docker system prune -f"
	ssh 192.168.50.30 "cd /home/domin/homarv3; docker-compose up -d"

deploy: docker_build docker_save manage_remote
