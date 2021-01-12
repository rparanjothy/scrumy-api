## Scrumy

Jeep API layer

### How to run

```
MONGO:
docker container run -d --rm -v /home/data:/data/db -p 27071:27071 --name scrumy-db mongo

Default Start
docker container run -d --restart unless-stopped --name scrumy-api -p30000:4777 --link scrumy-db:mongo

Custom Start
docker container run -d --restart unless-stopped --name scrumy-api \
-p30000:4777 \
-e MONGO_HOST=mongodb://mongo
-e MONGO_DB=testdb
-e MONGO_COLLECTION=test
--link scrumy-db:mongo IMAGE_NAME
```

### Usage:

0. http://localhost:30000/teams/listinfo?download=1
1. http://localhost:30000/teams/paginate?page=1
2. http://localhost:30000/teams/paginate?page=9&count=10
3. http://localhost:30000/stats
4. http://localhost:30000/health
5. http://localhost:30000/help
6. http://localhost:30000/teams/retrieve/afdb7f81-58ff-4743-b434-05073fe2ef07
7. http://localhost:30000/teams/aggregate?key=type&fn=sum
8. http://localhost:30000/teams/aggregate?key=data.iteration_name&fn=sum
9. http://localhost:30000/teams/paginate?page=9&count=100&sortKey=data.bios_name
10. http://localhost:30000/teams/paginate?page=9&count=100&sortKey=type
11. http://localhost:30000/teams/filter?key=data.test_name&val=TW20190416
12. http://localhost:30000/teams/paginate?page=9&count=100&sortKey=type
13. http://localhost:4777/teams/paginate?sortKey=data.upd_ts&descending=0

Ram
