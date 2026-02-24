# -------------------------------------------------------
# Remote state backend
#
# Stores terraform.tfstate in S3 instead of on your laptop.
# DynamoDB provides a "lock" so two people can't run
# terraform apply simultaneously and corrupt the state.
#
# SETUP: Before adding this file, you must first create the
# S3 bucket and DynamoDB table by running:
#   cd infra/remote-state-bootstrap
#   terraform init && terraform apply
#
# Then come back here and run:
#   cd infra/
#   terraform init -migrate-state
# -------------------------------------------------------
terraform {
  backend "s3" {
    bucket         = "openemr-agent-tfstate"
    key            = "infra/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "openemr-agent-tflock"
  }
}
