#variables
OHIO_REGION = "us-east-2"
NORTH_VIRGINIA = "us-east-1"
AMI_UBUNTU_OHIO = "ami-020db2c14939a8efb"
AMI_UBUNTU_NORTH_VIRGINIA = "ami-0279c3b3186e54acd"
KEY_PAIR_OHIO_NAME = "key_pair_marcelo_ohio"
KEY_PAIR_NORTH_VIRGINIA_NAME = "key_pair_marcelo_north_virginia"
SEC_GROUP_NAME_DB = "Sec_Group_DB"
SEC_GROUP_NAME_DJ = "Sec_Group_DJ"
IMAGE_DJ = "Image Django Instance"
LB_NAME = "LB-Django"
TG_NAME = "TG-DJANGO"
LAUNCH_CONFIG_NAME = "Launch-Config-Django"
AUTO_SCALING_GROUP_NAME = "AS-DJANGO"
AUTO_SCALING_POLICY_NAME = "AS-POLICY-DJANGO"



# commands line
comand_db="""
#cloud-config

runcmd:
- cd /
- sudo apt update
- sudo apt install postgresql postgresql-contrib -y
- sudo su - postgres
- sudo -u postgres psql -c "CREATE USER cloud WITH PASSWORD 'cloud';"
- sudo -u postgres psql -c "CREATE DATABASE tasks;"
- sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE tasks TO cloud;"
- sudo echo "listen_addresses = '*'" >> /etc/postgresql/10/main/postgresql.conf
- sudo echo "host all all 0.0.0.0/0 trust" >> /etc/postgresql/10/main/pg_hba.conf
- sudo ufw allow 5432/tcp -y
- sudo systemctl restart postgresql

"""

command_django="""
#cloud-config

runcmd:
- cd /home/ubuntu 
- sudo apt update -y
- git clone https://github.com/MarceloCMiguel/tasks.git
- cd tasks
- sed -i "s/node1/IP_REPLACE/g" ./portfolio/settings.py
- ./install.sh
- sudo ufw allow 8080/tcp -y
- sudo reboot
"""


# permissions
IpPermissions_DB = [
    {
        'IpProtocol': 'tcp',
        'FromPort': 22,
        'ToPort': 22,
        'IpRanges': [
            {'CidrIp': '0.0.0.0/0'}
        ]
    },
    {
        'IpProtocol': 'tcp',
        'FromPort': 5432,
        'ToPort': 5432,
        'IpRanges': [
            {'CidrIp': '0.0.0.0/0'}
        ]
    },
    {
            "FromPort": 80,
            "ToPort": 80,
            "IpProtocol": "tcp",
            "IpRanges": [
                {"CidrIp": "0.0.0.0/0", "Description": "internet"},
            ],
        },
]


IpPermissions_DJ = [
    {
        'IpProtocol': 'tcp',
        'FromPort': 22,
        'ToPort': 22,
        'IpRanges': [
            {'CidrIp': '0.0.0.0/0'}
        ]
    },
    {
        'IpProtocol': 'tcp',
        'FromPort': 8080,
        'ToPort': 8080,
        'IpRanges': [
            {'CidrIp': '0.0.0.0/0'}
        ]
    },
    {
            "FromPort": 80,
            "ToPort": 80,
            "IpProtocol": "tcp",
            "IpRanges": [
                {"CidrIp": "0.0.0.0/0", "Description": "internet"},
            ],
        },
]