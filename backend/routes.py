from . import app
import os
import json
import pymongo
from flask import jsonify, request, make_response, abort, url_for  # noqa; F401
from pymongo import MongoClient
from bson import json_util
from pymongo.errors import OperationFailure
from pymongo.results import InsertOneResult
from bson.objectid import ObjectId
import sys

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(SITE_ROOT, "data", "songs.json")
songs_list: list = json.load(open(json_url))

# client = MongoClient(
#     f"mongodb://{app.config['MONGO_USERNAME']}:{app.config['MONGO_PASSWORD']}@localhost")
mongodb_service = os.environ.get('MONGODB_SERVICE')
mongodb_username = os.environ.get('MONGODB_USERNAME')
mongodb_password = os.environ.get('MONGODB_PASSWORD')
mongodb_port = os.environ.get('MONGODB_PORT')

print(f'The value of MONGODB_SERVICE is: {mongodb_service}')

if mongodb_service == None:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
    # abort(500, 'Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)

if mongodb_username and mongodb_password:
    url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_service}"
else:
    url = f"mongodb://{mongodb_service}"


print(f"connecting to url: {url}")

try:
    client = MongoClient(url)
except OperationFailure as e:
    app.logger.error(f"Authentication error: {str(e)}")

db = client.songs
db.songs.drop()
db.songs.insert_many(songs_list)

def parse_json(data):
    return json.loads(json_util.dumps(data))

######################################################################
# INSERT CODE HERE
######################################################################
@app.route("/health", methods=["GET"])
def health():
    return {"status": "OK"}

@app.route("/count", methods=["GET"])
def count():
    count = db.songs.count_documents({})
    return {"count": count}, 200

@app.route('/song', methods=['GET'])
def songs():
    songs_list = list(db.songs.find({}))
    for song in songs_list:
        song['_id'] = str(song['_id'])
    return jsonify({"songs": songs_list}), 200

@app.route('/song/<id>', methods=['GET'])
def get_song_by_id(id):
    song = db.songs.find_one({"id": int(id)})
    if song is None:
        return jsonify({"message": "song with id not found"}), 404
    song['_id'] = str(song['_id'])
    return jsonify(song), 200

@app.route('/song', methods=["POST"])
def create_song():
    song_data = request.get_json()
    is_exists = db.songs.find_one({"id": song_data.get("id")})

    if is_exists:
        return jsonify({"Message": f"song with id {song_data.get('id')} already present"}), 302

    result = db.songs.insert_one(song_data)
    return jsonify({"inserted id": {"$oid": str(result.inserted_id)}}), 201

@app.route('/song/<int:id>', methods=["PUT"])
def update_song(id):
    song_data = request.get_json()
    song = db.songs.find_one({"id": id})

    if not song:
        return jsonify({"message": "song not found"}), 404

    is_changed = False

    for field in song_data:
        if song.get(field) != song_data.get(field):
            is_changed = True
            break

    if not is_changed:
        return jsonify({"message": "song found, but nothing updated"}), 200

    db.songs.update_one({"id": id}, {"$set": song_data})

    return jsonify({
        "_id": {"$oid": str(song["_id"])},
        "id": id,
        "lyrics": song_data.get("lyrics", song["lyrics"]),
        "title": song_data.get("title", song["title"])
    }), 200

@app.route('/song/<int:id>', methods=["DELETE"])
def delete_song(id):
    result = db.songs.delete_one({"id": id})

    if result.deleted_count == 0:
        return jsonify({"message": "song not found"}), 404

    return "", 204
