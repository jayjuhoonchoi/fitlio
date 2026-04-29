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
🔔 Notification: Slack Webhook + Block Kit  
🔒 Security: Trivy (0 vulnerabilities)  
☁️ Serverless: AWS Lambda + EventBridge  

## 🏗️ Architecture
👨‍💻 Developer pushes code → 🤖 GitHub Actions tests → 🚀 Deploys to AWS EC2  
🌐 Nginx handles HTTPS → ⚡ FastAPI serves API → 🗄️ PostgreSQL stores data  
📡 Prometheus scrapes metrics → 📊 Grafana visualizes dashboards  
💬 Slack receives deployment notifications  
⏰ EventBridge triggers Lambda daily → 🔍 Scans expiring memberships → 📲 Slack alert  

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
🤖 Serverless membership expiry alerts (Lambda + EventBridge)  
🌱 Automated DB seeding with startup report