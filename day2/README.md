# Session 2: Build Azure Pipeline for Infrastructure Deployment with Bicep



## What You'll Build Today (2 minutes)

**End Result**: A complete CI/CD pipeline using Azure DevOps that automatically deploys infrastructure with Bicep templates, uses managed variable groups for secure configuration, and deploys the same Order Service from Session 1 through Infrastructure as Code (IaC).



---



## Hands-On Block (58 minutes)

### Step 1: Create Bicep Infrastructure Templates (15 minutes)



**Create project structure:**

```bash

mkdir -p deployments/{bicep,pipelines}

cd deployments

```



```

Your-workspace

├─ your-repo-other-content

└─ deployments/

   ├── bicep/

   │    ├─ main.bicep

   │    └─ main.bicepparam

   └── pipelines/

        ├─ infrastructure.yml

        └─ variables.yml

```



**Create Bicep Template (`bicep/main.bicep`):**

```bicep

@description('Student name for resource naming')

param studentName string = 'your-unique-name'



@description('Environment name')

param environment string = 'production'



// Location inherited from resource group

@description('Location for all resources')

param location string = resourceGroup().location



@description('App Service Plan SKU')

param appServicePlanSku string = 'B3'



@description('Event Hub Namespace SKU')

param eventHubSku string = 'Standard'



// Variables

var appServicePlanName = '${studentName}-plan'

var webAppName = '${studentName}-order-service'

var eventHubNamespaceName = '${studentName}-events'

var eventHubName = 'orders'



// App Service Plan

resource appServicePlan 'Microsoft.Web/serverfarms@2022-03-01' = {

  name: appServicePlanName

  location: location

  sku: {

    name: appServicePlanSku

  }

  kind: 'linux'

  properties: {

    reserved: true

  }

}



// Event Hub Namespace

resource eventHubNamespace 'Microsoft.EventHub/namespaces@2022-01-01-preview' = {

  name: eventHubNamespaceName

  location: location

  sku: {

    name: eventHubSku

    tier: eventHubSku

    capacity: 1

  }

}



// Event Hub

resource eventHub 'Microsoft.EventHub/namespaces/eventhubs@2022-01-01-preview' = {

  parent: eventHubNamespace

  name: eventHubName

  properties: {

    messageRetentionInDays: 1

    partitionCount: 1

  }

}



// Event Hub Authorization Rule

resource eventHubAuthRule 'Microsoft.EventHub/namespaces/eventhubs/authorizationrules@2022-01-01-preview' = {

  parent: eventHub

  name: 'orders-access-key'

  properties: {

    rights: [

      'Listen'

      'Send'

    ]

  }

}



// Web App

resource webApp 'Microsoft.Web/sites@2022-03-01' = {

  name: webAppName

  location: location

  kind: 'app,linux'

  properties: {

    serverFarmId: appServicePlan.id

    reserved: true

    httpsOnly: true

    siteConfig: {

      linuxFxVersion: 'PYTHON|3.9'

      appCommandLine: 'uvicorn main:app --host 0.0.0.0 --port 8000'

      alwaysOn: true

      appSettings: [

        {

          name: 'EVENT_HUB_CONNECTION_STRING'

          value: eventHubAuthRule.listKeys().primaryConnectionString

        }

        {

          name: 'EVENT_HUB_NAME'

          value: eventHubName

        }

        {

          name: 'ENVIRONMENT'

          value: environment

        }

      ]

    }

  }

}



// Outputs

output webAppName string = webApp.name

output webAppUrl string = 'https://${webApp.properties.defaultHostName}'

output eventHubConnectionString string = eventHubAuthRule.listKeys().primaryConnectionString

```



**Create Bicep Parameters File (`bicep/main.bicepparam`):**

```bicep-params

using 'main.bicep'



param studentName = 'your-unique-name'

param environment = 'production'

param appServicePlanSku = 'B3'

param eventHubSku = 'Standard'

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

APPLICATION_ID: <your-service-principal-id>

APPLICATION_SECRET: <your-service-principal-secret>  # Mark as Secret

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

    displayName: 'Authenticate to Azure'

    steps:

    - checkout: self

      displayName: 'Checkout my code'

    

    - script: |

        az --version

        az bicep version

      displayName: 'Validate azure CLI and Bicep installation'



    - script: |

        echo "Setting up Azure CLI..."

        az login --service-principal -u $(APPLICATION_ID) -p $(APPLICATION_SECRET) --tenant $(TENANT_ID)

        az account set --subscription $(SUBSCRIPTION_ID)

      displayName: 'Azure CLI Setup - Authenticate to Azure'

      

# For the sake of learning, we deploy using complete mode

# This will also delete any resources not defined in the Bicep template to together with the resources defined in the template

- stage: DeployInfrastructure

  displayName: 'Deploy Infrastructure'

  dependsOn: CheckoutAndAuthenticate

  jobs:

  - job: DeployInfrastructure

    displayName: 'Deploy Infrastructure'

    steps:

    - script: |

        echo "Deploying Bicep Template..."

        az deployment group create \

          --mode Complete \

          --resource-group $(RG) \

          --template-file deployments/bicep/main.bicep \

          --parameters deployments/bicep/main.bicepparam \

          --name "infrastructure-$(Build.BuildId)"

      displayName: 'Deploy Bicep Template'



    - script: |

        echo "✅ Infrastructure deployed successfully!"

          

        # Show created resources

        az resource list \

          --resource-group $(RG) \

          --query "[].{Name:name, Type:type, Location:location}" \

          --output table

      displayName: 'Show Deployment Results'

```



### Step 4: Run the Pipeline and Deploy (10 minutes)



**Create and Run Pipeline:**

