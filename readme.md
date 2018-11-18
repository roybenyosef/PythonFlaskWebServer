Run DB locally

`docker run --name mqubel-postgres --rm -p 5432:5432 -e POSTGRES_PASSWORD=123Cyber postgres`

On AWS machine:

`cd ~/workspace/mqubel`

`sudo docker build -t mqubel .`

`sudo /usr/local/bin/docker-compose -f docker-compose up`
