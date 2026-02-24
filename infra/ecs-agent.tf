# -------------------------------------------------------
# Agent ECS Task Definition + Service
#
# Runs the custom AI agent image from ECR. The agent has
# two ports:
#   - FastAPI (8000): REST API for /health and /chat
#   - Streamlit (8501): Chat frontend UI
#
# The agent reaches OpenEMR through the ALB (replacing the
# Docker-internal "https://openemr:443" URL).
#
# Cost: ~$9/month (0.25 vCPU + 0.5 GB Fargate)
# -------------------------------------------------------

resource "aws_ecs_task_definition" "agent" {
  family                   = "${var.project_name}-agent"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.agent_task_cpu    # Default: 256 (0.25 vCPU)
  memory                   = var.agent_task_memory # Default: 512 (0.5 GB)
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  container_definitions = jsonencode([{
    name      = "agent"
    image     = "${aws_ecr_repository.agent.repository_url}:latest"
    essential = true

    portMappings = [
      { containerPort = 8000, protocol = "tcp" },
      { containerPort = 8501, protocol = "tcp" }
    ]

    # Non-sensitive environment variables
    environment = [
      # Point agent at OpenEMR via the ALB
      # (replaces "https://openemr:443" from Docker network)
      { name = "OPENEMR_BASE_URL", value = "http://${aws_lb.main.dns_name}" },
      { name = "OPENEMR_SSL_VERIFY", value = "false" },
      { name = "AGENT_BACKEND_URL", value = "http://localhost:8000" },
      { name = "LANGCHAIN_TRACING_V2", value = "true" },
    ]

    # Sensitive values from Secrets Manager
    secrets = [
      {
        name      = "ANTHROPIC_API_KEY"
        valueFrom = aws_secretsmanager_secret.anthropic_api_key.arn
      },
      {
        name      = "LANGCHAIN_API_KEY"
        valueFrom = aws_secretsmanager_secret.langchain_api_key.arn
      },
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.agent.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "agent"
      }
    }

    # Health check — uses the /health endpoint from app.py
    healthCheck = {
      command     = ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 60 # Agent boots faster than OpenEMR
    }
  }])

  tags = { Name = "${var.project_name}-agent-task" }
}

resource "aws_ecs_service" "agent" {
  name            = "${var.project_name}-agent"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.agent.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  enable_execute_command = true

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.agent.id]
    assign_public_ip = true
  }

  # Register with BOTH target groups (the agent serves two ports)
  load_balancer {
    target_group_arn = aws_lb_target_group.agent_api.arn
    container_name   = "agent"
    container_port   = 8000
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.agent_streamlit.arn
    container_name   = "agent"
    container_port   = 8501
  }

  depends_on = [aws_lb_listener.http]

  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 200

  tags = { Name = "${var.project_name}-agent-service" }
}
