#! /usr/bin/bash

cd ./tex
mkdir -p build_artifacts
docker build -t report_builder .
docker create --name built_report report_builder
docker cp built_report:/app/main.log ./build_artifacts/
docker cp built_report:/app/main.pdf ./build_artifacts/
docker cp built_report:/app/main.blg ./build_artifacts/
docker rm built_report