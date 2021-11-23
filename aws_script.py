import boto3
import os



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



#create a key_pair
def create_key_pair(client,key_name:str):
    key_pair = client.create_key_pair(KeyName=key_name)

    private_key = key_pair["KeyMaterial"]

    # write private key to file with 400 permissions
    print(f"Writing {key_name}.pem in directory ./")
    with os.fdopen(os.open(f"./{key_name}.pem", os.O_WRONLY | os.O_CREAT, 0o400), "w+") as handle:
        handle.write(private_key)
    return key_pair

#delete a key_pair
def delete_key_pair(client,key_name:str):
    key_pair = client.delete_key_pair(KeyName=key_name)
    print(f"removing {key_name} if exist")
    # write private key to file with 400 permissions
    try:
        os.remove("./" + key_name + ".pem")
        
    except:
        pass


def create_an_instance(client, ami,key_name,user_data,sec_group_name,sec_group_id):
    
    instancetype = "t2.micro"
    print(f"Creating an instance with {instancetype}, and keyname {key_name['KeyName']}")
    if user_data == None:
        instances = client.run_instances(
            ImageId=ami,
            MinCount=1,
            MaxCount=1,
            InstanceType="t2.micro",
            KeyName=key_name['KeyName'],
            SecurityGroupIds=[sec_group_id],
            SecurityGroups=[sec_group_name]
        )
    else:
        instances = client.run_instances(
            ImageId=ami,
            MinCount=1,
            MaxCount=1,
            InstanceType="t2.micro",
            KeyName=key_name['KeyName'],
            UserData = user_data,
            SecurityGroupIds=[sec_group_id],
            SecurityGroups=[sec_group_name]
        )
    for i in instances['Instances']:
        if i['KeyName'] == key_name["KeyName"]:
            instance_id = i['InstanceId']
    waiter = client.get_waiter('instance_status_ok')
    waiter.wait(InstanceIds=[instance_id])
    instance_ip = client.describe_instances(Filters=[
        {
            'Name': 'key-name',
            'Values': [
                key_name['KeyName'],
            ]
        },
        {
            'Name': 'instance-state-name',
            'Values': [
                "running"
            ]
        },
    ],
    )['Reservations'][0]['Instances'][0]['PublicIpAddress']
    print(f"Instance id: {instance_id}\nInstance Public IP:{instance_ip}")
    return instance_id, instance_ip

def delete_instances(client,key_pair):
    list_instances_id = []
    for i in client.describe_instances(Filters=[
        {
            'Name': 'key-name',
            'Values': [
                key_pair,
            ]
        },
        {
            'Name': 'instance-state-name',
            'Values': [
                "pending","running","stopping","stopped"
            ]
        },
    ],
)['Reservations']:
        list_instances_id.append(i['Instances'][0]["InstanceId"])
    if len(list_instances_id) > 0:
        print(f"Deleting Instances ids {list_instances_id}")
        waiter = client.get_waiter('instance_terminated')
        client.terminate_instances(InstanceIds=list_instances_id)
        waiter.wait(InstanceIds=list_instances_id)
        print(f"Instances withs keypair {key_pair} deleted")
    else:
        print(f"There is no instances running with the keypair {key_pair}")
        
def delete_sec_group(client,sec_group_name):
    find_sec_group = False
    security_groups = client.describe_security_groups()
    for sec_group in security_groups['SecurityGroups']:
        if sec_group['GroupName'] == sec_group_name:
            find_sec_group = True
            is_deleted = False
            while is_deleted ==False:
                try:
                    deleted_sec_group = client.delete_security_group(GroupName=sec_group["GroupName"], GroupId=sec_group["GroupId"])
                    #print(deleted_sec_group)
                    is_deleted = True
                except Exception as e:
                    pass

    if find_sec_group:
        print(f"{sec_group_name} deleted")
    else:
        print(f"{sec_group_name} not found")

def create_security_group(client, SEC_GROUP_NAME,IP_PERMISSIONS):
    vpcs = client.describe_vpcs()
    vpc_id = vpcs['Vpcs'][0]['VpcId']
    try:
        security_group = client.create_security_group(GroupName=SEC_GROUP_NAME,
                                                    Description="Created with boto3",
                                                    VpcId=vpc_id)
    except Exception as e:
        print(e)

    security_group_id = security_group['GroupId']
    client.authorize_security_group_ingress(
        GroupId=security_group_id,
        IpPermissions = IP_PERMISSIONS
    )
    print(f"Security Group {SEC_GROUP_NAME} created")
    return security_group_id

