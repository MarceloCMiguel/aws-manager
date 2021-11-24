# cloud-project

This repository contains the aws manager, which implements a [Django application](https://github.com/MarceloCMiguel/tasks) using Load Balancer and Auto Scaling. An instance is also created storing a PostgreSQL database. This application was made in Boto3.


## How to run

### Aws CLI

First, you need to configure your credentials in [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html).

After installing AWS CLI, configure your credentials running:

- `aws configure`

### Script

After that, you can run the script `aws_script.py` without problems. Check the logs file called `script.log` in the directory while running to see the logs of the application.
