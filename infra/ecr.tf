# -------------------------------------------------------
# ECR Repository
# ECR (Elastic Container Registry) is AWS's Docker image storage.
# When GitHub Actions builds the agent Docker image, it pushes
# it here. The EC2 instance pulls from here to run it.
# -------------------------------------------------------
resource "aws_ecr_repository" "agent" {
  name = var.project_name

  # Automatically delete old images when new ones are pushed
  image_tag_mutability = "MUTABLE"

  # Scan images for known security vulnerabilities
  image_scanning_configuration {
    scan_on_push = true
  }

  tags = {
    Name = "${var.project_name}-ecr"
  }
}

# -------------------------------------------------------
# Lifecycle policy — keep only the last 10 images
# Without this, old images pile up and cost storage money.
# -------------------------------------------------------
resource "aws_ecr_lifecycle_policy" "agent" {
  repository = aws_ecr_repository.agent.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep only the last 10 images"
      selection = {
        tagStatus   = "any"
        countType   = "imageCountMoreThan"
        countNumber = 10
      }
      action = {
        type = "expire"
      }
    }]
  })
}
