output "ec2_public_ip" {
  description = "Elastic IP for Fitlio EC2"
  value       = aws_eip.fitlio_eip.public_ip
}

output "ssh_example" {
  description = "SSH command"
  value       = "ssh -i ~/.ssh/id_ed25519 ubuntu@${aws_eip.fitlio_eip.public_ip}"
}