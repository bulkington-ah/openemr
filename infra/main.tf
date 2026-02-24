# -------------------------------------------------------
# Look up the latest Ubuntu 24.04 LTS AMI (machine image)
# An AMI is a template for the server's operating system.
# Canonical (the company behind Ubuntu) publishes official
# AMIs under owner ID 099720109477.
# -------------------------------------------------------
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"] # Canonical

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

# -------------------------------------------------------
# SSH Key Pair
# This creates a key pair in AWS using a public key you
# generate locally. The private key stays on your machine
# (and will be added as a GitHub Actions secret for deploys).
# -------------------------------------------------------
resource "aws_key_pair" "deploy_key" {
  key_name   = "${var.project_name}-deploy-key"
  public_key = file("${path.module}/deploy_key.pub")
}

# -------------------------------------------------------
# Security Group (firewall rules)
# Controls what network traffic can reach the EC2 instance.
# -------------------------------------------------------
resource "aws_security_group" "main" {
  name        = "${var.project_name}-sg"
  description = "Allow HTTP, HTTPS, and SSH traffic"

  # Allow HTTP (port 80) from anywhere
  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Allow HTTPS (port 443) from anywhere
  ingress {
    description = "HTTPS"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Allow SSH (port 22) from anywhere
  # In production you'd restrict this to specific IPs,
  # but for dev this is fine.
  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Allow the agent service port (8000) from anywhere
  ingress {
    description = "Agent service"
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # OpenEMR HTTP (docker-compose maps container port 80 → host port 8300)
  ingress {
    description = "OpenEMR HTTP"
    from_port   = 8300
    to_port     = 8300
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # OpenEMR HTTPS (docker-compose maps container port 443 → host port 9300)
  ingress {
    description = "OpenEMR HTTPS"
    from_port   = 9300
    to_port     = 9300
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # phpMyAdmin (docker-compose maps container port 80 → host port 8310)
  ingress {
    description = "phpMyAdmin"
    from_port   = 8310
    to_port     = 8310
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Allow ALL outbound traffic (the server can reach the internet)
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-sg"
  }
}

# -------------------------------------------------------
# EC2 Instance
# The actual server that runs our docker-compose stack.
# -------------------------------------------------------
resource "aws_instance" "main" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = var.instance_type
  key_name               = aws_key_pair.deploy_key.key_name
  vpc_security_group_ids = [aws_security_group.main.id]
  iam_instance_profile   = aws_iam_instance_profile.ec2_profile.name

  # 30 GB disk — OpenEMR + Docker images + MariaDB data need some room
  root_block_device {
    volume_size = 30
    volume_type = "gp3"
  }

  # user_data runs once when the instance first boots.
  # When it changes, Terraform will destroy and recreate the instance.
  user_data_replace_on_change = true

  user_data = <<-EOF
#!/bin/bash
set -ex

# Install Docker, Docker Compose, and git from Ubuntu's repos
apt-get update
apt-get install -y docker.io docker-compose-v2 git unzip

# Start Docker and enable it on boot
systemctl enable docker
systemctl start docker

# Add the default user to the docker group
usermod -aG docker ubuntu

# Install AWS CLI v2 (not in Ubuntu's default repos — use AWS's official installer)
curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o /tmp/awscliv2.zip
unzip -q /tmp/awscliv2.zip -d /tmp
/tmp/aws/install
rm -rf /tmp/awscliv2.zip /tmp/aws

# Log into ECR so we can pull our agent image
aws ecr get-login-password --region ${var.aws_region} \
  | docker login --username AWS --password-stdin ${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com
  EOF

  tags = {
    Name = "${var.project_name}-dev"
  }
}

# We need the account ID for the ECR login URL in user_data above
data "aws_caller_identity" "current" {}

# -------------------------------------------------------
# Elastic IP
# A static public IP address that stays the same even if
# the EC2 instance is stopped and restarted.
# -------------------------------------------------------
resource "aws_eip" "main" {
  instance = aws_instance.main.id

  tags = {
    Name = "${var.project_name}-eip"
  }
}
