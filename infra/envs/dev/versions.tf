terraform {
  required_version = ">= 1.9.0"

  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 4.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
    time = {
      source  = "hashicorp/time"
      version = "~> 0.12"
    }
    azuread = {
      source  = "hashicorp/azuread"
      version = "~> 3.0"
    }
    azapi = {
      source  = "Azure/azapi"
      version = "~> 2.0"
    }
  }

  # Created by infra/bootstrap. No access key: authentication is Entra ID, so
  # there is no credential in this file and none in any environment variable.
  backend "azurerm" {
    resource_group_name  = "rg-tfstate-tradingbot-neu"
    storage_account_name = "sttfstatetrading4vqxmldp"
    container_name       = "tfstate"
    key                  = "dev.terraform.tfstate"
    use_azuread_auth     = true
  }
}

provider "azuread" {}

provider "azapi" {}

provider "azurerm" {
  subscription_id = var.subscription_id

  # Reach the blob and queue data planes with the caller's Entra ID identity.
  # Without this the provider reads storage properties with a shared key, which
  # fails outright on an account that has key based authentication disabled.
  storage_use_azuread = true

  features {
    key_vault {
      # Do not recover a soft-deleted vault silently. Purge protection is off so
      # the environment can be rebuilt, and a recovered vault would bring back
      # secrets that the destroy was meant to remove.
      recover_soft_deleted_key_vaults = false
      purge_soft_delete_on_destroy    = true
    }

    resource_group {
      # Refuse to delete a resource group that still contains resources
      # Terraform does not know about. The alternative silently destroys
      # anything a human created inside it.
      prevent_deletion_if_contains_resources = true
    }
  }
}
