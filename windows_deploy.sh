#!/usr/bin/env bash

python3 ./setDebug
eb deploy
#
#if [[ $1 != "prod" && $1 != "dev" ]]; then
#    echo "please specify 'prod' or 'dev' to deploy"
#    exit 1;
#fi
#
#
#DEPLOY_FILE_NAME="aca-dashboard"-$1
#S3_BUCKET="wageup-deployments"
#S3_FOLDER="aca_dashboard"
#APPLICATION_NAME="aca-dashboard-"$1
#
#
##build the tar file
#zipfilename=${DEPLOY_FILE_NAME}.tar.gz
#tar -zcvf $zipfilename .
#echo $zipfilename " created"
#
#
##push the tar file to s3
#s3_target=s3://${S3_BUCKET}/${S3_FOLDER}/
#echo $s3_target
#echo $zipfilename
#
#echo "run: aws s3 cp" + $zipfilename + $s3_target
#s3_location=bucket=${S3_BUCKET},bundleType=tgz,key=${S3_FOLDER}/${zipfilename}
#echo "run: set s3_location=" + s3_location
#echo "run: aws "
#
#
#aws s3 cp $zipfilename $s3_target
#s3_location=bucket=${S3_BUCKET},bundleType=tgz,key=${S3_FOLDER}/${zipfilename}
#
##deploy
#aws deploy create-deployment \
#  --application-name aca-dasboard-$1-app \
#  --deployment-config-name CodeDeployDefault.HalfAtATime \
#  --file-exists-behavior OVERWRITE \
#  --deployment-group-name aca-dasboard-$1-main-group \
#  --s3-location $s3_location
#
#
#
#aws deploy create-deployment \
#  --application-name aca-dasboard-dev-app \
#  --deployment-config-name CodeDeployDefault.HalfAtATime \
#  --file-exists-behavior OVERWRITE \
#  --deployment-group-name aca-dasboard-dev-main-group \
#  --s3-location bucket=wageup-deployments,bundleType=tgz,key=aca_dashboard/aca-dashboard-dev.tar.gz
