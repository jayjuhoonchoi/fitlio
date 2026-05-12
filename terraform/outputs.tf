output "ec2_public_ip" {
  description = "Stable public IPv4 (Elastic IP) for the Fitlio EC2 instance"
  value       = aws_eip.fitlio_eip.public_ip
}