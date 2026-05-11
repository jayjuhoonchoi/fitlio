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
# EC2 IAM (S3 access for sealed-secrets key backup)
# ─────────────────────────────────────────
resource "aws_iam_role" "fitlio_ec2_role" {
  name = "fitlio-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "fitlio_ec2_s3_policy" {
  name = "fitlio-ec2-s3-policy"
  role = aws_iam_role.fitlio_ec2_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["s3:GetObject", "s3:PutObject", "s3:ListBucket"]
      Resource = [
        "arn:aws:s3:::fitlio-db-backup-jay",
        "arn:aws:s3:::fitlio-db-backup-jay/*"
      ]
    }]
  })
}

resource "aws_iam_instance_profile" "fitlio_ec2_profile" {
  name = "fitlio-ec2-instance-profile"
  role = aws_iam_role.fitlio_ec2_role.name
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
  iam_instance_profile   = aws_iam_instance_profile.fitlio_ec2_profile.name

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
    apt-get install -y git curl unzip
    # awscli (S3에 sealed-secrets 키 백업/복구용)
    curl -sS "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "/tmp/awscliv2.zip"
    unzip -q /tmp/awscliv2.zip -d /tmp
    /tmp/aws/install
    echo "✅ awscli 설치 완료"

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

    # ── 7. Sealed Secrets 컨트롤러 설치 (CRD 먼저) ─────────────
    kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.27.1/controller.yaml
    kubectl -n kube-system rollout status deploy/sealed-secrets-controller --timeout=180s
    echo "✅ Sealed Secrets 컨트롤러 설치 완료"

    # ── 7.1 Sealed Secrets 키 백업/복구 (S3) ───────────────────
    # 목표: EC2를 재생성해도 같은 키로 SealedSecret 복호화되게 고정
    KEY_BUCKET="fitlio-db-backup-jay"
    KEY_OBJECT="sealed-secrets/kube-system-sealed-secrets-key.yaml"
    export AWS_REGION="ap-southeast-2"

    if aws s3api head-object --bucket "$KEY_BUCKET" --key "$KEY_OBJECT" >/dev/null 2>&1; then
      echo "✅ S3에서 sealed-secrets 키 백업 발견 → 복구"
      aws s3 cp "s3://$KEY_BUCKET/$KEY_OBJECT" /tmp/sealed-secrets-key.yaml
      # 기존 자동생성 키 제거 후 복구 적용
      kubectl -n kube-system delete secret -l sealedsecrets.bitnami.com/sealed-secrets-key --ignore-not-found=true
      kubectl apply -f /tmp/sealed-secrets-key.yaml
      kubectl -n kube-system rollout restart deploy/sealed-secrets-controller
      kubectl -n kube-system rollout status deploy/sealed-secrets-controller --timeout=180s
      echo "✅ sealed-secrets 키 복구 완료"
    else
      echo "⚠️ S3 키 백업 없음 → 현재 키를 백업"
      kubectl -n kube-system get secret -l sealedsecrets.bitnami.com/sealed-secrets-key -o yaml > /tmp/sealed-secrets-key.yaml
      aws s3 cp /tmp/sealed-secrets-key.yaml "s3://$KEY_BUCKET/$KEY_OBJECT"
      echo "✅ sealed-secrets 키 백업 완료"
    fi

    # ── 8. cert-manager 설치 (CRD 먼저) ───────────────────────
    kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.16.3/cert-manager.yaml
    kubectl -n cert-manager rollout status deploy/cert-manager --timeout=300s
    kubectl -n cert-manager rollout status deploy/cert-manager-webhook --timeout=300s
    kubectl -n cert-manager rollout status deploy/cert-manager-cainjector --timeout=300s
    echo "✅ cert-manager 설치 완료"

    # ── 9. SealedSecret / ClusterIssuer 등 CRD 의존 리소스 적용 ──
    # NOTE: ArgoCD Application CRD는 여기서 설치하지 않으므로 argocd-app.yaml은 적용하지 않음
    kubectl apply -f /home/ubuntu/fitlio/k8s/sealed-secret.yaml
    kubectl apply -f /home/ubuntu/fitlio/k8s/cluster-issuer-prod.yaml
    echo "✅ CRD 의존 리소스 적용 완료"

    # ── 10. Fitlio 앱 리소스 적용 (CRD 의존 없음) ─────────────
    kubectl apply -f /home/ubuntu/fitlio/k8s/postgres.yaml
    kubectl apply -f /home/ubuntu/fitlio/k8s/api.yaml
    kubectl apply -f /home/ubuntu/fitlio/k8s/ingress.yaml
    echo "✅ Fitlio 리소스 적용 완료"

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