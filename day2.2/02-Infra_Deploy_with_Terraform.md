# Session 2: Build Azure Pipeline for Infrastructure Deployment with Terraform

## What You'll Build Today (2 minutes)
**End Result**: A complete CI/CD pipeline using Azure DevOps that automatically deploys infrastructure with Terraform templates, uses managed variable groups for secure configuration, and deploys the same Order Service from Session 1 through Infrastructure as Code (IaC).

---

## Understanding Terraform (3 minutes)
**Terraform** is an open-source Infrastructure as Code (IaC) tool that allows you to define and provision infrastructure using a declarative configuration language called HashiCorp Configuration Language (HCL). Terraform supports multiple cloud providers and enables consistent workflows across different platforms.

## Hands-On Block (58 minutes)
### Step 1: Create Terraform Infrastructure Templates (15 minutes)

**Create project structure:**
```bash
mkdir -p deployments/{terraform,pipelines}
cd deployments
```

Your-workspace=repo-from-[session-01](01-Manual-Deploy.md)
```
Your-workspace
├─ your-repo-other-content
└─ deployments/
   ├── terraform/
   │    ├─ main.tf
   │    ├─ variables.tf
   │    ├─ outputs.tf
   │    └─ terraform.tfvars
   └── pipelines/
        ├─ infrastructure.yml
        └─ variables.yml
```

**Create Terraform Variables (`terraform/variables.tf`):**

Change `your-unique-name` to a unique name for your resources, such as your student name or initials.


```hcl
variable "student_name" {
  description = "Student name for resource naming"
  type        = string
  default     = "your-unique-name"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "location" {
  description = "Azure region for all resources"
  type        = string
  default     = "East US"
}

variable "app_service_plan_sku" {
  description = "App Service Plan SKU"
  type        = string
  default     = "B3"
}

variable "eventhub_sku" {
  description = "Event Hub Namespace SKU"
  type        = string
  default     = "Standard"
}

variable "resource_group_name" {
  description = "Name of the resource group"
  type        = string
}
```

**Create Main Terraform Configuration (`terraform/main.tf`):**

Change `your-unique-name` to a unique name for your resources, such as your student name or initials.

```hcl
terraform {
  required_version = ">= 1.0"
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~>3.0"
    }
  }
}

provider "azurerm" {
  features {}
}

# Data source for existing resource group
data "azurerm_resource_group" "main" {
  name = var.resource_group_name
}

# Local values for resource naming
locals {
  app_service_plan_name    = "${var.student_name}-plan"
  web_app_name            = "${var.student_name}-order-service"
  eventhub_namespace_name = "${var.student_name}-events"
  eventhub_name           = "orders"
  common_tags = {
    Environment = var.environment
    Student     = var.student_name
    Project     = "order-service"
    ManagedBy   = "terraform"
  }
}

# App Service Plan
resource "azurerm_service_plan" "main" {
  name                = local.app_service_plan_name
  resource_group_name = data.azurerm_resource_group.main.name
  location            = data.azurerm_resource_group.main.location
  os_type             = "Linux"
  sku_name            = var.app_service_plan_sku

  tags = local.common_tags
}

# Event Hub Namespace
resource "azurerm_eventhub_namespace" "main" {
  name                = local.eventhub_namespace_name
  location            = data.azurerm_resource_group.main.location
  resource_group_name = data.azurerm_resource_group.main.name
  sku                 = var.eventhub_sku
  capacity            = 1

  tags = local.common_tags
}

# Event Hub
resource "azurerm_eventhub" "orders" {
  name                = local.eventhub_name
  namespace_name      = azurerm_eventhub_namespace.main.name
  resource_group_name = data.azurerm_resource_group.main.name
  partition_count     = 1
  message_retention   = 1
}

# Event Hub Authorization Rule
resource "azurerm_eventhub_authorization_rule" "orders_access" {
  name                = "orders-access-key"
  namespace_name      = azurerm_eventhub_namespace.main.name
  eventhub_name       = azurerm_eventhub.orders.name
  resource_group_name = data.azurerm_resource_group.main.name

  listen = true
  send   = true
  manage = false
}

# Linux Web App
resource "azurerm_linux_web_app" "main" {
  name                = local.web_app_name
  resource_group_name = data.azurerm_resource_group.main.name
  location            = data.azurerm_resource_group.main.location
  service_plan_id     = azurerm_service_plan.main.id
  https_only          = true

  site_config {
    always_on                         = true
    application_stack {
      python_version = "3.9"
    }
    app_command_line = "uvicorn main:app --host 0.0.0.0 --port 8000"
  }

  app_settings = {
    "EVENT_HUB_CONNECTION_STRING" = azurerm_eventhub_authorization_rule.orders_access.primary_connection_string
    "EVENT_HUB_NAME"              = azurerm_eventhub.orders.name
    "ENVIRONMENT"                 = var.environment
    "SCM_DO_BUILD_DURING_DEPLOYMENT" = "true"
  }

  tags = local.common_tags

  depends_on = [
    azurerm_service_plan.main,
    azurerm_eventhub_authorization_rule.orders_access
  ]
}
```

