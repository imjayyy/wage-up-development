#!/usr/bin/env bash

isDebugTrue="$(grep ^DEBUG ./root/settings.py)"
debug_bool="$(echo "$isDebugTrue" | sed "s/ //g" | cut -d = -f 2)"

if [[ $debug_bool == 'True' ]]; then
    echo "DEBUG in root/settings.py must be set to False"
    exit 0
fi

if [[ $1 != "prod" && $1 != "dev" ]]; then
    echo "please specify 'prod' or 'dev' as the first argument to deploy"
    exit 1;
fi

if [[ $2 != "ace" && $2 != "aca" && $2 != "demo" ]]; then
    echo "please specify the client as the second argument. Valid options are 'ace' or 'aca'"
    exit 1;
fi


#  push comment file
#python manage.py collectstatic
#aws s3 cp static s3://wageup-static/root-static --recursive
DEPLOY_FILE_NAME="$2-dashboard"-$1
S3_BUCKET="wageup-deployments"
S3_FOLDER="$2_dashboard"
APPLICATION_NAME="$2-dashboard-"$1


#delete old tar files
rm *.tar.gz

#build the tar file
zipfilename=${DEPLOY_FILE_NAME}.tar.gz
tar -zcvf $zipfilename .
echo $zipfilename " created"


#push the tar file to s3
s3_target=s3://${S3_BUCKET}/${S3_FOLDER}/
echo $s3_target
aws s3 cp $zipfilename $s3_target


s3_location=bucket=${S3_BUCKET},bundleType=tgz,key=${S3_FOLDER}/${zipfilename}

#deploy

aws deploy create-deployment \
  --application-name n-$2-dashboard-$1-app \
  --deployment-config-name CodeDeployDefault.HalfAtATime \
  --file-exists-behavior OVERWRITE \
  --deployment-group-name n-$2-dashboard-$1-main-group \
  --s3-location $s3_location \
  --ignore-application-stop-failures


#if creating new deployment, make sure that you copy
# application ne and deployment-group-name from terraform outputs