def create_image(client,instance_id,name_image):
    image_response=client.create_image(InstanceId=instance_id,Name=name_image)
    waiter = client.get_waiter('image_available')
    image_id = image_response["ImageId"]
    waiter.wait(ImageIds=[image_id])
    print(f"Image {name_image} created with id {image_id}")
    return image_id
    
def delete_image(client,image_name):
    images_described=ec2_north_virginia_.describe_images(Filters=[
        {
            'Name': 'name',
            'Values': [
                image_name,
            ]
        },
    ])
    if len(images_described['Images'])<1:
        print(f"There is no image with name {image_name}")
        return
    image_id = images_described['Images'][0]['ImageId']
    client.deregister_image(ImageId=image_id)
    print(f"Image {image_name} deleted")
    
    
def create_load_balancer(client,client_lb, lb_name,sec_group_id):    
    subnets = client.describe_subnets()
    list_subnets_id = []
    for subnet in subnets['Subnets']:
        list_subnets_id.append(subnet['SubnetId'])
    waiter = client_lb.get_waiter('load_balancer_available')    
    print("Creating load balancer with all subnets available")
    load_balancer_created = client_lb.create_load_balancer(Name = lb_name,
                                                                    Subnets=list_subnets_id,
                                                                    SecurityGroups=[sec_group_id],
                                                                    IpAddressType="ipv4",)
    LoadBalancerArn_ = load_balancer_created['LoadBalancers'][0]['LoadBalancerArn']
    waiter.wait(LoadBalancerArns=[LoadBalancerArn_])
    print(f"Load Balancer {lb_name} created")
    return LoadBalancerArn_

def delete_load_balancer(client_lb,lb_name):
    waiter = client_lb.get_waiter('load_balancers_deleted')
    try:
        load_balancers = client_lb.describe_load_balancers(Names=[lb_name])
    except:
        print(f"No load_balancers with name {lb_name}")
        return
    for lb in load_balancers['LoadBalancers']:
        client_lb.delete_load_balancer(LoadBalancerArn=lb['LoadBalancerArn'])
        lb_arn = lb['LoadBalancerArn']
        waiter.wait(LoadBalancerArns=[lb['LoadBalancerArn']])
        print(f"Load Balancer {lb['LoadBalancerArn']} with name {lb_name} deleted")
        
    
    return lb_arn
    
def create_target_group(client_ec2,client_lb,tg_name):
    vpc_id = ec2_north_virginia_.describe_vpcs()['Vpcs'][0]['VpcId']
    tg_created=lb_north_virginia_.create_target_group(
        Name = tg_name,
        Protocol = 'HTTP',
        Port = 8080,
        TargetType='instance',
        VpcId = vpc_id,
        HealthCheckPath='/tasks/'
    )
    tg_arn =tg_created['TargetGroups'][0]['TargetGroupArn']
    print(f"Target group {tg_name} with arn {tg_arn} created")
    return tg_arn

def delete_target_group(client_lb,tg_name):
    try:
        tgs=client_lb.describe_target_groups(Names=[tg_name])
    except:
        print(f"No target group with name {tg_name}")
        return
    tg_arn = tgs['TargetGroups'][0]['TargetGroupArn']
    client_lb.delete_target_group(TargetGroupArn = tg_arn)
    print(f"Target Group {tg_name} deleted")
    
def create_launch_configuration(as_client,launch_config_name,image_id, sec_group_id,key_name):    
    try:
        
        as_client.create_launch_configuration(
            LaunchConfigurationName=launch_config_name,
            ImageId=image_id,
            SecurityGroups=[sec_group_id],
            InstanceType='t2.micro',
            KeyName=key_name
        )
    except:
        print(f"A launch configuration already exists with the name {launch_config_name}")
        return
    print(f"Launch Configuration {launch_config_name} created")
    
def delete_launch_configuration(as_client,launch_config_name):
    try:        
        as_north_virginia_.delete_launch_configuration(
            LaunchConfigurationName = launch_config_name
        )
    except:
        print(f"Launch configuration {launch_config_name} not found")
        return
    print(f"Launch configuration {launch_config_name} deleted")

def create_auto_scaling_group(client_ec2,client_as,as_name,launch_config_name,tg_arn):
    
    list_zones = []
    for zones in client_ec2.describe_availability_zones()['AvailabilityZones']:
        list_zones.append(zones['ZoneName'])
    auto_scaling_created = client_as.create_auto_scaling_group(
        AutoScalingGroupName=as_name,
        LaunchConfigurationName=launch_config_name,
        MinSize=1,
        MaxSize = 3,
        TargetGroupARNs=[tg_arn],
        AvailabilityZones = list_zones
    )
    print(f"Auto scaling group {as_name} created")

