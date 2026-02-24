# -------------------------------------------------------
# OpenEMR ECS Task Definition + Service
#
# This is the core of the migration — running OpenEMR as a
# Fargate service instead of a Docker container on EC2.
#
# An ECS service has two parts:
#   1. Task Definition: WHAT to run (image, CPU, memory,
#      env vars, ports, health check) — like a detailed
#      "docker run" command
#   2. Service: HOW to run it (how many copies, which network,
#      which load balancer, deployment strategy)
#
# Environment variables are replicated from docker-compose.yml
# lines 44-72, with adjustments for ECS/RDS.
#
# Cost: ~$18/month (0.5 vCPU + 1 GB Fargate)
# -------------------------------------------------------

resource "aws_ecs_task_definition" "openemr" {
  family                   = "${var.project_name}-openemr"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"                # Required for Fargate — each task gets its own network interface
  cpu                      = var.openemr_task_cpu    # Default: 512 (0.5 vCPU)
  memory                   = var.openemr_task_memory # Default: 1024 (1 GB)
  execution_role_arn       = aws_iam_role.ecs_execution.arn
  task_role_arn            = aws_iam_role.ecs_task.arn

  # EFS volume for persistent site configuration
  volume {
    name = "openemr-sites"
    efs_volume_configuration {
      file_system_id     = aws_efs_file_system.openemr.id
      transit_encryption = "ENABLED"
      authorization_config {
        access_point_id = aws_efs_access_point.openemr.id
        iam             = "ENABLED"
      }
    }
  }

  container_definitions = jsonencode([{
    name      = "openemr"
    image     = "openemr/openemr:7.0.4"
    essential = true

    portMappings = [
      { containerPort = 80, protocol = "tcp" },
      { containerPort = 443, protocol = "tcp" }
    ]

    # Mount EFS at the OpenEMR sites directory so setup state
    # (sqlconf.php) persists across task restarts
    mountPoints = [{
      sourceVolume  = "openemr-sites"
      containerPath = "/var/www/localhost/htdocs/openemr/sites"
      readOnly      = false
    }]

    # --- Non-sensitive environment variables ---
    # Replicated from docker-compose.yml lines 44-72
    environment = [
      # Database connection — MYSQL_HOST points to the RDS endpoint
      # (replaces "mysql" from Docker Compose's internal DNS)
      { name = "MYSQL_HOST", value = aws_db_instance.main.address },
      { name = "MYSQL_USER", value = "openemr" },
      { name = "MYSQL_ROOT_USER", value = "root" },

      # Default admin user for OpenEMR
      { name = "OE_USER", value = "admin" },
      { name = "OE_PASS", value = "pass" },

      # OpenEMR REST API and OAuth2 settings
      # site_addr_oath MUST match the URL the Agent uses to reach OpenEMR
      { name = "OPENEMR_SETTING_site_addr_oath", value = "http://${aws_lb.main.dns_name}" },
      { name = "OPENEMR_SETTING_oauth_password_grant", value = "3" },
      { name = "OPENEMR_SETTING_rest_system_scopes_api", value = "1" },
      { name = "OPENEMR_SETTING_rest_api", value = "1" },
      { name = "OPENEMR_SETTING_rest_fhir_api", value = "1" },
      { name = "OPENEMR_SETTING_rest_portal_api", value = "1" },
      { name = "OPENEMR_SETTING_portal_onsite_two_enable", value = "1" },
      { name = "OPENEMR_SETTING_ccda_alt_service_enable", value = "3" },
    ]

    # --- Sensitive values --- pulled from Secrets Manager at container startup
    secrets = [
      {
        name      = "MYSQL_ROOT_PASS"
        valueFrom = aws_secretsmanager_secret.db_root_password.arn
      },
      {
        name      = "MYSQL_PASS"
        valueFrom = aws_secretsmanager_secret.db_app_password.arn
      },
    ]

    # --- Logging --- stdout/stderr → CloudWatch
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.openemr.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "openemr"
      }
    }

    # Health check — matches production docker-compose.yml (3 min start period)
    healthCheck = {
      command     = ["CMD", "/usr/bin/curl", "--fail", "--insecure", "--silent", "https://localhost/interface/login/login.php"]
      interval    = 60
      timeout     = 5
      retries     = 3
      startPeriod = 180
    }
  }])

  tags = { Name = "${var.project_name}-openemr-task" }
}

resource "aws_ecs_service" "openemr" {
  name            = "${var.project_name}-openemr"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.openemr.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  # Enable ECS Exec — lets you run commands inside the container
  # (needed for importing synthetic patient data in Step 12)
  enable_execute_command = true

  # Tell ECS not to kill the task based on ALB health checks during startup.
  # OpenEMR first boot compiles themes + installs Composer deps (~10 min on 0.5 vCPU).
  health_check_grace_period_seconds = 300 # 5 min — production image boots in ~3 min

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.openemr.id]
    assign_public_ip = true # CRITICAL: without NAT Gateway, tasks need public IPs to pull images
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.openemr.arn
    container_name   = "openemr"
    container_port   = 443 # ALB connects to the container's HTTPS port
  }

  depends_on = [aws_lb_listener.http]

  # Deployment settings for a single-task service:
  # Allow 0 healthy during deploy (old task stops before new one starts)
  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 200

  tags = { Name = "${var.project_name}-openemr-service" }
}
