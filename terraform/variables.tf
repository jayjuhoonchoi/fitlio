variable "db_host" {
  description = "EC2 private IP or RDS endpoint"
  type        = string
  default     = "10.0.1.17"
}

variable "db_password" {
  description = "PostgreSQL password"
  type        = string
  sensitive   = true
  default     = "fitlio123"
}

variable "slack_webhook_url" {
  description = "Slack Webhook URL"
  type        = string
  sensitive   = true
}