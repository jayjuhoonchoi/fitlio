terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = "ap-southeast-2"
}

# ─────────────────────────────────────────
# VPC
# ─────────────────────────────────────────
resource "aws_vpc" "fitlio_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "fitlio-vpc"
    Environment = "production"
    Project     = "fitlio"
    ManagedBy   = "terraform"
  }
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.fitlio_vpc.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "ap-southeast-2a"
  map_public_ip_on_launch = true

  tags = {
    Name    = "fitlio-public-subnet"
    Project = "fitlio"
  }
}

resource "aws_internet_gateway" "fitlio_igw" {
  vpc_id = aws_vpc.fitlio_vpc.id

  tags = {
    Name    = "fitlio-igw"
    Project = "fitlio"
  }
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.fitlio_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.fitlio_igw.id
  }

  tags = {
    Name    = "fitlio-public-rt"
    Project = "fitlio"
  }
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

# ─────────────────────────────────────────
# Security Group
# ─────────────────────────────────────────
resource "aws_security_group" "fitlio_sg" {
  name        = "fitlio-sg"
  description = "Security group for Fitlio EC2"
  vpc_id      = aws_vpc.fitlio_vpc.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "SSH access"
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP access"
  }

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS access"
  }

  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Fitlio API"
  }

  ingress {
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Grafana"
  }
  ingress {
    from_port   = 30030
    to_port     = 30030
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Grafana NodePort (k3s)"
  }
  ingress {
    from_port   = 30090
    to_port     = 30090
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Prometheus NodePort (k3s)"
  }

  ingress {
    from_port   = 9090
    to_port     = 9090
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Prometheus"
  }

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "PostgreSQL - Lambda access"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
    description = "All outbound"
  }

  tags = {
    Name    = "fitlio-sg"
    Project = "fitlio"
  }
}

# ─────────────────────────────────────────
# Key Pair
# ─────────────────────────────────────────
resource "aws_key_pair" "fitlio_key" {
  key_name   = "fitlio-key"
  public_key = file("~/.ssh/id_ed25519.pub")

  tags = {
    Project = "fitlio"
  }
}

# ─────────────────────────────────────────
# AMI
# ─────────────────────────────────────────
data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
}

# ─────────────────────────────────────────
# EC2
# ─────────────────────────────────────────
resource "aws_instance" "fitlio_server" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = "t2.small"
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.fitlio_sg.id]
  key_name               = aws_key_pair.fitlio_key.key_name

  root_block_device {
    volume_size = 20
    volume_type = "gp3"
  }

  user_data = <<-EOF
    #!/bin/bash
    set -e
    exec > /var/log/user-data.log 2>&1

    # ── 1. 필수 패키지 ────────────────────────────────────────
    apt-get update -y
    apt-get install -y git curl

    # ── 2. Swap 2GB (ArgoCD OOM 방지) ────────────────────────
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
    echo "✅ Swap 완료"

    # ── 3. fitlio 레포 클론 ───────────────────────────────────
    git clone https://github.com/jayjuhoonchoi/fitlio.git /home/ubuntu/fitlio
    chown -R ubuntu:ubuntu /home/ubuntu/fitlio
    echo "✅ Git clone 완료"

    # ── 4. k3s 설치 ───────────────────────────────────────────
    curl -sfL https://get.k3s.io | INSTALL_K3S_VERSION="v1.29.4+k3s1" sh -
    until kubectl get nodes 2>/dev/null | grep -q "Ready"; do
      echo "k3s 노드 준비 대기 중..."
      sleep 5
    done
    echo "✅ k3s Ready"

    # ── 5. kubeconfig 권한 ────────────────────────────────────
    chmod 644 /etc/rancher/k3s/k3s.yaml
    export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

    # ── 6. namespace 생성 ─────────────────────────────────────
    kubectl create namespace fitlio --dry-run=client -o yaml | kubectl apply -f -
    echo "✅ namespace 완료"

    # ── 8. K8s 매니페스트 적용 ───────────────────────────────
    kubectl apply -f /home/ubuntu/fitlio/k8s/
    echo "✅ K8s 매니페스트 적용 완료"

    # ── 9. cert-manager 설치 ─────────────────────────────────
    kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.16.3/cert-manager.yaml
    sleep 60
    kubectl apply -f /home/ubuntu/fitlio/k8s/cluster-issuer-prod.yaml
    echo "✅ 클러스터 부트스트랩 완료"
  EOF


  tags = {
    Name        = "fitlio-server"
    Environment = "production"
    Project     = "fitlio"
    ManagedBy   = "terraform"
  }
}

# ─────────────────────────────────────────
# Outputs
# ─────────────────────────────────────────
output "fitlio_public_ip" {
  value       = aws_instance.fitlio_server.public_ip
  description = "Public IP of Fitlio EC2 server"
}

output "fitlio_url" {
  value       = "https://fitlio-jay.duckdns.org"
  description = "Fitlio service URL"
}

output "grafana_url" {
  value       = "http://${aws_instance.fitlio_server.public_ip}:3000"
  description = "Grafana monitoring URL"
}

output "prometheus_url" {
  value       = "http://${aws_instance.fitlio_server.public_ip}:9090"
  description = "Prometheus metrics URL"
}