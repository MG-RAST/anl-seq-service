# scripts and env for the sequencing service

```bash
export TAG=`date +"%Y%m%d.%H%M"`
docker build --force-rm --no-cache --rm -t anl_seq:${TAG} .
skycore push anl_seq:${TAG}
```
