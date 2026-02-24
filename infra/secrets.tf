# -------------------------------------------------------
# AWS Secrets Manager — encrypted storage for sensitive values
#
# ECS task definitions reference these secrets by ARN
# (Amazon Resource Name). At container startup, ECS fetches
# the secret value and injects it as an environment variable.
# The actual value never appears in task definitions, logs,
# or Terraform plan output.
#
# Each secret costs $0.40/month. Total: $1.60/month for 4.
# -------------------------------------------------------

resource "aws_secretsmanager_secret" "db_root_password" {
  name        = "${var.project_name}/db-root-password"
  description = "MariaDB root password for the RDS instance"
  tags        = { Name = "${var.project_name}-db-root-password" }
}

resource "aws_secretsmanager_secret_version" "db_root_password" {
  secret_id     = aws_secretsmanager_secret.db_root_password.id
  secret_string = var.db_root_password
}

resource "aws_secretsmanager_secret" "db_app_password" {
  name        = "${var.project_name}/db-app-password"
  description = "MariaDB application user password (used by OpenEMR)"
  tags        = { Name = "${var.project_name}-db-app-password" }
}

resource "aws_secretsmanager_secret_version" "db_app_password" {
  secret_id     = aws_secretsmanager_secret.db_app_password.id
  secret_string = var.db_app_password
}

resource "aws_secretsmanager_secret" "anthropic_api_key" {
  name        = "${var.project_name}/anthropic-api-key"
  description = "Anthropic API key for Claude (used by the AI agent)"
  tags        = { Name = "${var.project_name}-anthropic-api-key" }
}

resource "aws_secretsmanager_secret_version" "anthropic_api_key" {
  secret_id     = aws_secretsmanager_secret.anthropic_api_key.id
  secret_string = var.anthropic_api_key
}

resource "aws_secretsmanager_secret" "langchain_api_key" {
  name        = "${var.project_name}/langchain-api-key"
  description = "LangChain/LangSmith API key for observability tracing"
  tags        = { Name = "${var.project_name}-langchain-api-key" }
}

resource "aws_secretsmanager_secret_version" "langchain_api_key" {
  secret_id     = aws_secretsmanager_secret.langchain_api_key.id
  secret_string = var.langchain_api_key
}
