# -------------------------------------------------------
# ECS Cluster + IAM Roles
#
# ECS (Elastic Container Service) is AWS's service for
# running Docker containers. A "cluster" is a logical
# grouping — think of it as a namespace for your services.
#
# With Fargate as the launch type, there are no servers to
# manage; you just tell AWS "run this container image with
# X CPU and Y memory" and it provisions compute automatically.
#
# This file creates the cluster and two IAM roles:
#   1. Execution Role — used by ECS itself (not your code)
#      to pull images, read secrets, and write startup logs
#   2. Task Role — used by your application code running
#      inside the container (e.g., ECS Exec for shell access)
# -------------------------------------------------------

resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-cluster"

  # Container Insights sends CPU/memory/network metrics to CloudWatch
  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = { Name = "${var.project_name}-cluster" }
}

# -------------------------------------------------------
# Execution Role — what ECS needs to START your containers
# (pull images from ECR, read secrets, write startup logs)
# -------------------------------------------------------
resource "aws_iam_role" "ecs_execution" {
  name = "${var.project_name}-ecs-execution-role"

  # "Trust policy" — says "the ECS service is allowed to use this role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })

  tags = { Name = "${var.project_name}-ecs-execution-role" }
}

# AWS provides a pre-built policy for ECS task execution.
# It covers: pull from ECR, write to CloudWatch Logs.
resource "aws_iam_role_policy_attachment" "ecs_execution_base" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Additional policy: allow reading our specific secrets from Secrets Manager
resource "aws_iam_role_policy" "ecs_execution_secrets" {
  name = "${var.project_name}-ecs-execution-secrets"
  role = aws_iam_role.ecs_execution.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["secretsmanager:GetSecretValue"]
      Resource = [
        aws_secretsmanager_secret.db_root_password.arn,
        aws_secretsmanager_secret.db_app_password.arn,
        aws_secretsmanager_secret.anthropic_api_key.arn,
        aws_secretsmanager_secret.langchain_api_key.arn,
      ]
    }]
  })
}

# -------------------------------------------------------
# Task Role — what YOUR CODE can do while running inside
# the container. The key permission here is ECS Exec,
# which lets you "SSH into" a running container via:
#   aws ecs execute-command --cluster ... --task ... --interactive --command /bin/bash
# -------------------------------------------------------
resource "aws_iam_role" "ecs_task" {
  name = "${var.project_name}-ecs-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })

  tags = { Name = "${var.project_name}-ecs-task-role" }
}

# ECS Exec uses SSM (Systems Manager) under the hood to establish
# a secure WebSocket connection to the container.
resource "aws_iam_role_policy" "ecs_exec" {
  name = "${var.project_name}-ecs-exec"
  role = aws_iam_role.ecs_task.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "ssmmessages:CreateControlChannel",
        "ssmmessages:CreateDataChannel",
        "ssmmessages:OpenControlChannel",
        "ssmmessages:OpenDataChannel"
      ]
      Resource = "*"
    }]
  })
}
