from logging import log
import os
from log import logging
#create a key_pair

def create_key_pair(client,key_name:str):
    key_pair = client.create_key_pair(KeyName=key_name)

    private_key = key_pair["KeyMaterial"]

    # write private key to file with 400 permissions
    logging.info(f"Writing {key_name}.pem in directory ./")
    with os.fdopen(os.open(f"./{key_name}.pem", os.O_WRONLY | os.O_CREAT, 0o400), "w+") as handle:
        handle.write(private_key)
    return key_pair

#delete a key_pair
def delete_key_pair(client,key_name:str):
    key_pair = client.delete_key_pair(KeyName=key_name)
    logging.warning(f"removing {key_name} if exist")
    # write private key to file with 400 permissions
    try:
        os.remove("./" + key_name + ".pem")
        
    except:
        pass


def create_an_instance(client, ami,key_name,user_data,sec_group_name,sec_group_id):
    
    instancetype = "t2.micro"
    logging.info(f"Creating an instance with {instancetype}, and keyname {key_name['KeyName']}")
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
    logging.info(f"Instance id: {instance_id}. Instance Public IP:{instance_ip}")
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
        logging.warning(f"Deleting Instances ids {list_instances_id}")
        waiter = client.get_waiter('instance_terminated')
        client.terminate_instances(InstanceIds=list_instances_id)
        waiter.wait(InstanceIds=list_instances_id)
        logging.warning(f"Instances with keypair {key_pair} deleted")
    else:
        logging.info(f"There is no instances running with the keypair {key_pair}")
        
def delete_sec_group(client,sec_group_name):
    logging.warning(f"Deleting {sec_group_name} if exist")
    find_sec_group = False
    security_groups = client.describe_security_groups()
    for sec_group in security_groups['SecurityGroups']:
        if sec_group['GroupName'] == sec_group_name:
            find_sec_group = True
            is_deleted = False
            while is_deleted ==False:
                try:
                    deleted_sec_group = client.delete_security_group(GroupName=sec_group["GroupName"], GroupId=sec_group["GroupId"])
                    is_deleted = True
                except Exception as e:
                    pass

    if find_sec_group:
        logging.warning(f"{sec_group_name} deleted")
    else:
        logging.info(f"{sec_group_name} not found")

def create_security_group(client, SEC_GROUP_NAME,IP_PERMISSIONS):
    vpcs = client.describe_vpcs()
    vpc_id = vpcs['Vpcs'][0]['VpcId']
    try:
        security_group = client.create_security_group(GroupName=SEC_GROUP_NAME,
                                                    Description="Created with boto3",
                                                    VpcId=vpc_id)
    except Exception as e:
        logging.info(e)

    security_group_id = security_group['GroupId']
    client.authorize_security_group_ingress(
        GroupId=security_group_id,
        IpPermissions = IP_PERMISSIONS
    )
    logging.info(f"Security Group {SEC_GROUP_NAME} created")
    return security_group_id

def create_image(client,instance_id,name_image):
    logging.info(f"Creating Image (AMI) {name_image} using instance ID {instance_id}")
    image_response=client.create_image(InstanceId=instance_id,Name=name_image)
    waiter = client.get_waiter('image_available')
    image_id = image_response["ImageId"]
    waiter.wait(ImageIds=[image_id])
    logging.info(f"Image {name_image} created with id {image_id}")
    return image_id
    
def delete_image(client,image_name):
    logging.warning(f"Deleting {image_name} if exist")
    images_described=client.describe_images(Filters=[
        {
            'Name': 'name',
            'Values': [
                image_name,
            ]
        },
    ])
    if len(images_described['Images'])<1:
        logging.info(f"There is no image with name {image_name}")
        return
    image_id = images_described['Images'][0]['ImageId']
    client.deregister_image(ImageId=image_id)
    logging.warning(f"Image {image_name} deleted")
    
    
def create_load_balancer(client,client_lb, lb_name,sec_group_id):    
    subnets = client.describe_subnets()
    list_subnets_id = []
    for subnet in subnets['Subnets']:
        list_subnets_id.append(subnet['SubnetId'])
    waiter = client_lb.get_waiter('load_balancer_available')    
    logging.info(f"Creating load balancer called {lb_name} with all subnets available")
    load_balancer_created = client_lb.create_load_balancer(Name = lb_name,
                                                                    Subnets=list_subnets_id,
                                                                    SecurityGroups=[sec_group_id],
                                                                    IpAddressType="ipv4",)
    LoadBalancerArn_ = load_balancer_created['LoadBalancers'][0]['LoadBalancerArn']
    waiter.wait(LoadBalancerArns=[LoadBalancerArn_])
    logging.info(f"Load Balancer {lb_name} created")
    return LoadBalancerArn_

