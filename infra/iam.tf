# -------------------------------------------------------
# IAM Role for the EC2 instance
#
# IAM roles let AWS resources (like an EC2 instance) perform
# actions without storing credentials on the machine.
# This role gives the EC2 instance permission to:
#   - Pull Docker images from ECR
# -------------------------------------------------------

# The "trust policy" — says "EC2 instances are allowed to assume this role"
resource "aws_iam_role" "ec2_role" {
  name = "${var.project_name}-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
  })

  tags = {
    Name = "${var.project_name}-ec2-role"
  }
}

# The "permissions policy" — says "this role can read from ECR"
resource "aws_iam_role_policy" "ecr_pull" {
  name = "${var.project_name}-ecr-pull"
  role = aws_iam_role.ec2_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchGetImage",
        "ecr:BatchCheckLayerAvailability",
        "ecr:GetAuthorizationToken"
      ]
      Resource = "*"
    }]
  })
}

# An "instance profile" is the bridge between an IAM role and an EC2 instance.
# You can't attach a role directly to EC2 — you wrap it in a profile first.
# (This is just an AWS quirk, don't worry about why.)
resource "aws_iam_instance_profile" "ec2_profile" {
  name = "${var.project_name}-ec2-profile"
  role = aws_iam_role.ec2_role.name
}

# -------------------------------------------------------
# IAM User for GitHub Actions
#
# This is a separate identity for the CI/CD pipeline.
# It only has permission to push Docker images to ECR.
# Its access keys get stored as GitHub Secrets.
# -------------------------------------------------------
resource "aws_iam_user" "github_actions" {
  name = "${var.project_name}-github-actions"

  tags = {
    Name = "${var.project_name}-github-actions"
  }
}

resource "aws_iam_user_policy" "github_actions_ecr" {
  name = "${var.project_name}-github-actions-ecr"
  user = aws_iam_user.github_actions.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        # ECR permissions (push/pull Docker images)
        Effect = "Allow"
        Action = [
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetAuthorizationToken",
          "ecr:PutImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload"
        ]
        Resource = "*"
      },
      {
        # ECS permissions for deployment
        # update-service triggers a new deployment;
        # describe-services is needed by "aws ecs wait services-stable"
        Effect = "Allow"
        Action = [
          "ecs:UpdateService",
          "ecs:DescribeServices"
        ]
        Resource = "*"
      }
    ]
  })
}

# Create access keys for GitHub Actions to use
resource "aws_iam_access_key" "github_actions" {
  user = aws_iam_user.github_actions.name
}
