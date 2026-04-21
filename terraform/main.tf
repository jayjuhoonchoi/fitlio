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

resource "aws_vpc" "fitlio_vpc" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name        = "fitlio-vpc"
    Environment = "production"
    Project     = "fitlio"
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
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS access"
  }

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP access"
  }

  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Fitlio API"
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

resource "aws_key_pair" "fitlio_key" {
  key_name   = "fitlio-key"
  public_key = file("~/.ssh/id_ed25519.pub")

  tags = {
    Project = "fitlio"
  }
}

data "aws_ami" "ubuntu" {
  most_recent = true
  owners      = ["099720109477"]

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-server-*"]
  }
}

resource "aws_instance" "fitlio_server" {
  ami                    = data.aws_ami.ubuntu.id
  instance_type          = "t3.micro"
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.fitlio_sg.id]
  key_name               = aws_key_pair.fitlio_key.key_name

  tags = {
    Name        = "fitlio-server"
    Environment = "production"
    Project     = "fitlio"
  }
}

output "fitlio_public_ip" {
  value       = aws_instance.fitlio_server.public_ip
  description = "Public IP of Fitlio server"
}