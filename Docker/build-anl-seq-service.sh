
TAG=0.1
#CACHE="--no-cache"
CACHE=""

# docker build ${CACHE} --platform linux/arm64 -t wilke/anl-seq-service:arm64 -f Docker/base.dockerfile .
# docker build ${CACHE} --platform linux/amd64 -t wilke/anl-seq-service:amd64 -f Docker/base.dockerfile .
# docker push wilke/anl-seq-service:arm64
# docker push wilke/anl-seq-service:amd64

# docker manifest create --amend wilke/anl-seq-service:${TAG} wilke/anl-seq-service:amd64 wilke/anl-seq-service:arm64 
# docker manifest create --amend wilke/anl-seq-service:latest wilke/anl-seq-service:amd64 wilke/anl-seq-service:arm64 

# docker manifest push wilke/anl-seq-service:${TAG}
# docker manifest push wilke/anl-seq-service:latest  


docker buildx build ${CACHE} --platform linux/amd64,linux/arm64 -t wilke/anl-seq-service:latest --push -f Docker/base.dockerfile .
docker buildx build ${CACHE} --platform linux/amd64,linux/arm64 -t wilke/anl-seq-service:0.1 --push -f Docker/base.dockerfile .