def delete_load_balancer(client_lb,lb_name):
    logging.warning(f"Deleting Load Balancer {lb_name} if exist")
    waiter = client_lb.get_waiter('load_balancers_deleted')
    try:
        load_balancers = client_lb.describe_load_balancers(Names=[lb_name])
    except:
        logging.info(f"No Load Balancers with name {lb_name}")
        return
    for lb in load_balancers['LoadBalancers']:
        client_lb.delete_load_balancer(LoadBalancerArn=lb['LoadBalancerArn'])
        lb_arn = lb['LoadBalancerArn']
        waiter.wait(LoadBalancerArns=[lb['LoadBalancerArn']])
        logging.warning(f"Load Balancer {lb_name} with Arn {lb['LoadBalancerArn']} deleted")
        
    
    return lb_arn
    
def create_target_group(client_ec2,client_lb,tg_name):
    vpc_id = client_ec2.describe_vpcs()['Vpcs'][0]['VpcId']
    tg_created=client_lb.create_target_group(
        Name = tg_name,
        Protocol = 'HTTP',
        Port = 8080,
        TargetType='instance',
        VpcId = vpc_id,
        HealthCheckPath='/tasks/'
    )
    tg_arn =tg_created['TargetGroups'][0]['TargetGroupArn']
    logging.info(f"Target group {tg_name} with Arn {tg_arn} created")
    return tg_arn

def delete_target_group(client_lb,tg_name):
    logging.warning(f"Deleting Target Group {tg_name} if exist")
    try:
        tgs=client_lb.describe_target_groups(Names=[tg_name])
    except:
        logging.info(f"No target group with name {tg_name}")
        return
    tg_arn = tgs['TargetGroups'][0]['TargetGroupArn']
    client_lb.delete_target_group(TargetGroupArn = tg_arn)
    logging.warning(f"Target Group {tg_name} deleted")
    
def create_launch_configuration(as_client,launch_config_name,image_id, sec_group_id,key_name):
    logging.info(f"Creating a Launch Configuration {launch_config_name}")   
    try:
        
        as_client.create_launch_configuration(
            LaunchConfigurationName=launch_config_name,
            ImageId=image_id,
            SecurityGroups=[sec_group_id],
            InstanceType='t2.micro',
            KeyName=key_name
        )
    except:
        logging.info(f"A launch configuration already exists with the name {launch_config_name}")
        return
    logging.info(f"Launch Configuration {launch_config_name} created")
    
def delete_launch_configuration(as_client,launch_config_name):
    logging.warning(f"Deleting Launch Configuration {launch_config_name} if exist")
    try:        
        as_client.delete_launch_configuration(
            LaunchConfigurationName = launch_config_name
        )
    except:
        logging.info(f"Launch Configuration {launch_config_name} not found")
        return
    logging.warning(f"Launch Configuration {launch_config_name} deleted")

def create_auto_scaling_group(client_ec2,client_as,as_name,launch_config_name,tg_arn):
    logging.info(f"Creating AutoScaling group with name {as_name}")
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
    logging.info(f"Auto scaling group {as_name} created")

def delete_auto_scaling_group(as_client,as_name):
    logging.warning(f"Deleting AutoScaling group {as_name} if exist")
    try:
        as_client.delete_auto_scaling_group(AutoScalingGroupName = as_name,ForceDelete= True)
        logging.warning(f"AutoScaling group {as_name} deleted")
    except:
        logging.info(f"{as_name} not found")
        
def create_listener(lb_client,load_balancer_arn,tg_arn):
    logging.info("Creating listener to port 80")
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
    logging.warning(f"Deleting all listener with LoadBalancer Arn {lb_arn}")
    try:
        listeners=client_lb.describe_listeners(LoadBalancerArn= lb_arn)
    except:
        logging.info(f"There is no Listener created with LoadBalancerArn {lb_arn}")
        return
    for listener in listeners['Listeners']:
        client_lb.delete_listener(ListenerArn = listener['ListenerArn'])
    logging.warning(f"Listeners with arn {lb_arn} deleted")