**Create Terraform Outputs (`terraform/outputs.tf`):**
```hcl
output "web_app_name" {
  description = "Name of the created web app"
  value       = azurerm_linux_web_app.main.name
}

output "web_app_url" {
  description = "URL of the web app"
  value       = "https://${azurerm_linux_web_app.main.default_hostname}"
}

output "web_app_default_hostname" {
  description = "Default hostname of the web app"
  value       = azurerm_linux_web_app.main.default_hostname
}

output "eventhub_namespace_name" {
  description = "Name of the Event Hub namespace"
  value       = azurerm_eventhub_namespace.main.name
}

output "eventhub_name" {
  description = "Name of the Event Hub"
  value       = azurerm_eventhub.orders.name
}

output "app_service_plan_name" {
  description = "Name of the App Service Plan"
  value       = azurerm_service_plan.main.name
}

output "resource_group_name" {
  description = "Name of the resource group"
  value       = data.azurerm_resource_group.main.name
}
```

**Create Terraform Variables File (`terraform/terraform.tfvars`):**
```hcl
# Change 'your-unique-name' to your actual unique identifier
student_name         = "your-unique-name"
environment          = "production"
location             = "East US"
app_service_plan_sku = "B3"
eventhub_sku         = "Standard"
# This will be provided via pipeline variable
# resource_group_name = "your-resource-group-name"
```

### Step 2: Setup Azure DevOps Variable Groups (10 minutes)

**In Azure DevOps Portal:**
1. Go to your Azure DevOps project
2. Navigate to **Pipelines** → **Library**
3. Click **+ Variable group**
4. Create variable group named: `az-sandbox`
5. Allow access to the variable group for your pipeline

**Add these variables:**
```yaml
# Service Principal Variables (mark as secret)
CLIENT_ID: <your-service-principal-id>
CLIENT_SECRET: <your-service-principal-secret>  # Mark as Secret
TENANT_ID: <your-tenant-id>
SUBSCRIPTION_ID: <your-subscription-id>

# Resource Group
RG: <your-resource-group-name>
```

**To get Service Principal credentials:**
```bash
Ask instructor
```

### Step 3: Create Azure DevOps Pipeline Files (15 minutes)

**Create Pipeline Variables (`pipelines/variables.yml`):**
```yaml
variables:
- group: az-sandbox
```

