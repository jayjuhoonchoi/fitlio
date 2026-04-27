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

# Lambda VPC 접근 권한 (VPC 안에 넣으려면 필요)
resource "aws_iam_role_policy_attachment" "lambda_vpc" {
  role       = aws_iam_role.lambda_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole"
}

# Lambda 전용 Security Group
resource "aws_security_group" "lambda_sg" {
  name        = "fitlio-lambda-sg"
  description = "Security group for Lambda"
  vpc_id      = aws_vpc.fitlio_vpc.id

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# psycopg2 Lambda Layer
resource "aws_lambda_layer_version" "psycopg2" {
  filename            = "${path.module}/../lambda/psycopg2-layer.zip"
  layer_name          = "psycopg2"
  compatible_runtimes = ["python3.11"]
}

# Lambda 함수 (VPC 안에 배치)
resource "aws_lambda_function" "membership_alert" {
  filename         = "${path.module}/../lambda/membership_alert.zip"
  function_name    = "fitlio-membership-alert"
  role             = aws_iam_role.lambda_role.arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.11"
  timeout          = 30
  layers           = [aws_lambda_layer_version.psycopg2.arn]

  vpc_config {
    subnet_ids         = [aws_subnet.public.id]
    security_group_ids = [aws_security_group.lambda_sg.id]
  }

  environment {
    variables = {
      DB_HOST           = aws_instance.fitlio_server.private_ip
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