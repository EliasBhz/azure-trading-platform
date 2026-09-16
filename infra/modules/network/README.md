# network

Dedicated VNet with two delegated subnets, network security groups and the private DNS zone that makes the database reachable only from inside the VNet.

<!-- BEGIN_TF_DOCS -->
## Requirements

| Name | Version |
| ---- | ------- |
| <a name="requirement_terraform"></a> [terraform](#requirement\_terraform) | >= 1.9.0 |
| <a name="requirement_azurerm"></a> [azurerm](#requirement\_azurerm) | ~> 4.0 |

## Providers

| Name | Version |
| ---- | ------- |
| <a name="provider_azurerm"></a> [azurerm](#provider\_azurerm) | ~> 4.0 |

## Modules

No modules.

## Resources

| Name | Type |
| ---- | ---- |
| [azurerm_network_security_group.container_apps](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/network_security_group) | resource |
| [azurerm_network_security_group.postgres](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/network_security_group) | resource |
| [azurerm_private_dns_zone.postgres](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/private_dns_zone) | resource |
| [azurerm_private_dns_zone_virtual_network_link.postgres](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/private_dns_zone_virtual_network_link) | resource |
| [azurerm_subnet.container_apps](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/subnet) | resource |
| [azurerm_subnet.postgres](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/subnet) | resource |
| [azurerm_subnet_network_security_group_association.container_apps](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/subnet_network_security_group_association) | resource |
| [azurerm_subnet_network_security_group_association.postgres](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/subnet_network_security_group_association) | resource |
| [azurerm_virtual_network.this](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs/resources/virtual_network) | resource |

## Inputs

| Name | Description | Type | Default | Required |
| ---- | ----------- | ---- | ------- | :------: |
| <a name="input_address_space"></a> [address\_space](#input\_address\_space) | VNet address space. | `string` | `"10.40.0.0/16"` | no |
| <a name="input_container_apps_subnet_prefix"></a> [container\_apps\_subnet\_prefix](#input\_container\_apps\_subnet\_prefix) | Subnet for the Container Apps environment. Must be /23 or larger. | `string` | `"10.40.0.0/23"` | no |
| <a name="input_location"></a> [location](#input\_location) | Azure region. | `string` | n/a | yes |
| <a name="input_name_prefix"></a> [name\_prefix](#input\_name\_prefix) | Short prefix used in every resource name, for example tradingbot-dev. | `string` | n/a | yes |
| <a name="input_postgres_subnet_prefix"></a> [postgres\_subnet\_prefix](#input\_postgres\_subnet\_prefix) | Delegated subnet for PostgreSQL Flexible Server. | `string` | `"10.40.2.0/28"` | no |
| <a name="input_resource_group_name"></a> [resource\_group\_name](#input\_resource\_group\_name) | Resource group that holds the network resources. | `string` | n/a | yes |
| <a name="input_tags"></a> [tags](#input\_tags) | Tags applied to every resource. | `map(string)` | n/a | yes |

## Outputs

| Name | Description |
| ---- | ----------- |
| <a name="output_container_apps_subnet_id"></a> [container\_apps\_subnet\_id](#output\_container\_apps\_subnet\_id) | Subnet the Container Apps environment is injected into. |
| <a name="output_postgres_private_dns_zone_id"></a> [postgres\_private\_dns\_zone\_id](#output\_postgres\_private\_dns\_zone\_id) | Private DNS zone resolving the PostgreSQL FQDN inside the VNet. |
| <a name="output_postgres_private_dns_zone_link_id"></a> [postgres\_private\_dns\_zone\_link\_id](#output\_postgres\_private\_dns\_zone\_link\_id) | VNet link on the private DNS zone. Depend on this to order server creation after DNS is resolvable. |
| <a name="output_postgres_subnet_id"></a> [postgres\_subnet\_id](#output\_postgres\_subnet\_id) | Delegated subnet for PostgreSQL Flexible Server. |
| <a name="output_vnet_id"></a> [vnet\_id](#output\_vnet\_id) | Virtual network resource id. |
<!-- END_TF_DOCS -->
