To build docker image & run locally (M1):
```
docker buildx build --platform=linux/arm64 -t tesla-solar:arm64 .
docker run -d -v $PWD:/data -e CREDENTIALS=/data/credentials.json tesla-solar:arm64
```

To build docker image & run remotely (x86):
```
docker buildx build --platform=linux/amd64 -t ghcr.io/forcey/tesla-solar:amd64 --push .
```

To copy credentials out from docker container:
```
docker cp <container>:/usr/src/app/credentials.json .
```
