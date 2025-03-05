# Backend

## Starting qdrant Database

- Create a docker instance (OrbStack is an easy way to do this on Mac)
- Run `docker pull qdrant/qdrant` on command line
- Run `docker run -p 6333:6333 -p 6334:6334 -v "$(pwd)/qdrant_storage:/qdrant/storage:z" qdrant/qdrant` on the command line