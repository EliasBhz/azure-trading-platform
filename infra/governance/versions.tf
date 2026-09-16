terraform {
  required_version = ">= 1.9.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
  }

  backend "azurerm" {
    resource_group_name  = "rg-tfstate-tradingbot-neu"
    storage_account_name = "sttfstatetrading4vqxmldp"
    container_name       = "tfstate"
    key                  = "governance.terraform.tfstate"
    use_azuread_auth     = true
  }
}

provider "azurerm" {
  subscription_id     = var.subscription_id
  storage_use_azuread = true
  features {}
}
