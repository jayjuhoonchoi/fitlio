output "ec2_public_ip" {
  description = "EC2 public IP address"
  value       = aws_instance.fitlio_server.public_ip
}