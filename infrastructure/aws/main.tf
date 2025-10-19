terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.region
}

locals {
  tags = merge(
    {
      Project     = "TraceFox"
      Environment = var.environment
    },
    var.additional_tags
  )
}

module "tracefox_service" {
  source = "../modules/container_service"

  name_prefix           = var.name_prefix
  environment           = var.environment
  image                 = var.image
  cpu                   = var.cpu
  memory                = var.memory
  desired_count         = var.desired_count
  subnet_ids            = var.subnet_ids
  security_group_ids    = var.security_group_ids
  tags                  = local.tags
}
