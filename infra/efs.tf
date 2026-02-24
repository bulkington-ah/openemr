# -------------------------------------------------------
# EFS (Elastic File System) — persistent storage for OpenEMR
#
# WHY THIS IS NEEDED:
# Fargate containers have ephemeral storage — when a task
# restarts (deploy, health check failure, scaling event),
# all local files are lost. OpenEMR stores a critical "setup
# lock" file at:
#   /var/www/localhost/htdocs/openemr/sites/default/sqlconf.php
#
# Without persistent storage:
#   1. First boot: OpenEMR creates DB schema, writes lock file ✓
#   2. Task restarts: lock file is gone, OpenEMR tries first-boot
#      setup AGAIN against an already-populated database ✗
#
# EFS is a network file system that persists across restarts.
# We mount it at the OpenEMR sites directory so the lock file
# (and all site config) survives task restarts.
#
# Cost: ~$0.30/GB/month (the sites directory is tiny, <1 GB)
# -------------------------------------------------------

resource "aws_efs_file_system" "openemr" {
  creation_token = "${var.project_name}-openemr-efs"
  encrypted      = true

  tags = { Name = "${var.project_name}-openemr-efs" }
}

# Mount targets — one per subnet so Fargate tasks in either
# AZ can access the filesystem
resource "aws_efs_mount_target" "openemr" {
  count           = 2
  file_system_id  = aws_efs_file_system.openemr.id
  subnet_id       = aws_subnet.public[count.index].id
  security_groups = [aws_security_group.efs.id]
}

# Access point — controls the POSIX user/group and root path
# for the mount. uid/gid 0 = root, because OpenEMR's container
# process runs as root.
resource "aws_efs_access_point" "openemr" {
  file_system_id = aws_efs_file_system.openemr.id

  posix_user {
    uid = 0
    gid = 0
  }

  root_directory {
    path = "/openemr-sites"
    creation_info {
      owner_uid   = 0
      owner_gid   = 0
      permissions = "755"
    }
  }

  tags = { Name = "${var.project_name}-openemr-efs-ap" }
}

# EFS security group: allow NFS (port 2049) from OpenEMR tasks only
resource "aws_security_group" "efs" {
  name        = "${var.project_name}-efs-sg"
  description = "Allow NFS from OpenEMR Fargate tasks"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "NFS from OpenEMR"
    from_port       = 2049
    to_port         = 2049
    protocol        = "tcp"
    security_groups = [aws_security_group.openemr.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${var.project_name}-efs-sg" }
}
