import boto3
import botocore
from configparser import ConfigParser

config = ConfigParser()
config.read('config.ini')

ec2 = boto3.resource('ec2', region_name="us-east-1",
                     aws_access_key_id=config.get('AWS_EC2', 'access_key_id'),
                     aws_secret_access_key=config.get('AWS_EC2', 'secret_access_key'))


def view_all_instances():
	"""
	This function takes not arguments.
	It simply returns a list of all instances that have been set up on AWS EC2.
	Returns:
		list of instance_objs
	"""
	instance_lst = []

	for instance in ec2.instances.all():
		instance_lst.append(instance)

	return instance_lst

view_all_instances()