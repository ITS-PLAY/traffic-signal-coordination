#!/bin/bash

set -eo pipefail
# 设置app name
export APP_NAME=ts-generator
VERSION=1.0.0-build.$(date +%Y%m%d%H%M%S)

# 拉取algorithm-api-base代码
git clone https://gl.ge.cn/ZHJT/algorithm-api-base.git

# 生成合并后的python代码到algorithm-api-base目录
python3 merge_project.py . ts_generator.py main.py

pushd algorithm-api-base
git checkout main
cp ../ts_generator.py algorithms/ts_generator.py
./build.sh $APP_NAME $VERSION
pushd

cd $(dirname $0)

deploy() {
    SERVER=$1
    if [ "x$DEPLOY" = "x1" ]; then
            echo "Deploy to $SERVER"

            curl -X POST \
            --fail \
            -F token=$GITOPS_PIPELINE_TRIGGER_TOKEN \
            -F "ref=main" \
            -F "variables[PKG]=$SERVER" \
            -F "variables[VERSION]=$VERSION" \
            https://gl.ge.cn/api/v4/projects/246/trigger/pipeline
    fi
}

packing() {
    sed -E -i "s|__APP_NAME__|$APP_NAME|g" helm/Chart.yaml
    sed -E -i "s|__VERSION__|$VERSION|g" helm/Chart.yaml
    sed -E -i "s|__APP_NAME__|$APP_NAME|g" helm/values.yaml
    sed -E -i "s|__VERSION__|$VERSION|g" helm/values.yaml
    export APP_NAME=$APP_NAME
    export APP_DESC=$APP_NAME
    export DOCKER_IMAGE_NAME=zhjt/$APP_NAME
    helm package helm --version="$VERSION"
    helm push $APP_NAME-$VERSION.tgz oci://cr.ytsd.cc/helm-charts
}

if [ "x$CI_COMMIT_REF_NAME" = "xmain" ]; then
    packing

    if [ "x$DEPLOY" = "x1" ]; then
        helm upgrade --reset-values --install -n zhjt $APP_NAME ./helm
    fi

    if [ "x$PKG" == "xhza" ]; then
        deploy hza/elastic/zhjt/ts-generator
    fi
fi


