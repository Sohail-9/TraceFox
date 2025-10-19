variable "location" {
  type        = string
  description = "Azure region for deployment."
}

variable "environment" {
  type        = string
  description = "Deployment environment name."
  default     = "dev"
}

variable "name_prefix" {
  type        = string
  description = "Prefix applied to resource names."
  default     = "devguardian"
}

variable "image" {
  type        = string
  description = "Container image to deploy."
}

variable "cpu" {
  type        = number
  description = "CPU cores allocated to the container."
  default     = 0.5
}

variable "memory_gb" {
  type        = number
  description = "Memory (GB) allocated to the container."
  default     = 1.0
}

variable "min_replicas" {
  type        = number
  description = "Minimum replicas for the container app."
  default     = 1
}

variable "max_replicas" {
  type        = number
  description = "Maximum replicas for the container app."
  default     = 3
}

variable "krutrim_model" {
  type        = string
  description = "Base Krutrim model to use."
  default     = "Krutrim-DeepSeek-R1"
}

variable "krutrim_api_base_url" {
  type        = string
  description = "Base URL for the Krutrim API."
  default     = "https://api.krutrim.com/v1"
}

variable "deepseek_router_model" {
  type        = string
  description = "Router model name."
  default     = "deepseek-r1"
}

variable "additional_tags" {
  type        = map(string)
  description = "Extra tags applied to resources."
  default     = {}
}

