terraform {
  required_version = ">= 1.9.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }
}

resource "azurerm_virtual_network" "this" {
  name                = "vnet-${var.name_prefix}"
  resource_group_name = var.resource_group_name
  location            = var.location
  address_space       = [var.address_space]
  tags                = var.tags
}

# Container Apps in a Consumption-only environment requires a dedicated subnet
# of at least /23. The platform allocates addresses per replica, so a tighter
# range fails at environment creation rather than later.
resource "azurerm_subnet" "container_apps" {
  name                 = "snet-container-apps"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.this.name
  address_prefixes     = [var.container_apps_subnet_prefix]

  delegation {
    name = "container-apps"
    service_delegation {
      name    = "Microsoft.App/environments"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }
}

# PostgreSQL Flexible Server with private access is injected into this subnet.
# The delegation is what makes the server unreachable from the internet: there
# is no public endpoint to disable afterwards.
resource "azurerm_subnet" "postgres" {
  name                 = "snet-postgres"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.this.name
  address_prefixes     = [var.postgres_subnet_prefix]

  delegation {
    name = "postgres"
    service_delegation {
      name    = "Microsoft.DBforPostgreSQL/flexibleServers"
      actions = ["Microsoft.Network/virtualNetworks/subnets/join/action"]
    }
  }
}

resource "azurerm_network_security_group" "container_apps" {
  name                = "nsg-${var.name_prefix}-container-apps"
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.tags

  # No custom rules. The default rules already deny inbound from the internet
  # and allow outbound, which is what Container Apps needs: the platform pulls
  # images, reaches Azure Monitor and reaches the exchange API over egress.
  #
  # Restricting egress to a list of service tags is a real hardening step, but
  # it needs the full set documented and tested, and an incomplete list breaks
  # the environment in ways that surface as a stuck revision rather than a clear
  # error. Left for a hardening pass, deliberately and not by omission.
  # checkov:skip=CKV_AZURE_160:No inbound HTTP rule exists to restrict; the default DenyAllInBound applies.
}

resource "azurerm_network_security_group" "postgres" {
  name                = "nsg-${var.name_prefix}-postgres"
  resource_group_name = var.resource_group_name
  location            = var.location
  tags                = var.tags

  # The default AllowVnetInBound rule would let anything in the VNet reach the
  # database. These two rules narrow that to the Container Apps subnet on the
  # PostgreSQL port only: order matters, the allow must sit above the deny.
  security_rule {
    name                       = "AllowPostgresFromContainerApps"
    priority                   = 100
    direction                  = "Inbound"
    access                     = "Allow"
    protocol                   = "Tcp"
    source_port_range          = "*"
    destination_port_range     = "5432"
    source_address_prefix      = var.container_apps_subnet_prefix
    destination_address_prefix = var.postgres_subnet_prefix
  }

  security_rule {
    name                       = "DenyAllOtherVnetInbound"
    priority                   = 200
    direction                  = "Inbound"
    access                     = "Deny"
    protocol                   = "*"
    source_port_range          = "*"
    destination_port_range     = "*"
    source_address_prefix      = "VirtualNetwork"
    destination_address_prefix = "*"
  }
}

resource "azurerm_subnet_network_security_group_association" "container_apps" {
  subnet_id                 = azurerm_subnet.container_apps.id
  network_security_group_id = azurerm_network_security_group.container_apps.id
}

resource "azurerm_subnet_network_security_group_association" "postgres" {
  subnet_id                 = azurerm_subnet.postgres.id
  network_security_group_id = azurerm_network_security_group.postgres.id
}

# A private DNS zone is mandatory for a VNet-integrated Flexible Server: the
# server's FQDN resolves only inside a VNet linked to this zone, which is what
# makes "private access" mean something rather than being a firewall rule.
resource "azurerm_private_dns_zone" "postgres" {
  name                = "${var.name_prefix}.private.postgres.database.azure.com"
  resource_group_name = var.resource_group_name
  tags                = var.tags
}

resource "azurerm_private_dns_zone_virtual_network_link" "postgres" {
  name                  = "link-${var.name_prefix}-postgres"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.postgres.name
  virtual_network_id    = azurerm_virtual_network.this.id
  registration_enabled  = false
  tags                  = var.tags
}
