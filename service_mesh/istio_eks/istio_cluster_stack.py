# import yaml
# import requests
from constructs import Construct
from aws_cdk.lambda_layer_kubectl_v28 import KubectlV28Layer
from aws_cdk import (
	Tags,
	Stack,
	aws_eks as eks,
	aws_ec2 as ec2,
	aws_iam as iam,
	aws_lambda as lambda_
)

class IstioClusterStack(Stack):
	def __init__(self, scope: Construct, id: str, **kwargs) -> None:
		super().__init__(scope, id, **kwargs)
		app_name = self.node.try_get_context('app_name')
		cluster_name = f'{app_name}IstioCluster'

		### Supporting resources
		istio_vpc = ec2.Vpc(self, f'{app_name}IstioVpc',
							max_azs=3,
							ip_addresses=ec2.IpAddresses.cidr('10.100.0.0/16'),
							enable_dns_support=True,
							enable_dns_hostnames=True,
							create_internet_gateway=True,
							subnet_configuration=[
								ec2.SubnetConfiguration(
									name='istio-private',
									cidr_mask=20,
									subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
								),
								ec2.SubnetConfiguration(
									name='istio-public',
									cidr_mask=20,
									subnet_type=ec2.SubnetType.PUBLIC,
									map_public_ip_on_launch=True
								)
							],		
						)

		istio_cluster_role = iam.Role(self, f'{app_name}-istio-cluster-role',
									role_name=f'{app_name}IstioCluster',
									assumed_by=iam.ServicePrincipal(
										'eks.amazonaws.com'
									)
								)
		
		istio_cluster_role.add_to_policy(
			iam.PolicyStatement(
				effect=iam.Effect.ALLOW,
				actions=['sts:AssumeRole'],
				resources=['*']
			)
		)

		istio_node_role = iam.Role(self, f'{app_name}-istio-worker-role',
								role_name=f'{app_name}IstioWorker',
								assumed_by=iam.ServicePrincipal(
									'ec2.amazonaws.com'
								),
								managed_policies=[
									iam.ManagedPolicy.from_aws_managed_policy_name(
										'AmazonEKSWorkerNodePolicy'
									),
									iam.ManagedPolicy.from_aws_managed_policy_name(
										'AmazonEC2ContainerRegistryReadOnly'
									),
									iam.ManagedPolicy.from_aws_managed_policy_name(
										'AmazonEKS_CNI_Policy'
									),
									iam.ManagedPolicy.from_aws_managed_policy_name(
										'AmazonSSMManagedInstanceCore'
									),
								]
							)

		cluster_admin_role = iam.Role(self, 'cluster_admin_role',
								role_name='istio-cluster-admin-role',
								assumed_by=iam.CompositePrincipal(
									iam.AnyPrincipal(),
									iam.ServicePrincipal(
										'eks.amazonaws.com'
									)
								)
							)
		cluster_admin_role.add_managed_policy(
			iam.ManagedPolicy.from_aws_managed_policy_name('AdministratorAccess')
		)
		readonly_role = iam.Role(self, 'cluster_readonly_role',
								role_name='istio-cluster-readonly-role',
								assumed_by=iam.CompositePrincipal(
									iam.AnyPrincipal(),
									iam.ServicePrincipal(
										'eks.amazonaws.com'
									)
								)
							)
		readonly_role.add_managed_policy(
			iam.ManagedPolicy.from_aws_managed_policy_name('AdministratorAccess')
		)

		istio_cluster_sg = ec2.SecurityGroup(self, f'{app_name}IstioClusterSG',
											security_group_name='istio_cluster_sg',
											vpc=istio_vpc,
											allow_all_outbound=True,
										)
		istio_cluster_sg.add_ingress_rule(
			peer=istio_cluster_sg,
			connection=ec2.Port.all_traffic(),
			description='Allow incoming traffic within security group'
		)

		### EKS Cluster
		istio_cluster = eks.Cluster(self, cluster_name,
			cluster_name=cluster_name,
			version=eks.KubernetesVersion.V1_28,
			vpc=istio_vpc,
			default_capacity=0,
			masters_role=cluster_admin_role,
			role=istio_cluster_role,
			security_group=istio_cluster_sg,
			endpoint_access=eks.EndpointAccess.PUBLIC,
			kubectl_layer=KubectlV28Layer(self, 'kubectlv28'),
			place_cluster_handler_in_vpc=True,
			vpc_subnets=[ec2.SubnetSelection(
				subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
			)]
		)

		cluster_admin_role.grant_assume_role(istio_cluster.admin_role)
		istio_cluster.aws_auth.add_role_mapping(
			readonly_role, groups=['system:authenticated']
		)

		istio_cluster_oidc_provider = eks.OpenIdConnectProvider(self, f'{cluster_name}OIDCProvider',
												 url=istio_cluster.cluster_open_id_connect_issuer_url
		)

		istio_cluster.add_manifest('istioClusterAdminSA',
									{
										'apiVersion': 'v1',
										'kind': 'ServiceAccount',
										'metadata': {
										'name': 'cluster-admin',
										'namespace': 'kube-system'
										}
									}
								)
		istio_cluster.add_manifest('istioClusterRole',
												{
													'apiVersion': 'rbac.authorization.k8s.io/v1',
													'kind': 'ClusterRole',
													'metadata': {
														'name': 'isito-cluster-admin',
														'namespace': 'kube-system'
													},
													'rules': [
														{
															'apiGroups': ['*'],
															'resources': ['*'],
															'verbs': ['*']
														}
													]
												}
											)
		
		istio_cluster.add_manifest('istioClusterRBAC',
									{
										'apiVersion': 'rbac.authorization.k8s.io/v1',
										'kind': 'ClusterRoleBinding',
										'metadata': {
											'name': 'service-mesh-istio-cluster-admin',
											'namespace': 'kube-system'
										},
										'roleRef': {
											'apiGroup': 'rbac.authorization.k8s.io',
											'kind': 'ClusterRole',
											'name': 'istio-cluster-admin'
										},
										'subjects': [
											{
												'kind': 'User',
												'name': readonly_role.role_arn,
												'apiGroup': 'rbac.authorization.k8s.io'
											}
										]
									}
								)

		istio_cluster.add_nodegroup_capacity(f'{cluster_name}Nodegroup',
			nodegroup_name=f'{cluster_name}Nodegroup',
			instance_types=[ec2.InstanceType('t3a.medium')],
			disk_size=20,
			min_size=1,
			max_size=5,
			desired_size=2,
			ami_type=eks.NodegroupAmiType.AL2_X86_64,
			capacity_type=eks.CapacityType.ON_DEMAND,
			node_role=istio_node_role,
		)

		istio_cluster_oidc_issuer = istio_cluster.cluster_open_id_connect_issuer
		istio_cluster_oidc_provider_arn = istio_cluster_oidc_provider.open_id_connect_provider_arn

		### Install Istio
		istio_cluster.add_helm_chart('istio-base',
								chart='base',
								version='1.20.2',
								repository='https://istio-release.storage.googleapis.com/charts',
								namespace='istio-system'
							)
		istio_cluster.add_helm_chart('istiod',
								chart='istiod',
								version='1.20.2',
								repository='https://istio-release.storage.googleapis.com/charts',
								namespace='istio-system',
								wait=True
							)
		# istio_cluster.add_helm_chart('istio-ingress',
		# 						chart='gateway',
		# 						version='1.20.2',
		# 						repository='https://istio-release.storage.googleapis.com/charts',
		# 						namespace='istio-ingress',
		# 						wait=True,
		# 						values={
		# 							'labels': {
		# 								'istio': 'ingressgateway'
		# 							},
		# 							'service': {
		# 								'annotations': {
		# 									'service.beta.kubernetes.io/aws-load-balancer-type': 'external',
		# 									'service.beta.kubernetes.io/aws-load-balancer-nlb-target-type': 'ip',
		# 									'service.beta.kubernetes.io/aws-load-balancer-scheme': 'internet-facing',
		# 									'service.beta.kubernetes.io/aws-load-balancer-attributes': 'load_balancing.cross_zone.enabled=true'
		# 								}
		# 							}
		# 						}
		# 					)

		# for addon in ['kiali', 'jaeger', 'prometheus', 'grafana']:
		# 	addon_url = f'https://raw.githubusercontent.com/istio/istio/release-1.20/samples/addons/{addon}.yaml'
		# 	manifests = yaml.safe_load_all(requests.get(addon_url).content)
		# 	for manifest in manifests:
		# 		istio_cluster.add_manifest(f'{addon}-{manifest["kind"]}', manifest)