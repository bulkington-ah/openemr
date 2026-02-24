# -------------------------------------------------------
# Security Groups — per-service firewalls
#
# Each service gets its own security group with ONLY the
# exact ports it needs. Traffic is restricted to come only
# from the services that should be talking to it. This is
# called the "principle of least privilege."
#
# For example, the RDS security group only allows port 3306
# from the OpenEMR security group — not from the internet,
# not from the Agent, not from anywhere else.
# -------------------------------------------------------

# --- ALB (Application Load Balancer) ---
# The ONLY thing that faces the public internet directly.
resource "aws_security_group" "alb" {
  name        = "${var.project_name}-alb-sg"
  description = "Allow HTTP from the internet to the ALB"
  vpc_id      = aws_vpc.main.id

  ingress {
    description = "HTTP from anywhere"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project_name}-alb-sg" }
}

# --- OpenEMR ECS Service ---
# Only accepts traffic from the ALB on ports 80 and 443.
resource "aws_security_group" "openemr" {
  name        = "${var.project_name}-openemr-sg"
  description = "Allow traffic from ALB to OpenEMR"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "HTTP from ALB"
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  ingress {
    description     = "HTTPS from ALB"
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    description = "Allow all outbound (pull images, reach RDS, etc.)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project_name}-openemr-sg" }
}

# --- Agent ECS Service ---
# Only accepts traffic from the ALB on ports 8000 (FastAPI) and 8501 (Streamlit).
resource "aws_security_group" "agent" {
  name        = "${var.project_name}-agent-sg"
  description = "Allow traffic from ALB to Agent"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "FastAPI from ALB"
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  ingress {
    description     = "Streamlit from ALB"
    from_port       = 8501
    to_port         = 8501
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    description = "Allow all outbound (reach OpenEMR via ALB, Anthropic API, etc.)"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project_name}-agent-sg" }
}

# --- RDS (Database) ---
# ONLY allows port 3306 (MariaDB) from the OpenEMR security group.
# The database is completely unreachable from the internet.
resource "aws_security_group" "rds" {
  name        = "${var.project_name}-rds-sg"
  description = "Allow MariaDB traffic from OpenEMR only"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "MariaDB from OpenEMR tasks"
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [aws_security_group.openemr.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project_name}-rds-sg" }
}
