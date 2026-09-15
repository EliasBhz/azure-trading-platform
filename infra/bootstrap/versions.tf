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
  }

  # No backend block. This stack creates the backend that every other stack
  # uses, so its own state is local. See README.md for why that is acceptable
  # here and how to recover if the local state is lost.
}

provider "azurerm" {
  subscription_id = var.subscription_id

  # Reach the blob data plane with the caller's Entra ID identity. The storage
  # account has shared keys disabled, so there is no account key to leak into a
  # developer machine, a CI variable or a state file.
  storage_use_azuread = true

  features {}
}
