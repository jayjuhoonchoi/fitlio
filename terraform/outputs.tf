output "ec2_public_ip" {
  description = "Stable public IPv4 (Elastic IP) for the Fitlio EC2 instance"
  value       = aws_eip.fitlio_eip.public_ip
}

output "ssh_example" {
  description = "Example SSH command (adjust -i to your private key path)"
  value       = "ssh -i ~/.ssh/id_ed25519 ubuntu@${aws_eip.fitlio_eip.public_ip}"
}