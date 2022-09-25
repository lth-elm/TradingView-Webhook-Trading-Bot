#!/bin/sh

docker stop flask_app_v1

docker rmi -f flask_app:v1.0

docker build . -t flask_app:v1.0