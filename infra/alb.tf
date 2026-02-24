# -------------------------------------------------------
# ALB (Application Load Balancer) — single HTTP entry point
#
# Replaces the multi-port setup (8300, 9300, 8000, 8501)
# with a single port 80 entry point that routes based on
# URL path:
#   /          → OpenEMR (default)
#   /agent/*   → Agent FastAPI (port 8000)
#   /chat/*    → Agent Streamlit (port 8501)
#   /_stcore/* → Streamlit internal assets/WebSocket
#
# ALB concepts:
#   Listener: "Listen on port 80 for incoming HTTP requests"
#   Target Group: "A pool of containers that handle a request type"
#   Listener Rule: "If URL matches X, send to target group Y"
#
# Cost: ~$17/month (ALB hourly + light traffic)
# -------------------------------------------------------

resource "aws_lb" "main" {
  name               = "${var.project_name}-alb"
  internal           = false # Internet-facing
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id # Must be in at least 2 AZs

  tags = { Name = "${var.project_name}-alb" }
}

# -------------------------------------------------------
# Target Groups — pools of containers
# -------------------------------------------------------

# OpenEMR target group
# The openemr/openemr:flex container serves HTTPS on port 443 internally
# (self-signed cert). The ALB connects to the container via HTTPS.
resource "aws_lb_target_group" "openemr" {
  name        = "${var.project_name}-oe-tg"
  port        = 443
  protocol    = "HTTPS"
  vpc_id      = aws_vpc.main.id
  target_type = "ip" # Required for Fargate (not "instance")

  health_check {
    enabled             = true
    path                = "/interface/login/login.php"
    port                = "443"
    protocol            = "HTTPS"
    healthy_threshold   = 2
    unhealthy_threshold = 5
    timeout             = 10
    interval            = 30
    matcher             = "200,302"
  }

  # Slow start: give OpenEMR 180 seconds to finish booting before
  # sending full traffic. Matches docker-compose.yml start_period: 3m.
  slow_start = 180

  tags = { Name = "${var.project_name}-oe-tg" }
}

# Agent FastAPI target group (port 8000)
resource "aws_lb_target_group" "agent_api" {
  name        = "${var.project_name}-api-tg"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    path                = "/health" # Exists in app.py
    port                = "8000"
    protocol            = "HTTP"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 15
    matcher             = "200"
  }

  tags = { Name = "${var.project_name}-api-tg" }
}

# Agent Streamlit target group (port 8501)
resource "aws_lb_target_group" "agent_streamlit" {
  name        = "${var.project_name}-st-tg"
  port        = 8501
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    path                = "/_stcore/health" # Streamlit's built-in health endpoint
    port                = "8501"
    protocol            = "HTTP"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    timeout             = 5
    interval            = 15
    matcher             = "200"
  }

  tags = { Name = "${var.project_name}-st-tg" }
}

# -------------------------------------------------------
# Listener — "listen on port 80"
# Default action: send everything to OpenEMR (the main app)
# -------------------------------------------------------
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.openemr.arn
  }
}

# -------------------------------------------------------
# Listener Rules — path-based routing to Agent services
# -------------------------------------------------------

# /agent and /agent/* → FastAPI on port 8000
resource "aws_lb_listener_rule" "agent_api" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 10

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.agent_api.arn
  }

  condition {
    path_pattern {
      values = ["/agent", "/agent/*"]
    }
  }
}

# /chat and /chat/* → Streamlit on port 8501
resource "aws_lb_listener_rule" "agent_streamlit" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 20

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.agent_streamlit.arn
  }

  condition {
    path_pattern {
      values = ["/chat", "/chat/*"]
    }
  }
}

# Streamlit's internal static assets and WebSocket connections.
# Without this rule, the chat UI would load but not be interactive.
resource "aws_lb_listener_rule" "streamlit_internal" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 25

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.agent_streamlit.arn
  }

  condition {
    path_pattern {
      values = ["/_stcore/*", "/static/*", "/component/*"]
    }
  }
}