**Create Infrastructure Pipeline (`pipelines/infrastructure.yml`):**
```yaml
trigger:
  branches:
    include:
      - main

pool:
  name: 'self-hosted-linux-agents' # this is the name of the pool where the pipeline will run
  demands:
    - agent.name -equals first-agent # this is the name of the agent where the pipeline will run

variables:
- template: variables.yml

stages:
- stage: CheckoutAndAuthenticate
  displayName: 'Checkout and Authenticate'
  jobs:
  - job: Authenticate
    displayName: 'Setup and Authenticate'
    steps:
    - checkout: self
      displayName: 'Checkout my code'
    
    - script: |
        terraform version
        az --version
      displayName: 'Validate Terraform and Azure CLI installation'

    - script: |
        echo "Setting up Azure CLI..."
        az login --service-principal -u $ARM_CLIENT_ID -p $ARM_CLIENT_SECRET --tenant $ARM_TENANT_ID
        az account set --subscription $ARM_SUBSCRIPTION_ID
        az account show
      displayName: 'Azure CLI Setup - Authenticate to Azure'
      # This is recommended way to reference secret variables in Azure DevOps Pipelines
      # You can't map secret variables globally by any means, so you need to pass them to each step that needs them
      env:
        ARM_CLIENT_ID: $(CLIENT_ID)
        ARM_CLIENT_SECRET: $(CLIENT_SECRET)
        ARM_TENANT_ID: $(TENANT_ID)
        ARM_SUBSCRIPTION_ID: $(SUBSCRIPTION_ID)

- stage: TerraformPlan
  displayName: 'Terraform Plan'
  dependsOn: CheckoutAndAuthenticate
  jobs:
  - job: TerraformPlan
    displayName: 'Terraform Plan'
    steps:
    - checkout: self
      displayName: 'Checkout Repository'
      
    - script: |
        cd deployments/terraform
        echo "Initializing Terraform..."
        terraform init
      displayName: 'Terraform Init'
      # This is recommended way to reference secret variables in Azure DevOps Pipelines
      # You can't map secret variables globally by any means, so you need to pass them to each step that needs them
      env:
        ARM_CLIENT_ID: $(CLIENT_ID)
        ARM_CLIENT_SECRET: $(CLIENT_SECRET)
        ARM_TENANT_ID: $(TENANT_ID)
        ARM_SUBSCRIPTION_ID: $(SUBSCRIPTION_ID)

    - script: |
        cd deployments/terraform
        echo "Validating Terraform configuration..."
        terraform validate
      displayName: 'Terraform Validate'

    - script: |
        cd deployments/terraform
        echo "Formatting Terraform files..."
        terraform fmt -check
      displayName: 'Terraform Format Check'
      continueOnError: true

    - script: |
        cd deployments/terraform
        echo "Creating Terraform execution plan..."
        terraform plan \
          -var="resource_group_name=$TF_RG" \
          -out=tfplan \
          -detailed-exitcode
      displayName: 'Terraform Plan'
      # This is recommended way to reference secret variables in Azure DevOps Pipelines
      # You can't map secret variables globally by any means, so you need to pass them to each step that needs them
      env:
        TF_RG: $(RG)
        ARM_CLIENT_ID: $(CLIENT_ID)
        ARM_CLIENT_SECRET: $(CLIENT_SECRET)
        ARM_TENANT_ID: $(TENANT_ID)
        ARM_SUBSCRIPTION_ID: $(SUBSCRIPTION_ID)

    - task: PublishPipelineArtifact@1
      inputs:
        targetPath: 'deployments/terraform/tfplan'
        artifact: 'terraform-plan'
        publishLocation: 'pipeline'
      displayName: 'Publish Terraform Plan'

- stage: TerraformApply
  displayName: 'Terraform Apply'
  dependsOn: TerraformPlan
  jobs:
  - deployment: TerraformApply
    displayName: 'Terraform Apply'
    environment: 'production'
    strategy:
      runOnce:
        deploy:
          steps:
          - checkout: self
            displayName: 'Checkout my code'

          - task: DownloadPipelineArtifact@2
            inputs:
              buildType: 'current'
              artifactName: 'terraform-plan'
              targetPath: 'deployments/terraform/'
            displayName: 'Download Terraform Plan'

          - script: |
              cd deployments/terraform
              echo "Re-initializing Terraform..."
              terraform init
            displayName: 'Terraform Re-Init'
            env:
              ARM_CLIENT_ID: $(CLIENT_ID)
              ARM_CLIENT_SECRET: $(CLIENT_SECRET)
              ARM_TENANT_ID: $(TENANT_ID)
              ARM_SUBSCRIPTION_ID: $(SUBSCRIPTION_ID)

          - script: |
              cd deployments/terraform
              echo "Applying Terraform plan..."
              terraform apply tfplan
            displayName: 'Terraform Apply'
            env:
              ARM_CLIENT_ID: $(CLIENT_ID)
              ARM_CLIENT_SECRET: $(CLIENT_SECRET)
              ARM_TENANT_ID: $(TENANT_ID)
              ARM_SUBSCRIPTION_ID: $(SUBSCRIPTION_ID)

          - script: |
              cd deployments/terraform
              echo "✅ Infrastructure deployed successfully!"
              
              echo "Terraform Outputs:"
              terraform output
              
              echo "Verifying Azure resources..."
              az resource list \
                --resource-group $TF_RG \
                --query "[].{Name:name, Type:type, Location:location}" \
                --output table
            displayName: 'Show Deployment Results'
            # This is recommended way to reference secret variables in Azure DevOps Pipelines
            # You can't map secret variables globally by any means, so you need to pass them to each step that needs them
            env:
              TF_RG: $(RG)
```

**Draw-backs of this approach ⚠️**:
- State management is local to the pipeline agent (terraform.tfstate file)
- No remote state storage, which can lead to issues in team environments
- No locking mechanism, which can cause concurrent modifications 

### Step 4: Run the Pipeline and Deploy (10 minutes)

**Create and Run Pipeline:**
0. Commit and push your changes to the repository
1. In Azure DevOps, go to **Pipelines** → **Pipelines**
2. Click **New pipeline**
3. Select **Azure Repos Git** (or your repository type)
4. Select your repository
5. Choose **Existing Azure Pipelines YAML file**
6. Select `/deployments/pipelines/infrastructure.yml`
7. Click **Continue** → **Run**

