
TAG=0.1

docker buildx build --platform linux/arm64 -t wilke/anl-seq-service:arm64 -f Docker/Base.dockerfile .
docker buildx build --platform linux/amd64 -t wilke/anl-seq-service:amd64 -f Docker/Base.dockerfile .
docker push wilke/anl-seq-service:arm64
docker push wilke/anl-seq-service:amd64
docker manifest create --amend wilke/anl-seq-service:${TAG} wilke/wilke/anl-seq-service:amd64 wilke/wilke/anl-seq-service:arm64 
docker manifest create --amend wilke/anl-seq-service:latest wilke/wilke/anl-seq-service:amd64 wilke/wilke/anl-seq-service:arm64 

docker manifest push wilke/anl-seq-service:${TAG}
docker manifest push wilke/anl-seq-service:latest  


