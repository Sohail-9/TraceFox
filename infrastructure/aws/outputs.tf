output "cluster_name" {
  value       = module.devguardian_service.cluster_name
  description = "Name of the ECS cluster hosting DevGuardian."
}

output "service_name" {
  value       = module.devguardian_service.service_name
  description = "Name of the ECS service."
}

