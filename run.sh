#!/bin/sh

docker stop flask_app_v1

docker rm flask_app_v1

docker run -d -p 5000:5000 --name flask_app_v1 flask_app:v1.0
