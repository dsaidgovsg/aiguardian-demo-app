#!/bin/bash -ex

echo "Retrieving env file from SSM parameter $DOT_ENV_SSM_PARAMETER_NAME"
python -c "
import boto3
import os

ssm = boto3.client('ssm', region_name='ap-southeast-1')
parameter_name = os.getenv('DOT_ENV_SSM_PARAMETER_NAME')

response = ssm.get_parameter(
    Name=parameter_name,
    WithDecryption=True
)

env_value = response['Parameter']['Value']

with open('.env', 'a') as env_file:
    env_file.write(env_value)
"
echo "Done retrieving env file"

exec "$@"
