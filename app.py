
#!/usr/bin/env python3
import io
import re
import os.path
from datetime import datetime
from flask import Flask
from flask import jsonify
from flask import request
from flask import Response
from flask_cors import CORS
from mongo_dict import MongoDict
import json

##
# debug logging flag
# can be dynamically changed from client side
##

api = Flask(__name__)

cors = CORS(api)

default_mongoURL = "mongodb://mongo"
default_mongoDB = "scrumy"
default_mongoCOLLECTION = "teams"


def _getConfigValue(config, defaultValue):
    '''
    fetch and return the value of an environment variable if it is set.
    return the supplied default value otherwise.
    '''
    configValue = os.environ.get(config)
    return defaultValue if not configValue else configValue


def getEnv():
    fuseFileConfigs = [_getConfigValue(config, defaultValue) for config, defaultValue in [
        ('MONGO_HOST', default_mongoURL), ('MONGO_DB', default_mongoDB), ('MONGO_COLLECTION', default_mongoCOLLECTION)]]
    if all(fuseFileConfigs):
        return fuseFileConfigs
    else:
        print("**" * 30)
        raise Exception(f"Error while Defaulting env vars... - {fuseFileConfigs}")


_hostUrl, _db, _collection = getEnv()

print(f'HOST        : {_hostUrl}')
print(f'DB          : {_db}')
print(f'COLLECTION  : {_collection}')

teams = MongoDict(_db, _collection, _hostUrl)


def filterDict(x={}, filterKeys=[]):
    """
        Similar to JS unpacking, remove removeKeys from the incoming dict.
        This is used to remove the 'teams' binary object prior to sending back to
        avoid Serialization error.
    """
    return {k: x[k] for k in x.keys() if k not in filterKeys}


##
# Health Route
##
@api.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', "host": _hostUrl})


@api.route('/stats', methods=['GET'])
def stats():
    return jsonify({'status': 'healthy', "host": _hostUrl, "db": _db, "collection": _collection, "docs": teams.stats()})

##
# Help Route
##


@api.route('/help', methods=['GET'])
def show_routes():
    xs = list(map(repr, api.url_map.iter_rules()))
    return jsonify({'routes': xs})


##
# update  file
#
# @api.route('/teams/update/<id>', methods=['POST'])
@api.route('/teams/upsert/<id>', methods=['POST'])
def update_object(id):
    # if we have an object against that key, update, else insert
    try:
        if teams[id]:
            # backup
            id_bkup = f"{id}_{datetime.now().strftime('%Y-%m-%d-%H:%M:%S')}"
            teams[id_bkup] = teams[id]
            teams[id] = request.json
            return jsonify({"status": "ok", 'updated': True})
        else:
            teams[id] = request.json
            return jsonify({'status': 'ok'})
    except Exception as update_exception:
        return error_response(update_exception)


@api.route('/teams/create/<name>', methods=['POST'])
def create_object(name):
    # UPLOAD
    try:
        if not teams[name]:
            teams[name] = request.json
            return jsonify({'status': 'ok',
                            'team_saved': {'name': teams[name]['_id']
                                           }})
        else:
            return error_response(data={"status": "error", "msg": "Duplicate Key", "_id": name}, err_code=500)
    except Exception as create_exception:
        return error_response(create_exception)


@api.route('/teams/createEvent/<name>', methods=['POST'])
def create_event(name):
    # UPLOAD
    # This one sets timestamps as dates so Mongo can understand them better.
    try:
        if not teams[name]:
            payload = request.json
            ld_ts = payload['ld_ts']
            msg_ts = payload['data']['msg_ts']
            print(ld_ts, msg_ts, type(ld_ts), type(msg_ts))
            teams[name] = {
                **payload,
                "ld_dt": datetime.fromtimestamp(ld_ts / 1000),
                "msg_dt": datetime.fromtimestamp(msg_ts / 1000)}
            return jsonify({'status': 'ok'})
        else:
            return error_response(data={"status": "error", "msg": "Duplicate Key", "_id": name}, err_code=500)
    except Exception as create_exception:
        return error_response(create_exception)


@api.route('/teams/push', methods=['POST'])
def push_object():
    # UPLOAD
    # TODO: "nodes" can be a param..
    try:
        payload = request.json
        k = payload['key']
        v = payload['nodes']
        listObj = "nodes"
        ret = teams.push(k, v, listObj)
        return jsonify(ret)

    except Exception as create_exception:
        return error_response(create_exception)


##
# retrieve  file
##
@api.route('/teams/retrieve/<id>', methods=['GET'])
def retrieve_ByID(id):
    if teams[id]:
        return teams[id]
    else:
        return error_response(err_code=404)


def gg(x):
    c = x.read(1024 * 5)
    while c:
        yield c
        c = x.read(1024 * 5)


