# -------------------------------------------------------
# One-time bootstrap: creates the S3 bucket and DynamoDB
# lock table for storing Terraform state remotely.
#
# This is run separately from the main infra/ config:
#   cd infra/remote-state-bootstrap
#   terraform init && terraform apply
#
# WHY: Terraform state is a JSON file that tracks every
# resource Terraform has created. By default it lives on
# your laptop. Moving it to S3 makes it durable (won't be
# lost if your laptop dies) and shareable. DynamoDB adds
# locking so two people can't run "terraform apply" at the
# same time and corrupt the state.
# -------------------------------------------------------

provider "aws" {
  region = "us-east-1"
}

resource "aws_s3_bucket" "tfstate" {
  bucket = "openemr-agent-tfstate"

  # Safety net: Terraform will refuse to delete this bucket.
  # You'd have to remove this line first, which forces you to think twice.
  lifecycle {
    prevent_destroy = true
  }

  tags = { Name = "openemr-agent-tfstate" }
}

# Keep old versions of the state file so you can recover from mistakes
resource "aws_s3_bucket_versioning" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  versioning_configuration {
    status = "Enabled"
  }
}

# Encrypt the state file at rest (it contains sensitive data like passwords)
resource "aws_s3_bucket_server_side_encryption_configuration" "tfstate" {
  bucket = aws_s3_bucket.tfstate.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# DynamoDB table used as a "lock" — when someone runs terraform apply,
# a lock is written here. If someone else tries to apply at the same time,
# Terraform sees the lock and refuses. PAY_PER_REQUEST means zero cost
# when idle (locks are acquired/released in milliseconds).
resource "aws_dynamodb_table" "tflock" {
  name         = "openemr-agent-tflock"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "LockID"

  attribute {
    name = "LockID"
    type = "S" # "S" = String
  }

  tags = { Name = "openemr-agent-tflock" }
}