1. In Azure DevOps, go to **Pipelines** → **Pipelines**

2. Click **New pipeline**

3. Select **Azure Repos Git** (or your repository type)

4. Select your repository

5. Choose **Existing Azure Pipelines YAML file**

6. Select `/deployments/pipelines/infrastructure.yml`

7. Click **Continue** → **Run**



**Monitor the Pipeline:**

- Watch the validation stage complete

- Monitor the deployment progress

- Check the deployment results and outputs



**Verify Deployment:**

```bash

# In Azure Cloud Shell or local Azure CLI

az resource list \

  --resource-group <your-rg> \

  --query "[].{Name:name, Type:type, Status:properties.provisioningState}" \

  --output table

```





---



## What You Built Today:



✅ **Infrastructure as Code (IaC)** - Complete Bicep templates for Azure resources  

✅ **CI/CD Pipeline** - Automated deployment using Azure DevOps  

✅ **Secure Configuration** - Variable groups and service connections  

✅ **Template Validation** - Bicep validation before deployment  

✅ **Parameter Management** - Separate parameter files for different environments  

✅ **Deployment Outputs** - Structured outputs for integration  

✅ **Complete Automation** - From code commit to live infrastructure  



## Bicep Template Benefits You Implemented:



| Feature | Benefit | Implementation |

|---------|---------|----------------|

| **Declarative** | Define what you want, not how to get it | Bicep resource definitions |

| **Idempotent** | Run multiple times safely | ARM template deployment mode |

| **Parameterized** | Reusable across environments | `@description` and `param` |

| **Type Safety** | Catch errors at compile time | Bicep language validation |

| **Modular** | Organize complex infrastructures | Separate template files |

| **Version Control** | Track infrastructure changes | Git integration |



## Pipeline Stages Breakdown:



### 🔍 **Validation Stage**

- **Bicep Installation**: Ensures latest Bicep CLI

- **Template Validation**: Checks syntax and dependencies

- **Parameter Validation**: Verifies parameter files

- **Resource Validation**: Validates Azure resource definitions



### 🚀 **Deployment Stage**

- **Resource Provisioning**: Creates Azure resources

- **Configuration Application**: Sets app settings and configurations

- **Output Generation**: Provides deployment results

- **Status Reporting**: Shows deployment summary



### 📊 **Verification Stage**

- **Resource Listing**: Shows all created resources

- **URL Generation**: Provides application endpoints

- **Health Checking**: Validates application availability



## Infrastructure Architecture You Deployed:



```

Azure Resource Group

├── App Service Plan (B3 SKU)

│   ├── Linux-based hosting

│   └── Auto-scaling capabilities

├── Event Hub Namespace

│   ├── Standard SKU

│   ├── Event Hub: "orders"

│   └── Authorization Rules

└── Web App (Python 3.9)

    ├── Auto-configured with Event Hub

    ├── Environment variables set

    └── HTTPS enforced

```



## Session Recap:



### Key Takeaways:

1. **Infrastructure as Code** - Automated, repeatable infrastructure deployment

2. **Bicep Advantages** - Type-safe, declarative infrastructure definitions

3. **CI/CD Integration** - Automated validation and deployment pipeline

4. **Security Best Practices** - Service principals and variable groups

5. **Environment Management** - Parameterized templates for multiple environments

6. **DevOps Workflow** - Complete automation from commit to deployment



### Knowledge Check (5 Multiple Choice Questions):

1. **What is the main advantage of using Bicep over ARM templates?**

   - A) Faster deployment

   - B) Better syntax and type safety

   - C) Lower cost

   - D) More Azure services supported



2. **What deployment mode should you use for production environments?**

   - A) Complete mode

   - B) Incremental mode

   - C) Override mode

   - D) Merge mode



3. **Where should sensitive configuration like service principal secrets be stored?**

   - A) In the Bicep template

   - B) In the parameter file

   - C) In Azure DevOps variable groups (marked as secret)

   - D) In the pipeline YAML file



4. **What happens during the Bicep validation stage?**

   - A) Resources are created

   - B) Template syntax and dependencies are checked

   - C) Application code is deployed

   - D) Costs are calculated



5. **Which Azure DevOps feature enables secure connection to Azure resources?**

   - A) Variable groups

   - B) Service connections

   - C) Pipeline templates

   - D) Build agents



**Answers: 1-B, 2-B, 3-C, 4-B, 5-B**



### Interview Questions:

1. "Explain the difference between Bicep and ARM templates. When would you use each?"

2. "How would you handle secrets and sensitive data in your Bicep deployments with Azure Pipeline?"

3. "Open question: Describe your strategy for managing multiple environments (dev, staging, prod) with Bicep."



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

    ├── bicep/

    │   ├── main.bicep           # Main infrastructure template

    │   └── main.bicepparam      # Environment-specific parameters

    └── pipelines/

      ├── infrastructure.yml   # Main deployment pipeline

      └── variables.yml        # Pipeline variable references



```



## Bicep Template Features You Implemented:



✅ **Parameters** - Configurable values for different environments  

✅ **Variables** - Computed values and naming conventions  

✅ **Resources** - App Service Plan, Event Hubs (Namespace and Hub), Web App  

✅ **Dependencies** - Automatic resource dependency management  

✅ **Outputs** - Structured results for pipeline integration  

✅ **Security** - Proper authorization rules and HTTPS enforcement  

✅ **Configuration** - Automatic app settings injection  

✅ **Best Practices** - Resource naming, location inheritance  



## Next Session Preview:

**We'll add advanced DevOps capabilities! You'll build:**

- **Multi-environment pipelines** with dev, test, acceptance, and production stages

- **Terraform integration** for complex infrastructure




