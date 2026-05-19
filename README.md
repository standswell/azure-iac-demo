# azure-iac-demo

Standswell demonstration of Infrastructure As Code (IAC).

## Linux VM (Bicep)

Deploys a Ubuntu Linux VM with VNet, NSG, public IP, and SSH key login.

**Prerequisites:** [Azure CLI](https://learn.microsoft.com/cli/azure/install-azure-cli), logged in (`az login`), and an SSH public key.

1. Edit `infra/main.parameters.json` — set `sshPublicKey` to your public key (from `~/.ssh/id_rsa.pub` or `id_ed25519.pub`).
2. Create a resource group and deploy:

```powershell
az group create --name rg-iac-demo-dev --location australiaeast
az deployment group create `
  --resource-group rg-iac-demo-dev `
  --template-file infra/main.bicep `
  --parameters @infra/main.parameters.json
```

3. SSH using the `sshCommand` output from the deployment.

## Tests

Uses [uv](https://docs.astral.sh/uv/). Static checks need no Azure tools. Compile checks need [Bicep](https://aka.ms/bicep) or Azure CLI (`az bicep`).

```powershell
uv sync
uv run pytest -v
```
