variable "name_prefix" {
  type        = string
  description = "Prefix for all resource names."
}

variable "environment" {
  type        = string
  description = "Deployment environment name."
}

variable "image" {
  type        = string
  description = "Container image (including tag) to deploy."
}

variable "cpu" {
  type        = number
  description = "Fargate task CPU units."
  default     = 512
}

variable "memory" {
  type        = number
  description = "Fargate task memory (MB)."
  default     = 1024
}

variable "desired_count" {
  type        = number
  description = "Desired task count for the ECS service."
  default     = 1
}

variable "subnet_ids" {
  type        = list(string)
  description = "Subnets used by the ECS Service."
}

variable "security_group_ids" {
  type        = list(string)
  description = "Security groups applied to the ECS tasks."
}

variable "tags" {
  type        = map(string)
  description = "Tags applied to all resources."
  default     = {}
}

variable "krutrim_model" {
  type        = string
  description = "Base Krutrim model to use in the container."
  default     = "Krutrim-DeepSeek-R1"
}

variable "krutrim_api_base_url" {
  type        = string
  description = "Base URL for the Krutrim API."
  default     = "https://api.krutrim.com/v1"
}

variable "deepseek_router_model" {
  type        = string
  description = "Router model name used when escalating workloads."
  default     = "deepseek-r1"
}

resource "aws_ecs_cluster" "this" {
  name = "${var.name_prefix}-${var.environment}"
  tags = var.tags
}

resource "aws_cloudwatch_log_group" "this" {
  name              = "/devguardian/${var.environment}"
  retention_in_days = 14
  tags              = var.tags
}

data "aws_iam_policy_document" "task_assume_role" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "task_execution" {
  name               = "${var.name_prefix}-${var.environment}-execution"
  assume_role_policy = data.aws_iam_policy_document.task_assume_role.json
  tags               = var.tags
}

resource "aws_iam_role_policy_attachment" "task_execution" {
  role       = aws_iam_role.task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role" "task" {
  name               = "${var.name_prefix}-${var.environment}-task"
  assume_role_policy = data.aws_iam_policy_document.task_assume_role.json
  tags               = var.tags
}

resource "aws_ecs_task_definition" "this" {
  family                   = "${var.name_prefix}-${var.environment}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = tostring(var.cpu)
  memory                   = tostring(var.memory)
  execution_role_arn       = aws_iam_role.task_execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([
    {
      name      = "devguardian"
      image     = var.image
      essential = true
      portMappings = [
        {
          containerPort = 8000
          hostPort      = 8000
          protocol      = "tcp"
        }
      ]
      environment = [
        {
          name  = "KRUTRIM_MODEL"
          value = var.krutrim_model
        },
        {
          name  = "KRUTRIM_API_BASE_URL"
          value = var.krutrim_api_base_url
        },
        {
          name  = "DEEPSEEK_ROUTER_MODEL"
          value = var.deepseek_router_model
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.this.name
          awslogs-region        = data.aws_region.current.name
          awslogs-stream-prefix = "service"
        }
      }
    }
  ])

  runtime_platform {
    operating_system_family = "LINUX"
    cpu_architecture        = "X86_64"
  }

  tags = var.tags
}

data "aws_region" "current" {}

resource "aws_ecs_service" "this" {
  name            = "${var.name_prefix}-${var.environment}"
  cluster         = aws_ecs_cluster.this.id
  task_definition = aws_ecs_task_definition.this.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.subnet_ids
    security_groups  = var.security_group_ids
    assign_public_ip = true
  }

  tags = var.tags
}

output "cluster_name" {
  value       = aws_ecs_cluster.this.name
  description = "Name of the ECS cluster."
}

output "service_name" {
  value       = aws_ecs_service.this.name
  description = "Name of the ECS service."
}

