# The AWS region to deploy into
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

# The EC2 instance type (size of the server)
# t3.medium = 2 vCPUs, 4 GB RAM — enough for OpenEMR + agent + MariaDB
variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.medium"
}

# A name prefix for all resources, so they're easy to identify in the AWS console
variable "project_name" {
  description = "Project name used to tag and name resources"
  type        = string
  default     = "openemr-agent"
}
