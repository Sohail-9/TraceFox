output "cluster_name" {
  value       = module.tracefox_service.cluster_name
  description = "Name of the ECS cluster hosting TraceFox."
}

output "service_name" {
  value       = module.tracefox_service.service_name
  description = "Name of the ECS service."
}
