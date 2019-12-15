#README Dev 2:
#Using Memcached to cache JSON responses
#Modifying the existing xspy.py(XSPF Code)

#$ pip3 install --user pymemcache
#sudo apt-get install memcached
#sudo service memcached start

#Run using:  export FLASK_APP=cachedxspf
#            flask run

from flask import request, jsonify
#from pymemcache.client import base
import pymemcache
from pymemcache.client import base
from pymemcache import serde
#from pymemcache.client.base import Client
import requests
import xspf
from flask import Flask
app = Flask(__name__)
import json


@app.route("/")
def hello():
    return "Welcome to XSPF conversion! Please add playlist id(existing id's are 1,2,3,4,5) into /xspf/playlist.xspf/  URL to get the details."


def do_playlist_query(id):
    r = requests.get("http://localhost:8000/playlists/"+id)
    r= r.json()
    return r

def do_user_query(username):
    r= requests.get("http://localhost:8000/users/"+username)
    r=r.json()
    return r

@app.route("/xspf/playlist.xspf/<string:id>")
def playlists(id):
    #instantiating the client
    client = base.Client(('localhost', 11211),serializer=serde.python_memcache_serializer,deserializer=serde.python_memcache_deserializer)
    #now client object started on port 11211
    #store the key-value pair!
    result = client.get(id)
    #if the cached object does not exist:

    if result is None:
        #make the HTTP request from the microservice and store the json response in Memcached with expiration time!
        result = do_playlist_query(id)

        user_details=do_user_query(result[0]['username'])


        username=result[0]['username']
        result[0]['username']=user_details
        trackList = result[1]
        l1=[]

        #loop to request track details(from desc service) of different tracks in the playlist
        user_desc=[]
        for tracks in trackList:
            #calling the tracks service here: (directly from db)
            track_details= requests.get(tracks['trackurl'])

            track_details=track_details.json()
            l1.append(track_details)
            #for each track, calling the description service
            user_desc=requests.get("http://localhost:8000/description/"+username+'/'+track_details[0]['URL_media'])
            user_desc=user_desc.json()
            track_details[0]['description']=user_desc[track_details[0]['URL_media']]
            #track_details.update(user_desc)

        #store the JSON response in Memcached with expiration of atleast 60 sec
        result[1]=l1
        client.set(id, result, 100)
        
    #if the cached object exists: use its value(result) to construct the xspf!
    x= xspf.Xspf()

    print("Hello ",result)
    #using result json object to construct the xspf

    x.title=result[0]['playlist_title']
    x.creator=result[0]['username'][0]['full_name']
    x.info=result[0]['username'][0]['email']
    trackList=result[1]

    #each playlist of user has multiple tracks such as file1, file2, file3,file4.mp3
    for track in trackList:
        tr1=xspf.Track()
        track=track[0]
        tr1.title=track['track_title']
        tr1.creator=track['artist']
        tr1.duration=track['track_length']
        tr1.album=track['album_title']
        tr1.identifier="http://localhost:9000/media/"+track['URL_media']
        tr1.annotation=track['description']
        x.add_track(tr1)
    y=x.toXml()
    return y, 200,{'Content-Type': 'application/xml; charset=utf-8'}