**Monitor the Pipeline:**
- Watch the authentication stage complete
- Monitor the Terraform plan generation
- Review the planned changes
- Monitor the deployment progress
- Check the deployment results and outputs

**Verify Deployment:**
```bash
# In Azure Cloud Shell or local Azure CLI
az resource list \
  --resource-group <your-rg> \
  --query "[].{Name:name, Type:type, Status:properties.provisioningState}" \
  --output table

# Check Terraform outputs
cd deployments/terraform
terraform output
```

---

## What You Built Today:

✅ **Infrastructure as Code (IaC)** - Complete Terraform templates for Azure resources  
✅ **CI/CD Pipeline** - Automated deployment using Azure DevOps  
✅ **Secure Configuration** - Variable groups and service principal authentication  
✅ **Template Validation** - Terraform validation and planning before deployment  
✅ **Parameter Management** - Separate variable files for different environments  
✅ **Deployment Outputs** - Structured outputs for integration  
✅ **Complete Automation** - From code commit to live infrastructure  

## Terraform Benefits You Implemented:

| Feature | Benefit | Implementation |
|---------|---------|----------------|
| **Declarative** | Define desired state, not steps | HCL resource definitions |
| **Idempotent** | Run multiple times safely | Terraform state management |
| **Multi-Cloud** | Works across cloud providers | Provider-agnostic syntax |
| **Plan Preview** | See changes before applying | `terraform plan` command |
| **State Management** | Track resource state | Terraform state file |
| **Modular** | Reusable infrastructure components | Terraform modules support |

## Pipeline Stages Breakdown:

### 🔍 **Authentication Stage**
- **Tool Validation**: Checks Terraform and Azure CLI installation
- **Azure Authentication**: Sets up service principal authentication
- **Environment Setup**: Configures Azure subscription context

### 📋 **Terraform Plan Stage**
- **Terraform Init**: Initializes working directory and downloads providers
- **Template Validation**: Validates Terraform configuration syntax
- **Format Check**: Ensures consistent code formatting
- **Plan Generation**: Creates execution plan showing proposed changes
- **Artifact Publishing**: Saves plan for deployment stage

### 🚀 **Terraform Apply Stage**
- **Environment Deployment**: Uses Azure DevOps environments for approvals
- **Plan Download**: Retrieves the approved execution plan
- **Resource Provisioning**: Applies changes to create/update infrastructure
- **Output Display**: Shows Terraform outputs and resource verification

### 📊 **Verification Stage**
- **Output Review**: Displays all Terraform outputs
- **Resource Listing**: Shows all created Azure resources
- **Status Verification**: Confirms successful resource provisioning

## Infrastructure Architecture You Deployed:

```
Azure Resource Group
├── App Service Plan (B3 SKU)
│   ├── Linux-based hosting
│   └── Auto-scaling capabilities
├── Event Hub Namespace
│   ├── Standard SKU
│   ├── Event Hub: "orders"
│   └── Authorization Rules with Listen/Send rights
└── Linux Web App (Python 3.9)
    ├── Auto-configured with Event Hub connection
    ├── Environment variables automatically set
    ├── HTTPS enforced
    └── Resource tags for management
```

## Terraform Structure You Built:

### 📂 **File Organization**:
- **`main.tf`** - Primary resource definitions
- **`variables.tf`** - Input variable declarations
- **`outputs.tf`** - Output value definitions
- **`terraform.tfvars`** - Variable value assignments

### 🔧 **Key Terraform Concepts Used**:
- **Resources** - Infrastructure components to create
- **Data Sources** - Reference existing infrastructure
- **Variables** - Parameterized configurations
- **Locals** - Computed values and expressions
- **Outputs** - Values to return after deployment
- **Dependencies** - Resource creation ordering

## Session Recap:

### Key Takeaways:
1. **Infrastructure as Code** - Automated, repeatable infrastructure deployment
2. **Terraform Advantages** - Multi-cloud support and plan preview capabilities
3. **CI/CD Integration** - Plan-and-apply workflow with Azure DevOps
4. **Security Best Practices** - Service principal authentication and variable groups
5. **Environment Management** - Parameterized templates for multiple environments
6. **DevOps Workflow** - Complete automation with approval gates

### Terraform vs Other IaC Tools:

