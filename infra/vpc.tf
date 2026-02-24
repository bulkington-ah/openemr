# -------------------------------------------------------
# VPC (Virtual Private Cloud) — our own isolated network
#
# A VPC is like your own private data center within AWS,
# with its own IP address range. We create separate zones:
#   - Public subnets: connected to the internet (for ALB + Fargate)
#   - Private subnets: no internet access (for RDS database)
#
# AWS requires that RDS and ALB span at least 2 Availability
# Zones (AZs). An AZ is a physically separate data center
# within a region (e.g., us-east-1a and us-east-1b).
# -------------------------------------------------------

# Look up which Availability Zones are available in our region
data "aws_availability_zones" "available" {
  state = "available"
}

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16" # 65,536 IP addresses
  enable_dns_support   = true          # Let AWS resolve DNS names inside the VPC
  enable_dns_hostnames = true          # Let resources get DNS hostnames (RDS needs this)

  tags = { Name = "${var.project_name}-vpc" }
}

# -------------------------------------------------------
# Public subnets — internet-accessible
# Used by: ALB, ECS Fargate tasks (OpenEMR + Agent)
#
# map_public_ip_on_launch = true is KEY: it gives Fargate
# tasks public IPs so they can pull Docker images from the
# internet without needing a NAT Gateway (~$32/month savings).
# -------------------------------------------------------
resource "aws_subnet" "public" {
  count                   = 2
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(aws_vpc.main.cidr_block, 8, count.index) # 10.0.0.0/24, 10.0.1.0/24
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true

  tags = { Name = "${var.project_name}-public-${count.index}" }
}

# -------------------------------------------------------
# Private subnets — NOT internet-accessible
# Used by: RDS only (database should never face the internet)
# -------------------------------------------------------
resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(aws_vpc.main.cidr_block, 8, count.index + 10) # 10.0.10.0/24, 10.0.11.0/24
  availability_zone = data.aws_availability_zones.available.names[count.index]

  tags = { Name = "${var.project_name}-private-${count.index}" }
}

# -------------------------------------------------------
# Internet Gateway — the "front door" to the internet
# Without this, nothing in the VPC can reach the outside world.
# -------------------------------------------------------
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = { Name = "${var.project_name}-igw" }
}

# -------------------------------------------------------
# Route table for public subnets
#
# A route table is a set of rules: "traffic going to X
# should be sent through Y." This one says:
#   "Anything going to 0.0.0.0/0 (the internet) → IGW"
# -------------------------------------------------------
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = { Name = "${var.project_name}-public-rt" }
}

# Associate the public route table with each public subnet
resource "aws_route_table_association" "public" {
  count          = 2
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}

# Private subnets intentionally have NO route to the internet.
# They use the VPC's implicit "local" route to talk to other
# resources inside the VPC (e.g., Fargate tasks can reach RDS).
