variable "region" {
  type        = string
  description = "AWS region to deploy into."
}

variable "environment" {
  type        = string
  description = "Deployment environment name."
  default     = "dev"
}

variable "name_prefix" {
  type        = string
  description = "Prefix applied to resource names."
  default     = "tracefox"
}

variable "image" {
  type        = string
  description = "Container image (including tag) hosted in ECR/registry."
}

variable "subnet_ids" {
  type        = list(string)
  description = "Subnets for the ECS service."
}

variable "security_group_ids" {
  type        = list(string)
  description = "Security groups attached to the ECS tasks."
}

variable "cpu" {
  type        = number
  description = "Fargate CPU units."
  default     = 512
}

variable "memory" {
  type        = number
  description = "Fargate memory in MB."
  default     = 1024
}

variable "desired_count" {
  type        = number
  description = "Number of tasks to run."
  default     = 1
}

variable "additional_tags" {
  type        = map(string)
  description = "Additional tags to add to provisioned resources."
  default     = {}
}