| Feature | Terraform | ARM Templates | Bicep | CloudFormation |
|---------|-----------|---------------|-------|----------------|
| **Multi-Cloud** | ✅ Yes | ❌ Azure only | ❌ Azure only | ❌ AWS only |
| **Plan Preview** | ✅ Yes | ❌ No | ❌ No | ✅ Change sets |
| **State Management** | ✅ Yes | ❌ No | ❌ No | ✅ Yes |
| **Learning Curve** | 🟡 Moderate | 🔴 Steep | 🟢 Easy | 🟡 Moderate |
| **Community** | ✅ Large | 🟡 Medium | 🟡 Growing | ✅ Large |
| **Syntax** | HCL | JSON | DSL | JSON/YAML |

### Knowledge Check (5 Multiple Choice Questions):
1. **What is the main advantage of Terraform's plan command?**
   - A) It's faster than direct deployment
   - B) It shows what changes will be made before applying them
   - C) It validates syntax only
   - D) It reduces deployment costs

2. **Which file contains the resource definitions in a Terraform project?**
   - A) variables.tf
   - B) outputs.tf
   - C) main.tf
   - D) terraform.tfvars

3. **What does Terraform use to track the current state of infrastructure?**
   - A) Azure Resource Manager
   - B) Terraform state file
   - C) Azure DevOps
   - D) Configuration files

4. **Which authentication method is used for Terraform with Azure in this pipeline?**
   - A) Azure CLI login
   - B) Managed Identity
   - C) Service Principal with environment variables
   - D) Personal access tokens

5. **What happens during the 'terraform plan' stage?**
   - A) Resources are created
   - B) Configuration is validated and an execution plan is generated
   - C) State file is updated
   - D) Providers are downloaded

**Answers: 1-B, 2-C, 3-B, 4-C, 5-B**

### Interview Questions:
1. "Explain the difference between Terraform, ARM templates, and Bicep. When would you choose each?"
2. "How does Terraform's state management work, and why is it important?"
3. "Open question: Why do we use variables like ARM_CLIENT_ID, ARM_CLIENT_SECRET, etc. but not CLIENT_ID, CLIENT_SECRET, etc. in our pipeline?"

---

## Project Structure You Built:

```
current_workspace
├── order-service/
│   ├── src/
│   │   ├── __init__.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── order.py
│   │   ├── schemas/
│   │   │   ├── __init__.py
│   │   │   └── order.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── eventhub.py
│   │   │   └── order_service.py
│   │   └── database/
│   │       ├── __init__.py
│   │       ├── connection.py
│   │       └── repository.py
│   └── main.py
├── requirements.txt
├── .gitignore
├── orders.db
├── README.md
└── deployments/
    ├── terraform/
    │   ├── main.tf                 # Main infrastructure template
    │   ├── variables.tf            # Variable definitions
    │   ├── outputs.tf              # Output definitions
    │   └── terraform.tfvars        # Variable values
    └── pipelines/
        ├── infrastructure.yml      # Main deployment pipeline
        └── variables.yml           # Pipeline variable references
```

## Terraform Template Features You Implemented:

✅ **Variables** - Configurable values for different environments  
✅ **Data Sources** - Reference existing Azure resource group  
✅ **Resources** - App Service Plan, Event Hubs (Namespace and Hub), Linux Web App  
✅ **Local Values** - Computed values and naming conventions  
✅ **Outputs** - Structured results for pipeline integration  
✅ **Dependencies** - Explicit and implicit resource dependency management  
✅ **Tags** - Consistent resource tagging for management  
✅ **Provider Configuration** - Azure Resource Manager provider setup  

## Terraform Advanced Features:

### 🏗️ **Resource Types Used**:
- **`azurerm_service_plan`** - App Service Plan for hosting
- **`azurerm_eventhub_namespace`** - Event Hub Namespace
- **`azurerm_eventhub`** - Event Hub for messaging
- **`azurerm_eventhub_authorization_rule`** - Access permissions
- **`azurerm_linux_web_app`** - Linux-based web application
- **`data.azurerm_resource_group`** - Reference existing resource group

### ⚙️ **Terraform Workflow**:
1. **`terraform init`** - Initialize working directory
2. **`terraform validate`** - Validate configuration syntax
3. **`terraform fmt`** - Format code consistently
4. **`terraform plan`** - Generate execution plan
5. **`terraform apply`** - Apply changes to infrastructure

## Next Session Preview:
**We'll add advanced DevOps capabilities! You'll build:**
- **Multi-environment pipelines** with dev, test, acceptance, and production stages
- **Terraform modules** for reusable infrastructure components
- **Remote state management** with Azure Storage backend
- **Advanced Terraform patterns** with workspaces and modules