@api.route('/teams/filter', methods=['GET'])
def filter():
    k = request.args.get("key", "_id")
    v = request.args.get("val", "123")
    d = request.args.get("download", "0")

    if teams[{k: v}]:
        if(d == "1"):
            inMem = io.BytesIO(json.dumps({"data": teams[{k: v}]}).encode('utf-8'))
            return Response(gg(inMem), mimetype="application/octet-stream", headers={
                'Content-Disposition': f'attachment; filename=filter-{k}-{v}.json'})
        else:
            return jsonify({"data": teams[{k: v}]})
    else:
        return error_response(err_code=404, data={"query": {k: v}})


##
# delete  file
##


@api.route('/teams/delete/<id>', methods=['DELETE'])
def remove_object(id):
    try:
        result = teams.pop(id)
        if isinstance(result, list):
            deletedCount = len(result)
        else:
            deletedCount = 1 if result else 0
        if result:
            return jsonify({'status': 'ok', 'removed': True, 'name': id, "deletedCount": deletedCount})
        else:
            return error_response(data={'msg': 'No Data Found', 'key': id}, err_code=404)
    except Exception as delete_exception:
        return error_response(
            delete_exception, data={"err_msg": f"delete(s) failed for key: {id}"})


@api.route('/teams/listinfo', methods=['GET'])
def list_fuse_file_info():
    try:
        d = request.args.get("download", "0")

        if (d == "1"):

            inMem = io.BytesIO(json.dumps({"data": list(teams.data)}, default=str).encode('utf-8'))
            return Response(gg(inMem), mimetype="application/octet-stream", headers={
                'Content-Disposition': f'attachment; filename=master.json'})
        else:
            return jsonify({"data": list(teams.data)})

    except Exception as list_exception:
        return error_response(list_exception)


@api.route('/teams/paginate', methods=['GET'])
def paginate():
    try:
        page = request.args.get('page', "1")
        count = request.args.get('count', "100")
        srtKey = request.args.get('sortKey', "_id")
        descFlg = request.args.get('descending', "1")
        d = request.args.get("download", "0")

        if (d == "1"):
            inMem = io.BytesIO(json.dumps(
                {"data": list(teams.paginate(int(page), int(count), srtKey))}).encode('utf-8'))
            return Response(gg(inMem), mimetype="application/octet-stream", headers={
                'Content-Disposition': f'attachment; filename=paginate-{page}-{count}.json'})
        else:
            return jsonify({"_meta": {"page": page, "count": count, "sortKey": srtKey, "descending": descFlg},
                            "data": list(teams.paginate(int(page), int(count), srtKey, descFlg))})
    except Exception as list_exception:
        return error_response(list_exception)


# @api.route('/teams/fix', methods=['GET'])
# def fix():
#     import random
#     try:
#         for x in teams.data:
#             if 'data' in x.keys():
#                 pid = x['_id']
#                 # print(pid)
#                 pl = x['data']
#                 if 'upd_ts' in pl.keys():
#                     p2 = {

#                         "ld_dt": datetime.fromtimestamp(
#                             pl['upd_ts'] / 1000),
#                         "msg_dt": datetime.fromtimestamp(
#                             (pl['upd_ts'] - random.randrange(0,11316208133)) / 1000)}
#                     # print(p2)
#                     teams[pid] = {**x, **p2}
#                 else:
#                     print(pid, "missing upd_ts")
#         return {"msg":"ShitzFixed"}
#     except Exception as list_exception:
#         return error_response(list_exception)


@api.route('/teams/aggregate', methods=['GET'])
def agg():
    try:
        page = request.args.get('key')
        count = request.args.get('fn')
        d = request.args.get("download", "0")
        if not page or not count:
            raise Exception("missing key and fn for aggregation.")
        if (d == "1"):
            inMem = io.BytesIO(json.dumps({"data": list(teams.aggregate(page, count))}).encode('utf-8'))
            return Response(gg(inMem), mimetype="application/octet-stream", headers={
                'Content-Disposition': f'attachment; filename=aggregate-{page}-{count}.json'})
        else:
            return jsonify({"data": list(teams.aggregate(page, count))})
    except Exception as list_exception:
        return error_response(list_exception)


@api.route('/teams/aggregateTS', methods=['GET'])
def aggTS():
    try:
        page = request.args.get('key')
        count = request.args.get('fn')
        d = request.args.get("download", "0")
        if not page or not count:
            raise Exception("missing key and fn for aggregation.")
        if (d == "1"):
            inMem = io.BytesIO(json.dumps({"data": list(teams.aggregateTS(page, count))}).encode('utf-8'))
            return Response(gg(inMem), mimetype="application/octet-stream", headers={
                'Content-Disposition': f'attachment; filename=aggregate-{page}-{count}.json'})
        else:
            return jsonify({"data": list(teams.aggregateTS(page, count))})
    except Exception as list_exception:
        return error_response(list_exception)


def error_response(current_exception=None, data={"status": "error"}, err_code=500):
    """
    Helper function to compose a Response object via jsonify
    """
    res = jsonify({**data, "err_code": err_code, "msg": f'{current_exception!r}'}
                  if current_exception else {**data, "err_code": err_code})
    res.status_code = err_code
    return res


##
# start the web service
##
if __name__ == '__main__':
    api.run(host='0.0.0.0', port=4777, debug=True)
