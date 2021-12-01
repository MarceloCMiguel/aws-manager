import boto3
import os
from functions import *
from variables import *







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
                          
policy = create_auto_scaling_policy(as_north_virginia_,AUTO_SCALING_POLICY_NAME,AUTO_SCALING_GROUP_NAME)

listener_arn = create_listener(lb_north_virginia_,load_balancer_arn,tg_arn_django)