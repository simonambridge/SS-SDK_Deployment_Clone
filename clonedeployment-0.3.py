#!/usr/bin/env python
# coding: utf-8
###############
# History
# 0.1 - basic SELF managed deployment cloning
# 0.2 - added support for AWS managed deployments
# 0.3 - 1/12/23 removed data protector and sql server bdc libraries that aren't supported in 5.7.2
###############
# Pre-reqs: Install SDK
# 1. Install Python 3.x
# 2. pip3 install streamsets~=5.2
# - Successfully installed streamsets-5.2.1
# 3. Create a sdk.properties file
###############
# Run:
# % /usr/bin/python3 clonedeployment-0.2.py
#################################################

from streamsets.sdk import ControlHub
# from streamsets.sdk import Transformer
# import json
import javaproperties


# Retrieve the credentials
# ========================
# Specify the path to the properties file
file_path = "/Users/dilbert/.sdk/sdk.properties"
print("Getting SDK properties...")
print("")

# Open the file in read mode
with open(file_path, "r") as f:
    # Load the properties from the file
    properties = javaproperties.load(f)

# print(properties)

# Retrieve the sdk configuration from the properties object
username       = properties.get("username")
password       = properties.get("password")
credential_id  = properties.get("credential_id")
token          = properties.get("token")

engine_id      = properties.get("engine_id")
environment_id = properties.get("environment_id")
deployment_id  = properties.get("deployment_id")

# Print the credentials
print("Credentials:")
print("  Username:      ", username)
print("  Password:      ", password)
print("  credential_id: ", credential_id)
print("  token:         ", token)
print("Origin Deployment & Engine details:")
print("  environment_id:", environment_id)
print("  deployment_id: ", deployment_id)
print("  engine_id:     ", engine_id)
print("")


# Set your new deployment config here
# ===================================
print("Setting new deployment parameters...")
print("")
old_deployment_id = deployment_id # This is the deployment we want to copy

new_deployment_name = 'AWS - SDC 5.7.2 - EMEA - M4.Large' # used in builder
# new_deployment_type = 'SELF'        # used in builder
new_deployment_type = 'EC2'        # used in builder
new_deployment_tags = ['simon-sdk-generated','AWS','Engine-SDC','SDC-V:5.7.2'] # used in builder
new_engine_type     = 'DC'                # used in builder

new_engine_version  = '5.7.2'        # used in builder
# new_engine_version_id='DC:5.7.2::Released' - not needed, autogenerated
new_engine_labels   = ['5.7.2','demo','latest']

print("Target Deployment & Engine details:")
print("  environment_id:", environment_id)
print("  Deployment ", new_deployment_name)
print("  Deployment type", new_deployment_type)
print("  Deployment tags", new_deployment_tags)
print("  Engine type",new_engine_type)
print("  Engine version",new_engine_version)
print("  Engine labels",new_engine_labels)
print("")

input("Press Enter to continue or ^C to exit...")
print("")

# Login to DataOps
print("Logging in to DataOps...")
sch = ControlHub(credential_id=credential_id, token=token)

# Get the existing environment
print("Get environment & deployment details...")
env=sch.environments.get(environment_id=environment_id)

# >>> get deployment type
# Get the deployment to copy
old_deployment = sch.deployments.get(deployment_id=old_deployment_id)

# Copy the old deployment stage libraries
libs = old_deployment.engine_configuration.stage_libs

# Get a deployment builder
deployment_builder = sch.get_deployment_builder(deployment_type=new_deployment_type)

# Create a vanilla deployment with our new header info
new_deployment = deployment_builder.build(deployment_type=new_deployment_type, 
                                          deployment_name=new_deployment_name, 
                                          environment=env,
                                          engine_type=new_engine_type,
                                          engine_version=new_engine_version,
                                          deployment_tags=new_deployment_tags)

new_deployment.engine_instances = 1

# Create A new Deployment
print("Creating the new deployment...")
sch.add_deployment(new_deployment)

############ CONFIGURE THE VANILLA NEW DEPLOYMENT ################

# Update the vanilla Deployment
print("Updating the new deployment config...")
# Need to 
# 1. Copy the config of the source deployment
# 2. Ensure we have the new version of the libraries for the clone deployment
# -- NB the snowflake lib has changed from enterprise lib to sdc lib, so the name has changed
# -- Other enterprise libs need to be added back in with their version number too.
# 3. Apply CSP-specific attribute updates

# 1. Copy the source deployment config
# ====================================
# Update Deployment Engine labels - default is "['5.5', 'latest']"
new_deployment.engine_configuration.engine_labels=new_engine_labels # check for other uncopied attributes

# Update the External Resource config
new_deployment.engine_configuration.external_resource_source = old_deployment.engine_configuration.external_resource_source

# Update the Advanced Data Collector config
new_deployment.engine_configuration.advanced_configuration.data_collector_configuration=old_deployment.engine_configuration.advanced_configuration.data_collector_configuration
new_deployment.engine_configuration.advanced_configuration.credential_stores=old_deployment.engine_configuration.advanced_configuration.credential_stores
new_deployment.engine_configuration.advanced_configuration.log4j2=old_deployment.engine_configuration.advanced_configuration.log4j2
new_deployment.engine_configuration.advanced_configuration.proxy_properties=old_deployment.engine_configuration.advanced_configuration.proxy_properties
new_deployment.engine_configuration.advanced_configuration.security_policy=old_deployment.engine_configuration.advanced_configuration.security_policy

# Update the Java config
new_deployment.engine_configuration.java_configuration=old_deployment.engine_configuration.java_configuration._data

# 2. Update the libraries 
# =======================
print("Updating the new deployment stage libraries...")
new_libs = []
new_deployment.engine_configuration.stage_libs = new_libs

# Replacement of Enterprise Stage Libraries with standard stage libraries
for i in range(len(libs)):
     if libs[i] == 'snowflake':
         new_libs.append('sdc-snowflake')
     elif 'synapse' in libs[i]:
        if 'azure' not in new_libs:
             new_libs.append('azure')
     elif 'protector' in libs[i]:
    #     new_libs.append('dataprotector:1.9.0') # causes error in 5.7.2
        print(" skipping data protector")
     #elif 'databricks' in libs[i]:
     #    new_libs.append('databricks:1.7.0')
     #elif 'oracle' in libs[i]:
     #    new_libs.append('oracle:1.4.0')
     elif 'sql-server-bdc' in libs[i]:    # causes error in 5.7.2
        print(" skipping sql-server-bdc")
     #    new_libs.append('sql-server-bdc:1.0.1')
     else:
         new_libs.append(libs[i])

# print(new_libs)

# Update the deployment with new libraries 
new_deployment.engine_configuration.stage_libs = new_libs

# 3. CSP-specific updates
# =======================
# For EC2 set the instance profile as otherwise the deployment will be left in incomplete state
if new_deployment_type=="EC2":
    print("EC2 Configuration...")
    print("  Updating the EC2 instance profile...")
#    new_deployment.instance_profile=env.default_instance_profile
    new_deployment.instance_profile=old_deployment.instance_profile
    print("  Updating the EC2 instance type...")
    new_deployment.ec2_instance_type=old_deployment.ec2_instance_type
    print("  Updating the EC2 key source...")
    new_deployment.ssh_key_source=old_deployment.ssh_key_source
    print("  Updating the EC2 key pair name...")
    new_deployment.key_pair_name=old_deployment.key_pair_name

# update the new deployment with the configuration
print("Updating the new deployment in DataOps...")
sch.update_deployment(new_deployment)

# Start the deployment
#sch.start_deployment(new_deployment)





