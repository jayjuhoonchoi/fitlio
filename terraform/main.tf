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

  user_data = <<-EOF
    #!/bin/bash
    set -e
    exec > /var/log/user-data.log 2>&1

    # ── 1. 기본 패키지 ──────────────────────────────
    apt-get update -y
    apt-get install -y docker.io docker-compose git curl certbot

    usermod -aG docker ubuntu

    # ── 2. 코드 clone ────────────────────────────────
    su - ubuntu -c "git clone https://github.com/jayjuhoonchoi/fitlio.git /home/ubuntu/fitlio"

    # ── 3. .env 생성 ─────────────────────────────────
    cat > /home/ubuntu/fitlio/.env << 'ENVEOF'
    POSTGRES_USER=fitlio
    POSTGRES_PASSWORD=fitlio123
    POSTGRES_DB=fitlio
    GRAFANA_PASSWORD=fitlio123
    ENVEOF

    # ── 4. DuckDNS IP 업데이트 ───────────────────────
    PUBLIC_IP=$(curl -s http://checkip.amazonaws.com)
    curl -s "https://www.duckdns.org/update?domains=fitlio-jay&token=${var.duckdns_token}&ip=$PUBLIC_IP"
    echo "DuckDNS updated: $PUBLIC_IP"

    # ── 5. DNS 전파 대기 ─────────────────────────────
    sleep 60

    # ── 6. nginx HTTP 임시 모드로 먼저 시작 ──────────
    mkdir -p /var/www/certbot
    cat > /home/ubuntu/fitlio/nginx/nginx.conf << 'NGINXEOF'
    server {
        listen 80;
        server_name fitlio-jay.duckdns.org;
        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }
        location / {
            return 200 'ok';
        }
    }
    NGINXEOF

    cd /home/ubuntu/fitlio
    docker-compose up -d nginx
    sleep 10

    # ── 7. certbot 인증서 발급 ───────────────────────
    certbot certonly --webroot \
      -w /var/www/certbot \
      -d fitlio-jay.duckdns.org \
      --email jayjuhoonchoi@gmail.com \
      --agree-tos \
      --non-interactive

    # ── 8. nginx HTTPS config 원복 ───────────────────
    cat > /home/ubuntu/fitlio/nginx/nginx.conf << 'NGINXEOF'
    server {
        listen 80;
        server_name fitlio-jay.duckdns.org;
        return 301 https://$host$request_uri;
    }
    server {
        listen 443 ssl;
        server_name fitlio-jay.duckdns.org;
        ssl_certificate /etc/letsencrypt/live/fitlio-jay.duckdns.org/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/fitlio-jay.duckdns.org/privkey.pem;
        location /auth/ {
            proxy_pass http://api:8000/auth/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            add_header Access-Control-Allow-Origin *;
        }
        location /classes {
            proxy_pass http://api:8000/classes;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            add_header Access-Control-Allow-Origin *;
        }
        location /payments/ {
            proxy_pass http://api:8000/payments/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            add_header Access-Control-Allow-Origin *;
        }
        location /check-in {
            proxy_pass http://api:8000/check-in;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            add_header Access-Control-Allow-Origin *;
        }
        location /attendances {
            proxy_pass http://api:8000/attendances;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            add_header Access-Control-Allow-Origin *;
        }
        location /admin/ {
            proxy_pass http://api:8000/admin/;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            add_header Access-Control-Allow-Origin *;
        }
        location /.well-known/acme-challenge/ {
            root /var/www/certbot;
        }
        location / {
            root /usr/share/nginx/html;
            index index.html;
            try_files $uri $uri.html $uri/ =404;
        }
    }
    NGINXEOF

    # ── 9. 전체 서비스 시작 ──────────────────────────
    docker-compose down
    docker-compose up -d --build

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