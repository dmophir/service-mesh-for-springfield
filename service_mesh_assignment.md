# API Gateway and Service Mesh Implementation Assignment

## Objective
Implement an API Gateway and a Service Mesh within a microservices architecture to demonstrate capabilities in managing APIs, ensuring secure and efficient communication between services, and implementing common operational patterns like rate limiting, authentication, and tracing.

## Requirements and Tasks

### Environment Setup
- Create a set of microservices for a simple application (e.g., an e-commerce platform with services like user management, product catalog, and order processing).
- Containerize these microservices using Docker.
- Deploy these containers in a Kubernetes cluster (Minikube or a cloud-managed Kubernetes service can be used. We prefer AWS).

### API Gateway Implementation
- Choose an API Gateway, like Kong or AWS API Gateway.
- Configure the API Gateway to route traffic to your microservices.
- Implement rate limiting to prevent abuse of the APIs.
Bonus: 
- Set up authentication mechanisms (like API keys or OAuth) to secure the APIs.
- Ensure the API Gateway handles cross-cutting concerns like logging, monitoring, and request transformation.

### Service Mesh Implementation
- Implement a service mesh using a tool like Istio.
- Configure simple service-to-service communication within the mesh.
- Implement mutual TLS (mTLS) within the service mesh for secure communication.
Bonus: 
- Set up observability features like tracing and monitoring of inter-service communication.

### Testing and Validation
- Create scenarios to demonstrate the working of rate limiting and authentication in the API Gateway.
- Validate secure communication between services with mTLS in the service mesh.
Bonus:
- Demonstrate the use of observability tools to trace a request flow through the mesh.

### Documentation
- Include a README file explaining the architecture and the choice of tools.
- Provide step-by-step instructions for setting up the API Gateway and Service Mesh.
- Document how to run the test scenarios and interpret the results.

### Bonus (Optional)
- Implement a CI/CD pipeline to automate the deployment of microservices and configuration of the API Gateway and Service Mesh.
- Add auto-scaling capabilities to the services based on the load.

## Deliverables
- Source code for the microservices and Dockerfiles.
- Configuration files for the API Gateway and Service Mesh.
- A README file with detailed setup and testing instructions.
- (Optional) CI/CD pipeline configuration files.

## Tools to use
- AWS CloudFormation
- Kubernetes
- Terraform
- Docker
- Istio