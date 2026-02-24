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

# -------------------------------------------------------
# Sensitive variables — passed via terraform.tfvars
# NEVER hardcode these values in .tf files!
#
# To set them, create infra/terraform.tfvars (gitignored):
#   db_root_password  = "your-strong-password"
#   db_app_password   = "your-strong-password"
#   anthropic_api_key = "sk-ant-api03-..."
#   langchain_api_key = "lsv2_pt_..."
# -------------------------------------------------------
variable "db_root_password" {
  description = "Root password for the RDS MariaDB instance"
  type        = string
  sensitive   = true # Terraform will mask this in plan/apply output
}

variable "db_app_password" {
  description = "Application user (openemr) password for MariaDB"
  type        = string
  sensitive   = true
}

variable "anthropic_api_key" {
  description = "Anthropic API key for the AI agent's Claude model"
  type        = string
  sensitive   = true
}

variable "langchain_api_key" {
  description = "LangChain/LangSmith API key for observability tracing"
  type        = string
  sensitive   = true
  default     = "" # Optional — tracing can be disabled
}

# -------------------------------------------------------
# Infrastructure sizing variables
# Adjust these to change resource sizes without editing
# task definitions directly.
# -------------------------------------------------------
variable "db_instance_class" {
  description = "RDS instance size. db.t3.micro = 2 vCPUs, 1 GB RAM (~$13/month)"
  type        = string
  default     = "db.t3.micro"
}

variable "openemr_task_cpu" {
  description = "CPU units for OpenEMR Fargate task. 1024 = 1 vCPU"
  type        = number
  default     = 512 # 0.5 vCPU
}

variable "openemr_task_memory" {
  description = "Memory in MiB for OpenEMR Fargate task"
  type        = number
  default     = 1024 # 1 GB
}

variable "agent_task_cpu" {
  description = "CPU units for Agent Fargate task. 1024 = 1 vCPU"
  type        = number
  default     = 256 # 0.25 vCPU
}

variable "agent_task_memory" {
  description = "Memory in MiB for Agent Fargate task"
  type        = number
  default     = 512 # 0.5 GB
}
