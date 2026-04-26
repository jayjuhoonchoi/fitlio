# 🏋️ Fitlio — Sports Facility Management SaaS

## 🌍 Overview
Fitlio is a production-grade SaaS platform built for a real gym in Gwanghwamun, Seoul.
Members book classes, track memberships, and check in by phone number.
Owners get a live dashboard with attendance stats and membership status.

## 🛠️ Tech Stack
🐍 Backend: FastAPI + PostgreSQL  
🐳 Container: Docker + Docker Compose  
🏗️ IaC: Terraform  
☁️ Cloud: AWS EC2 (t3.micro, ap-southeast-2)  
🌐 Web Server: Nginx + Let's Encrypt  
⚙️ CI/CD: GitHub Actions  
📊 Monitoring: Prometheus + Grafana + Node Exporter  
🔔 Notification: Slack Webhook  
🔒 Security: Trivy (0 vulnerabilities)  

## 🏗️ Architecture
👨‍💻 Developer pushes code → 🤖 GitHub Actions tests → 🚀 Deploys to AWS EC2  
🌐 Nginx handles HTTPS → ⚡ FastAPI serves API → 🗄️ PostgreSQL stores data  
📡 Prometheus scrapes metrics → 📊 Grafana visualizes dashboards  
💬 Slack receives deployment notifications  

## 💪 Key Features
🔐 HTTPS with Let's Encrypt SSL  
🔄 Automated SSL renewal (certbot + pre/post hooks)  
🚀 Automated CI/CD pipeline (test → deploy → notify)  
📊 Real-time monitoring dashboard  
🏗️ Infrastructure as Code (Terraform)  
🤫 Zero hardcoded secrets (.env + GitHub Secrets)  
🛡️ Security scanning (Trivy — 0 CRITICAL, 0 HIGH)  
🏃 Membership & class booking system  
📱 Attendance check-in by phone number  
👑 Admin dashboard (stats + members + check-ins)  
🌏 International phone number support (20 countries)  
🇰🇷🇦🇺 Korean/English language switch  

## 🌐 Live Demo
https://fitlio-jay.duckdns.org

## 🔄 SSL Auto-Renewal
Certificates issued by Let's Encrypt (valid 90 days).  
Certbot systemd timer runs twice daily and renews before expiry.  
Pre-hook stops Nginx → certbot renews → post-hook restarts Nginx.  
Zero manual intervention required.  

## ⚙️ CI/CD Pipeline
Push to main → GitHub Actions triggered  
Trivy security scan → Docker build → Deploy to EC2  
Slack notification on success/failure  

## 📊 Monitoring
Prometheus: http://fitlio-jay.duckdns.org:9090  
Grafana: http://fitlio-jay.duckdns.org:3000  

## 🔒 Security
Secrets managed via .env (gitignored) + GitHub Secrets  
Trivy vulnerability scan: 0 CRITICAL, 0 HIGH, 0 MEDIUM  
IAM: Least privilege principle (no root access)  
HTTPS enforced — all traffic encrypted  

## 🚀 Local Development
git clone git@github.com:jayjuhoonchoi/fitlio.git  
cd fitlio  
cp .env.example .env  
docker compose up