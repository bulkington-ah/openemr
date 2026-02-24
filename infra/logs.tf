# -------------------------------------------------------
# CloudWatch Log Groups — centralized logging for Fargate
#
# When containers run on Fargate, there's no server to SSH
# into and run "docker logs". CloudWatch Logs collects each
# container's stdout/stderr so you can search, filter, and
# monitor them in the AWS Console.
#
# Each service gets its own log group so logs don't mix.
# Retention is 30 days — after that, logs are auto-deleted
# to control storage costs.
#
# View logs with:
#   aws logs tail /ecs/openemr-agent/openemr --follow
#   aws logs tail /ecs/openemr-agent/agent --follow
# -------------------------------------------------------

resource "aws_cloudwatch_log_group" "openemr" {
  name              = "/ecs/${var.project_name}/openemr"
  retention_in_days = 30

  tags = { Name = "${var.project_name}-openemr-logs" }
}

resource "aws_cloudwatch_log_group" "agent" {
  name              = "/ecs/${var.project_name}/agent"
  retention_in_days = 30

  tags = { Name = "${var.project_name}-agent-logs" }
}
