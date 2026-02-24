# -------------------------------------------------------
# Outputs
# These values are printed after "terraform apply" finishes.
# They give us the info we need to connect to and use
# the infrastructure.
# -------------------------------------------------------

output "instance_public_ip" {
  description = "The static public IP address of the EC2 instance"
  value       = aws_eip.main.public_ip
}

output "instance_public_dns" {
  description = "The public DNS name (the free domain name we discussed)"
  value       = aws_eip.main.public_dns
}

output "ecr_repository_url" {
  description = "The URL to push/pull Docker images"
  value       = aws_ecr_repository.agent.repository_url
}

output "ssh_command" {
  description = "Command to SSH into the instance"
  value       = "ssh -i infra/deploy_key ubuntu@${aws_eip.main.public_ip}"
}

# These are needed to configure GitHub Secrets for CI/CD.
# They'll print once after apply — copy them into your repo's secrets.
output "github_actions_access_key_id" {
  description = "AWS Access Key ID for GitHub Actions"
  value       = aws_iam_access_key.github_actions.id
}

output "github_actions_secret_access_key" {
  description = "AWS Secret Access Key for GitHub Actions"
  value       = aws_iam_access_key.github_actions.secret
  sensitive   = true
}
