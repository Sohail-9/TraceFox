terraform {
  required_version = ">= 1.6.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.90"
    }
  }
}

provider "azurerm" {
  features {}
}

resource "azurerm_resource_group" "this" {
  name     = "${var.name_prefix}-${var.environment}-rg"
  location = var.location
  tags = merge(
    {
      Project     = "DevGuardian"
      Environment = var.environment
    },
    var.additional_tags
  )
}

resource "azurerm_log_analytics_workspace" "this" {
  name                = "${var.name_prefix}-${var.environment}-law"
  location            = azurerm_resource_group.this.location
  resource_group_name = azurerm_resource_group.this.name
  sku                 = "PerGB2018"
  retention_in_days   = 30
  tags                = azurerm_resource_group.this.tags
}

resource "azurerm_container_app_environment" "this" {
  name                       = "${var.name_prefix}-${var.environment}-cae"
  location                   = azurerm_resource_group.this.location
  resource_group_name        = azurerm_resource_group.this.name
  log_analytics_workspace_id = azurerm_log_analytics_workspace.this.id
  tags                       = azurerm_resource_group.this.tags
}

resource "azurerm_container_app" "this" {
  name                         = "${var.name_prefix}-${var.environment}-app"
  container_app_environment_id = azurerm_container_app_environment.this.id
  resource_group_name          = azurerm_resource_group.this.name
  revision_mode                = "Single"

  ingress {
    external_enabled = true
    target_port      = 8000
    transport        = "auto"
  }

  template {
    container {
      name   = "devguardian"
      image  = var.image
      cpu    = var.cpu
      memory = "${var.memory_gb}Gi"

      env {
        name  = "KRUTRIM_MODEL"
        value = var.krutrim_model
      }

      env {
        name  = "KRUTRIM_API_BASE_URL"
        value = var.krutrim_api_base_url
      }

      env {
        name  = "DEEPSEEK_ROUTER_MODEL"
        value = var.deepseek_router_model
      }
    }

    scale {
      min_replicas = var.min_replicas
      max_replicas = var.max_replicas
    }
  }

  tags = azurerm_resource_group.this.tags
}

