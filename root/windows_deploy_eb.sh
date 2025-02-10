#!/bin/sh
second_input="0"
if [ "$1" = "aaane" ]; then second_input="1"
fi
if [ "$1" = "aca" ]; then second_input="1"
fi
if [ "$1" = "demo" ]; then second_input="1"
fi

if [ "$second_input" -ne "1" ]; then echo "no client specified"
fi
if [ "$second_input" -ne "1" ]; then exit
fi

CLIENT=$1
input="0"
echo "you are using $CLIENT"

if [ "$2" = "prod" ];
then input="1"
fi

if [ "$2" = "dev" ];
then input="1"
fi

if [ "$input" -ne "1" ]; then echo "no environment specified"
fi
if [ "$input" -ne "1" ]; then exit
fi

ENV=%2%

#if "%3%" == "ignore" SET branch="dev"
#
branch=""

if git branch | grep -q "\* aaane_master"; then
  branch="dev"
elif git branch | grep -q "\* aaane_prod"; then
  branch="prod"
elif git branch | grep -q "\* aca_master"; then
  branch="dev"
elif git branch | grep -q "\* aca_prod"; then
  branch="prod"
elif git branch | grep -q "\* demo_dev"; then
  branch="dev"
else
  branch="Invalid"
fi

if [ "$branch" = "Invalid" ]; then
  echo "bad branch" & exit
fi

echo "branch is $branch"
echo "env is $ENV"

if [ "$branch" = "prod" ] && [ "$ENV" = "dev" ]; then
  echo "bad branch" & exit
fi
if [ "$branch" = "dev" ] && [ "$ENV" = "prod" ]; then
  echo "bad branch" & exit
fi

echo "$(dirname "$0")"
rm -rf "$(dirname "$0")/root/whoosh_index"

aws s3 cp s3://wageup-whoosh/"$CLIENT".zip .
unzip "${CLIENT}.zip" -d ./

# Move the directory
mv ./root/"${CLIENT}" ./root/whoosh_index

# Rebuild the index
python ./rebuild_index.py

# Remove zip files
rm whoosh_index.zip
rm "${CLIENT}.zip"

# Compress the directory
zip -r "${CLIENT}.zip" ./root/whoosh_index/

# Upload to S3
aws s3 cp ./"${CLIENT}.zip" s3://wageup-whoosh/"${CLIENT}.zip"

# Clean up zip files
rm whoosh_index.zip
rm "${CLIENT}.zip"

# Deploy with Elastic Beanstalk
eb deploy