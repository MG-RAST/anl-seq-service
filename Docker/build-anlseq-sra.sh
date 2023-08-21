docker buildx build --platform linux/arm64 -t wilke/anl-seq-service:arm64 -f Docker/Base.dockerfile .
docker buildx build --platform linux/amd64 -t wilke/anl-seq-service:amd64 -f Docker/Base.dockerfile .
docker push wilke/anl-seq-service:arm64
docker push wilke/anl-seq-service:amd64
docker manifest create --amend wilke/anl-seq-service:0.1 wilke/wilke/anl-seq-service:amd64 wilke/wilke/anl-seq-service:arm64 
docker tag wilke/anl-seq-service:0.1 wilke/anl-seq-service:latest
docker manifest push wilke/anl-seq-service:0.1  
docker push -a wilke/anl-seq-service:latest    

docker buildx build --platform linux/arm64 -t wilke/anlseq-sra:arm64 -f Docker/anlseq-sra.dockerfile .
docker buildx build --platform linux/amd64 -t wilke/anlseq-sra:amd64 -f Docker/anlseq-sra.dockerfile .
docker push wilke/anlseq-sra:arm64
docker push wilke/anlseq-sra:amd64
docker manifest create --amend wilke/anlseq-sra:1.0 wilke/anlseq-sra:arm64 wilke/anlseq-sra:amd64
docker manifest push wilke/anlseq-sra:1.0