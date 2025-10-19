output "resource_group_name" {
  value       = azurerm_resource_group.this.name
  description = "Name of the resource group hosting TraceFox."
}

output "ingress_fqdn" {
  value       = azurerm_container_app.this.latest_revision_fqdn
  description = "Public endpoint for the Container App."
}
