# Project Structure and Deployment
For this technical assessment, I developed a CICD pipeline that builds docker images and deploys them to an EKS cluster. The docker images represent microservices powering an e-commerce template. You can find in this repo the CDK code that I used to create the pipeline and source for my APIs and their containers. Please note the following:

1) The pipeline stack is defined in `/service_mesh/container_pipeline`. The `/service-mesh/src` directory contains a single deployment template and a simple docker recipe. While this can be used as a proof-of-concept as is, pointing the pipeline stacks to existing repositories outside the project will improve management. That way, this CDK project can be kept as both a template and a tracker for ongoing pipelines and what resources they point to without the complexity of multiple projects or git branches.
2) The `istio_cluster_stack` is non-functional. It seems to timeout whenever IAM permissions are applied to it, causing a rollback to deletion. This might be related to the VPC networking configuration, Of note, each failed build required 40 minutes to complete. Since I was limited in time to build and complete this project, I had to postpone completing this feature, but would be a top priority for completion given more time.
3) The final stage of the pipeline deploys templates to the EKS cluster. The way I managed to accomplish that was by separately creating a cluster, then granting the `CodeBuild` resource administrative permission to it via `kubectl edit` in a separate terminal after the pipeline was built. For actual deployment, please either grant the `CodeBuild` service permissions in each EKS cluser, or provision the pipeline before granting the specific CodeBuild resource permission to the cluster. *Note*: at line 111, the policy change I made did not work. The `CodeBuilder` resource was able to see and attempt to access the EKS cluster, but the cluster itself had its own permission set that prevented it from accessing internal cluster resources. This would be another priority for follow-up completion.

Before deploying, please set the context variables in `/cdk.json`:
-`proj-name`: the name of the current project all pipelines in this CDK app will deploy. Avoiding mixing project pipelines.
-`eks_cluster`: the EKS cluster where all pipelines will deploy. Multi-cluster deployments are not uncommon, but I assume closely grouped pipelines are also closely group pods.
-`container_names`: add as many containers as you like. This will cause the app to have many stacks, which can be deployed either in sequence or all at once.

My API code and Kubernetes templates are found in `/API/*`. I provisioned an EKS cluster with Istio using Terraform, which is the [prescribed documentation](https://istio.io/latest/docs/setup/platform-setup/amazon-eks/) for Istio on EKS. Simply clone the [repo](https://github.com/aws-ia/terraform-aws-eks-blueprints/blob/main/patterns/istio/README.md) and apply it. Monitoring and observability software was installed with Helm by following the instructions in the terraform repo. Other kubernetes resources, inlcuding Istio services and my APIs, were deployed entirely manually with `docker build` and `kubectl`. You can set up pipelines for each API using this CDK project, which will simplify creating ECR repositories for each image. The only resources that need to be provisioned first are:
1. `/API/environment/namespace.yml` - creates the namespace everything belongs to
2. `/API/environment/db_secret.yml` - Contains a Kubernetes secret to configure database passwords without hardcoding them into templates. Use this to recreate my work, though I recommend provisioning a token authorizer in the cluster for even more security.
3. `/API/environment/certs/*` - these represent the resources I used to enable mTLS on my cluster. Install `cert-manager.yml` first and the `certificate.yml` last. Once these exist, future infrastructure like Gateways can be installed without worry. 

**N.B.:** My templates have account-specific configurations, like ECR repos and my domain name, so please be sure to confirm before deploying.

Testing was entirely manual once the pipeline was completed. In order to test API development, I would edit code locally and manually deploy to the cluster via `kubectl`. APIs were added to Istio's service mesh via `VirtualService`, and traffic was balanced with `DestinationRules`. The `Frontend-service` was deployed alongside two copies of a test function with different traffic weights to simulate slow rollout of a new update. To simulate continuity of service while APIs were updated, API pods were manually deleted and replaced in quick succession. This was compeleted without issue. Horizontal scaling was demonstrated by increasing replica counts on `Deployment` templates. The entire cluster was also configured for global rate limiting. In order to encrypt traffic, a `Certificate` resource from Cert-Manager.io that issued Let'sEncrypt certs was deployed the API's namespace, enabling mTLS. This certificate was tested by creating a CNAME record pointing to the EKS cluster's load balancer and associating the certificate with the CNAME's domain. 


# Design Goals and Requirements
In order to meet the requirements of this take-home assessment, I created this design doc to define objectives and concerns at each stage of development. These goals were defined based on the requirements highlighted in the assessment and my own previous experience.

## Goals
- Minimize use of proprietary cloud services. Use as many open source tools as is reasonably possible in their place.
- Build with CI/CD from the beginning
- Use infrastructure as code tools from the beginning
- Include observability tools to support scaling/troubleshooting
- Make scalable to meet demand/performance
- Make secure with encryption and secure access

In summary, my design should be as agnostic to its environment as possible, while still using a performant, modern architecture that provides flexibility and supports rapid development. With that in mind, I decided on the following development plan:
1. Create a CI/CD pipeline that will provision the resources necessary to compile docker images and deploy them to a kubernetes cluster.
2. Create APIs to simulate an e-commerce website
3. Package my work to be as close to one-click deployment as possible.

During my tenure at AWS, I was required to use AWS' proprietary tools. That meant I rarely used tools like Kubernetes and Terraform, and had never used Istio previously. In fact, I was unfamiliar with most of the non-AWS tools highlighted in this assessment, so I had to spend a significant part of the assessment learning new technologies at tools. As a result, I made teh following decisions that somewhat impact the design goals: 
1. Infrastructure will be developed with AWS CDK/Cloudformation instead of Terraform. This greatly speeds up development, but makes the work less portable, which is a risk factor.
2. While I will build a CI/CD pipeline that functions, I will also forego completing it in favor of experimenting manually with Istio and its various features.

Please note that these decisions did not affect my goal to implement at least one thing that meets every technical requirement laid out in the design doc.

## Lessons Learned
I have a great deal of detailed notes about my observations and learnings related to these tool and the compromises related to these choices. I would and would be happy to share them if desire. More broadly, I found the experience very rewarding. In only a few days, I have progressed from not knowing about Istio and EKS to very much enjoying their use. Once configured properly, Istio and EKS are, in many ways, more convenient than even the serverless services I previously used. I am excited to continue working wtih these tools, including for my personal endeavors on a Raspberry Pi cluster. And now that I am familiar with these tools, I am confident that I could more rapidly complete tasks such as the ones in this assessment.

However, in retrospect, I should never have used CDK as much as I did. Terraform configuration syntax was not so different from JSON, and not using it caused me to waste time that would have been better used for other parts of the exercise. Also, for the purposes of this assessment, I think I should have developed much simpler APIs that were less prone to strange bugs so I could focus on delivering a final product faster.

As a result, I do not view this deliverable as a finished product. As I began to note above, there are additional steps that I would udnertake with more time. For example, I was not able to finish the APIs that I wanhted for the ecommerce site becuase I spent so much time wrestling with EKS configuration. The website ostensibly has support for logins and authorization tokens, but I was not able to finish the user-service API or implement authentication logic in other services. Futher, `order-service` was never deployed to the cluster.

Despite these clear shortfalls, `product-service` and `frontend` do work. Observability, mTLS, and rate limiting was implemented. And despite the rough start, Istio's service mesh is the heart of my application.