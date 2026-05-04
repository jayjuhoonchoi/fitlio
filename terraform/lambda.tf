# Lambda 실행 권한 (IAM Role)
resource "aws_iam_role" "lambda_role" {
  name = "fitlio-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

# Lambda 기본 실행 권한
resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# psycopg2 Lambda Layer
resource "aws_lambda_layer_version" "psycopg2" {
  filename            = "${path.module}/../lambda/psycopg2-layer.zip"
  layer_name          = "psycopg2"
  compatible_runtimes = ["python3.11"]
}

# Lambda 함수 (VPC 밖 - Slack 인터넷 접근 가능)
resource "aws_lambda_function" "membership_alert" {
  filename         = "${path.module}/../lambda/membership_alert.zip"
  function_name    = "fitlio-membership-alert"
  role             = aws_iam_role.lambda_role.arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.11"
  timeout          = 30
  layers           = [aws_lambda_layer_version.psycopg2.arn]

  environment {
    variables = {
      DB_HOST           = aws_instance.fitlio_server.public_ip
      DB_NAME           = "fitlio"
      DB_USER           = "fitlio"
      DB_PASSWORD       = var.db_password
      SLACK_WEBHOOK_URL = var.slack_webhook_url
    }
  }
}

# EventBridge Rule (매일 오전 9시 KST = UTC 00:00)
resource "aws_cloudwatch_event_rule" "daily_9am" {
  name                = "fitlio-membership-alert-daily"
  schedule_expression = "cron(0 0 * * ? *)"
}

# EventBridge → Lambda 연결
resource "aws_cloudwatch_event_target" "lambda_target" {
  rule      = aws_cloudwatch_event_rule.daily_9am.name
  target_id = "fitlio-membership-alert"
  arn       = aws_lambda_function.membership_alert.arn
}

# EventBridge가 Lambda 실행할 수 있는 권한
resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.membership_alert.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_9am.arn
}

# ─────────────────────────────────────────
# S3 백업 버킷 (이미 생성됨 - import용)
# ─────────────────────────────────────────
resource "aws_s3_bucket" "db_backup" {
  bucket = "fitlio-db-backup-jay"
}

resource "aws_s3_bucket_versioning" "db_backup" {
  bucket = aws_s3_bucket.db_backup.id
  versioning_configuration {
    status = "Enabled"
  }
}

# ─────────────────────────────────────────
# Lambda S3 접근 권한
# ─────────────────────────────────────────
resource "aws_iam_role_policy" "lambda_s3_backup" {
  name = "fitlio-lambda-s3-backup"
  role = aws_iam_role.lambda_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["s3:PutObject", "s3:GetObject", "s3:ListBucket"]
      Resource = [
        aws_s3_bucket.db_backup.arn,
        "${aws_s3_bucket.db_backup.arn}/*"
      ]
    }]
  })
}

# ─────────────────────────────────────────
# Lambda 백업 함수
# ─────────────────────────────────────────
data "archive_file" "backup_lambda" {
  type        = "zip"
  source_file = "${path.module}/../lambda/backup/handler.py"
  output_path = "${path.module}/../lambda/backup/handler.zip"
}

resource "aws_lambda_function" "db_backup" {
  filename         = data.archive_file.backup_lambda.output_path
  function_name    = "fitlio-db-backup"
  role             = aws_iam_role.lambda_role.arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.11"
  timeout          = 300
  layers           = ["arn:aws:lambda:ap-southeast-2:238391222114:layer:psycopg2:9"]

  source_code_hash = data.archive_file.backup_lambda.output_base64sha256

  environment {
    variables = {
      DB_HOST     = aws_instance.fitlio_server.public_ip
      DB_NAME     = "fitlio"
      DB_USER     = "fitlio"
      DB_PASSWORD = "fitlio123"
      S3_BUCKET   = aws_s3_bucket.db_backup.bucket
    }
  }
}

# ─────────────────────────────────────────
# EventBridge - 매일 자정 UTC (한국 오전 9시)
# ─────────────────────────────────────────
resource "aws_cloudwatch_event_rule" "daily_backup" {
  name                = "fitlio-daily-backup"
  schedule_expression = "cron(0 0 * * ? *)"
}

resource "aws_cloudwatch_event_target" "backup_target" {
  rule      = aws_cloudwatch_event_rule.daily_backup.name
  target_id = "fitlio-db-backup"
  arn       = aws_lambda_function.db_backup.arn
}

resource "aws_lambda_permission" "allow_eventbridge_backup" {
  statement_id  = "AllowEventBridgeBackup"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.db_backup.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_backup.arn
}