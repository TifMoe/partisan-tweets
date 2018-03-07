import boto3
import os
from configparser import ConfigParser

config = ConfigParser()
config.read('config.ini')

ec2 = boto3.resource('ec2', region_name="us-east-2",
                     aws_access_key_id=config.get('AWS_EC2', 'access_key_id'),
                     aws_secret_access_key=config.get('AWS_EC2', 'secret_access_key'))


def fetch_instances():
    instance_lst = []

    for instance in ec2.instances.all():
        instance_lst.append(instance)

    return instance_lst


def update_bash_profile(instance):

    current_directory = os.getcwd()

    os.chdir('/Users/tmoeller')  # change to match the path to your home directory

    with open('.bash_profile', 'r') as file:
        data = file.readlines()

    data[7] = 'export metis_chi18_url="{}"\n'.format(
            instance.public_dns_name)

    with open('.bash_profile', 'w') as file:
        file.writelines(data)

    os.system("source .bash_profile")

    os.chdir(current_directory)
    print(
        """.bash_profile has been updated for the instance with id: {}.
        Be sure to open a new terminal window for changes to take effect""".format(
            instance.id))


def instance_state(instance):
    """
    Returns the state of the instance. I.e. Stopped, running, rebooting etc.
    """

    return instance.state['Name']


def start_instance(instance_obj, safety=True):
    """
    This function takes an instance_obj and starts it up.
    The safety parameters default value is True - this means the function will ask for confirmation before starting the instance.
    If the safety parameter is set to False, it will automatically launch the instance.
    Inputs:
        instance_obj
    Returns:
        None
    """

    if safety:
        question = input("Are you sure you want to start instance {}. [y/n]: ".format(instance_obj.id))

        if question == 'y':
            instance_obj.start()
            print("EC2 Instance with id {} has has been started".format(instance_obj.id))
        else:
            print("Operation aborted")
    else:
        instance_obj.start()
        print("EC2 Instance with id {} has has been started".format(instance_obj.id))


def stop_instance(instance_obj, safety=True):
    """
    This function takes an instance_obj and stops it.
    The safety parameters default value is True - this means the function will ask for confirmation before stopping the instance.
    If the safety parameter is set to False, it will automatically stop the instance.
    NOTE: When stopping in the instance, you will lose all data stored in memory!
    Inputs:
        instance_obj
    Returns:
        None
    """

    if safety:
        question = input("Are you sure you want to stop instance {}. [y/n]: ".format(instance_obj.id))

        if question == "y":
            instance_obj.stop()
            print("EC2 Instance with id {} has has been stopped".format(instance_obj.id))
        else:
            print("Operation aborted")
    else:
        instance_obj.stop()
        print("EC2 Instance with id {} has has been stopped".format(instance_obj.id))