# -------------------------------------------------------
# RDS MariaDB — managed database replacing Docker MariaDB
#
# RDS (Relational Database Service) is a managed database —
# AWS handles backups, patching, failover, and storage scaling.
# This replaces the "mariadb:11.8" Docker container from
# docker-compose.yml.
#
# Key difference from Docker MariaDB:
#   - Docker: runs on the same EC2 instance, data stored in a volume
#   - RDS: runs on a dedicated AWS-managed server, automatic backups
#
# Cost: ~$15/month for db.t3.micro + 20 GB gp3 storage
# -------------------------------------------------------

# A "subnet group" tells RDS which subnets to use.
# RDS requires at least 2 Availability Zones for failover support.
resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-db-subnet-group"
  subnet_ids = aws_subnet.private[*].id # Private subnets — NOT internet-accessible

  tags = { Name = "${var.project_name}-db-subnet-group" }
}

# Custom parameter group to match Docker MariaDB's --character-set-server=utf8mb4
resource "aws_db_parameter_group" "mariadb" {
  family = "mariadb11.4"
  name   = "${var.project_name}-mariadb-params"

  parameter {
    name  = "character_set_server"
    value = "utf8mb4"
  }

  parameter {
    name  = "collation_server"
    value = "utf8mb4_general_ci"
  }

  tags = { Name = "${var.project_name}-mariadb-params" }
}

resource "aws_db_instance" "main" {
  identifier = "${var.project_name}-db"

  # Engine: MariaDB 11.4 LTS
  # We use 11.4 (Long Term Support) for stability. The Docker Compose
  # uses 11.8, but OpenEMR is compatible with both. RDS offers 11.4
  # as the recommended LTS version.
  engine         = "mariadb"
  engine_version = "11.4"

  # Size: db.t3.micro = 2 vCPUs, 1 GB RAM (~$12/month)
  instance_class = var.db_instance_class

  # Storage: start at 20 GB, auto-grow up to 100 GB as needed
  allocated_storage     = 20
  max_allocated_storage = 100
  storage_type          = "gp3"
  storage_encrypted     = true

  # Credentials — root user password comes from Secrets Manager variable
  username = "root"
  password = var.db_root_password

  # Do NOT set db_name here. OpenEMR's auto-configure script runs
  # "CREATE DATABASE openemr" on first boot — if the DB already exists,
  # the script crashes with a fatal error. Let OpenEMR create it.

  # Networking — private subnets only (no internet exposure)
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.rds.id]
  publicly_accessible    = false

  # Character set matching Docker's --character-set-server=utf8mb4
  parameter_group_name = aws_db_parameter_group.mariadb.name

  # Maintenance and backup
  backup_retention_period    = 7                     # Keep 7 days of automated backups
  backup_window              = "03:00-04:00"         # Backup at 3 AM UTC
  maintenance_window         = "sun:04:00-sun:05:00" # Maintenance on Sunday 4 AM UTC
  auto_minor_version_upgrade = true

  # Dev settings — in production, set skip_final_snapshot = false
  # and deletion_protection = true
  skip_final_snapshot = true
  deletion_protection = false

  tags = { Name = "${var.project_name}-db" }
}
