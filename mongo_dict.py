# Ramkumar Paranjothy

import collections.abc
import pymongo
import datetime


class Repository(object):
    """
        Repository implementation for Mongo APIs
    """

    def __init__(self, schema, collection, hosturl="localhost"):
        # create connection to Mongo for that schema
        client = pymongo.MongoClient(hosturl)
        db = client[schema]
        self.collection = db[collection]

    def find(self, x=None):
        if isinstance(x, dict):
            return list(self.collection.find(x))
        elif isinstance(x, str):
            return self.collection.find_one({'_id': x})
        else:
            return self.collection.find()

    def delete(self, x):
        if isinstance(x, str):
            result = self.collection.delete_one({'_id': x})
        elif isinstance(x, dict):
            result = self.collection.delete_many(x)
        return result

    def update(self, k, v):
        if isinstance(k, dict):
            self.collection.update_many(
                k, {'$set': v}, upsert=True)
        elif isinstance(k, str):
            self.collection.update_one(
                {'_id': k}, {'$set': v}, upsert=True)
        return v

    def insert(self, k, v):
        self.collection.insert_one(
            {**v, '_id': k})
        return v

    def stats(self):
        return self.collection.count_documents({})

    def paginate(self, p, ct, srtKey="_id", descFlg="1"):
        # return self.collection.find(skip=p * ct, limit=ct, sort=[(srtKey,
        # int(descFlg) * -1 if descFlg == "1" else 1)])
        return self.collection.find().sort(srtKey, int(descFlg) * -1 if descFlg == "1" else 1).skip((p - 1) * ct).limit(p + 1 * ct)

    def aggregate(self, key, fn):
        pipe = [{"$group": {'_id': f'${key}', "value": {f'${fn}': 1}}}]
        return self.collection.aggregate(pipe)

    def aggregateTS(self, key, fn):
        # pipe = [{"$group": {'_id': f'${key}', "value": {f'${fn}': 1}}}]
        # pipe = [
        #    { "$group": {
        #             '_id': {
        #                 'month': {"$month": f'${key}'},
        #                 'day': {"$dayOfMonth": f'${key}'},
        #                 'year': {"$year": f'${key}'}
        #             },
        #             "value": {f'${fn}': 1}}
        #     }

        # ]

        pipe = [
            {
                '$group': {
                    "_id": {"$dateToString": {"timezone": "America/Chicago" , "format": "%Y-%m-%d", 'date': f'${key}'}},
                    "value": {f'${fn}': 1}
                }
            },
        ]
        return self.collection.aggregate(pipe)

    def push(self, k, v, listObj):
        # append v to the listObje array found under the _id of k
        _id = k
        nodes = v
        pushConfig = {"$push": {listObj: {"$each": nodes}}}
        return self.collection.update({"_id": _id}, pushConfig)


class MongoDict(collections.abc.MutableMapping):
    def __init__(self, schema, collection, hosturl=None):
        self.repository = Repository(schema, collection, hosturl)
        self.schema = schema
        self.collection = collection

    @ property
    def data(self):
        return self.repository.find()

    def __len__(self):
        return len(self.data)

    def __iter__(self):
        return map(lambda x: x["_id"], self.data)

    def __getitem__(self, key):
        return self.repository.find(key)

    def __delitem__(self, key):
        return self.repository.delete(key)

    def __setitem__(self, key, value):
        if self.__getitem__(key):
            self.repository.update(key, value)
        else:
            self.repository.insert(key, value)

    def __repr__(self):
        return f'{self.schema}:{self.collection} - {len(list(self.repository.find()))} documents'

    def iterData(self):
        for x in self.repository.find():
            yield x

    def stats(self):
        return self.repository.stats()

    def paginate(self, page, count, srtKey="_id", descFlg="1"):
        for x in self.repository.paginate(page, count, srtKey, descFlg):
            yield x

    def aggregate(self, k, f):
        for x in self.repository.aggregate(k, f):
            yield x

    def aggregateTS(self, k, f):
        for x in self.repository.aggregateTS(k, f):
            yield x

    def push(self, k, v, listObj):
        #  $push of Mongo: push the value to the list ided by _id
        #  see if it is there?
        alreadyIndexed = self.repository.find(k)

        if not alreadyIndexed:
            # print("Fresh Meat!")
            return self.repository.insert(k, {listObj: v})
        else:
            alreadyIndexedForNode = self.repository.find({'_id': k, 'nodes': {"$elemMatch": v[0]}})
            if not alreadyIndexedForNode:
                return self.repository.push(k, v, listObj)
            else:
                # print(" ***  Already Indexed for incoming value", alreadyIndexedForNode)
                return {"msg": "Already Indexed for incoming value"}