def delete_auto_scaling_group(as_client,as_name):
    try:
        as_client.delete_auto_scaling_group(AutoScalingGroupName = as_name,ForceDelete= True)
    except:
        print(f"{as_name} not found")
        
def create_listener(lb_client,load_balancer_arn,tg_arn):
    listener_created=lb_client.create_listener(
        LoadBalancerArn= load_balancer_arn,
        Protocol='HTTP',
        Port=80,
        DefaultActions=[
            {
                'Type': 'forward',
                'TargetGroupArn': tg_arn

            }
        ]
    )
    listener_arn = listener_created['Listeners'][0]['ListenerArn']
    return listener_arn
        
def delete_listeners(client_lb, lb_arn):
    
    try:
        listeners=client_lb.describe_listeners(LoadBalancerArn= lb_arn)
    except:
        print(f"There is no Listener created with LoadBalancerArn {lb_arn}")
        return
    for listener in listeners['Listeners']:
        client_lb.delete_listener(ListenerArn = listener['ListenerArn'])
    print(f"Listeners with arn {lb_arn} deleted")


#checking if boto3 client is working
iam = boto3.client("iam")

for user in iam.list_users()["Users"]:
    if user["UserName"] == "marcelo":
        print(user["UserName"])
        print(user["UserId"])
        print(user["Arn"])
        print(user["CreateDate"])


#connection to ec2
ec2_ohio = boto3.client('ec2', region_name='us-east-2')
ec2_north_virginia_ = boto3.client('ec2', region_name='us-east-1')
lb_north_virginia_ = boto3.client('elbv2',region_name="us-east-1")
as_north_virginia_ = boto3.client('autoscaling',region_name="us-east-1")

lb_arn=delete_load_balancer(lb_north_virginia_,LB_NAME)

delete_auto_scaling_group(as_north_virginia_,AUTO_SCALING_GROUP_NAME)


delete_image(ec2_north_virginia_,IMAGE_DJ)


delete_launch_configuration(as_north_virginia_,LAUNCH_CONFIG_NAME)



# if lb_arn is not None:
#     delete_listeners(lb_north_virginia_, lb_arn)






delete_instances(ec2_ohio,KEY_PAIR_OHIO_NAME)
delete_instances(ec2_north_virginia_,KEY_PAIR_NORTH_VIRGINIA_NAME)



delete_key_pair(ec2_ohio,KEY_PAIR_OHIO_NAME)
delete_key_pair(ec2_north_virginia_,KEY_PAIR_NORTH_VIRGINIA_NAME)

delete_target_group(lb_north_virginia_,TG_NAME)


delete_sec_group(ec2_ohio,SEC_GROUP_NAME_DB)
delete_sec_group(ec2_north_virginia_,SEC_GROUP_NAME_DJ)








key_pair_ohio = create_key_pair(ec2_ohio,KEY_PAIR_OHIO_NAME)
key_pair_north_virginia = create_key_pair(ec2_north_virginia_,KEY_PAIR_NORTH_VIRGINIA_NAME)

sec_group_id_db = create_security_group(ec2_ohio,SEC_GROUP_NAME_DB,IpPermissions_DB)
sec_group_id_dj = create_security_group(ec2_north_virginia_,SEC_GROUP_NAME_DJ,IpPermissions_DJ)

postgres_ID, postgres_IP = create_an_instance(ec2_ohio,AMI_UBUNTU_OHIO,key_pair_ohio,comand_db,SEC_GROUP_NAME_DB,sec_group_id_db)
command_django = command_django.replace("IP_REPLACE",str(postgres_IP))
django_ID, django_IP = create_an_instance(ec2_north_virginia_,AMI_UBUNTU_NORTH_VIRGINIA,key_pair_north_virginia,command_django,SEC_GROUP_NAME_DJ,sec_group_id_dj)


image_dj_id = create_image(ec2_north_virginia_,django_ID,IMAGE_DJ)
delete_instances(ec2_north_virginia_,KEY_PAIR_NORTH_VIRGINIA_NAME)


tg_arn_django=create_target_group(ec2_north_virginia_,lb_north_virginia_,TG_NAME)

load_balancer_arn = create_load_balancer(ec2_north_virginia_,lb_north_virginia_,LB_NAME,sec_group_id_dj)






create_launch_configuration(as_north_virginia_,LAUNCH_CONFIG_NAME,image_dj_id,sec_group_id_dj,KEY_PAIR_NORTH_VIRGINIA_NAME)


create_auto_scaling_group(ec2_north_virginia_,as_north_virginia_,
                          AUTO_SCALING_GROUP_NAME,LAUNCH_CONFIG_NAME,
                          tg_arn_django)

listener_arn = create_listener(lb_north_virginia_,load_balancer_arn,tg_arn_django)