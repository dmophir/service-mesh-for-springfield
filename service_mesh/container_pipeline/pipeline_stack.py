from constructs import Construct
from aws_cdk import (
	Stack,
	aws_iam as iam,
	aws_ecr as ecr,
	aws_lambda as lambda_,
	aws_codebuild as codebuild,
	aws_codecommit as codecommit,
	aws_codepipeline as codepipeline,
	aws_codepipeline_actions as codepipeline_actions
)

class ContainerPipelineStack(Stack):
	def __init__(self, scope: Construct, id: str, container_name: str, **kwargs) -> None:
		super().__init__(scope, id, **kwargs)
		proj_name = self.node.try_get_context('proj_name')
		ecr_name = f'{proj_name}/{container_name}'
		repo_name = f'{proj_name}_{container_name}'

		#pod_deployer = lambda_.Function.from_function_arn(self.node.try_get_context('pod_deployer_arn'))

		# git_repo = codecommit.Repository(self, f'{repo_name}-codecommit',
		# 					   repository_name=repo_name,
		# 					   code=codecommit.Code.from_directory('service_mesh/src')
		# 					   )
		
		git_repo = codecommit.Repository.from_repository_name(self, f'{repo_name}-codecommit',
																repository_name=repo_name
															)
		
		ecr_repo = ecr.Repository(self, f'{ecr_name}-ecr', repository_name=ecr_name)

		container_project = codebuild.PipelineProject(self, f'{repo_name}-build',
												project_name=f'{repo_name}-project',
												environment=codebuild.BuildEnvironment(privileged=True),
												build_spec=codebuild.BuildSpec.from_object({
													'version': '0.02',
													'phases': {
														'build': {
															'commands': [
																'$(aws ecr get-login --region $AWS_DEFAULT_REGION --no-include-email)',
																'docker build -t $REPOSITORY_URI:latest .',
																'docker tag $REPOSITORY_URI:latest $REPOSITORY_URI:$CODEBUILD_RESOLVED_SOURCE_VERSION'
															]
														},
														'post_build': {
															'commands': [
																'docker push $REPOSITORY_URI:latest',
																'docker push $REPOSITORY_URI:$CODEBUILD_RESOLVED_SOURCE_VERSION',
																'export imageTag=$CODEBUILD_RESOLVED_SOURCE_VERSION',
																'printf \'[{\"name\":\"app\",\"imageUri\":\"%s\"}]\' $REPOSITORY_URI:$imageTag > imagedefinitions.json'
															]
														}
													},
													'env': {
														'exported_variables': ['imageTag']
													},
													'artifacts': {
														'files': 'imagedefinitions.json',
														'secondary-artifacts': {
															'imagedefinitions': {
																'files': 'imagedefinitions.json',
																'name': 'imagedefinitions'
															}
														}
													}
												}),
												environment_variables={
													'REPOSITORY_URI': codebuild.BuildEnvironmentVariable(
														value=ecr_repo.repository_uri
													)
												}
											)
		
		ecr_repo.grant_pull_push(container_project)

		pod_project = codebuild.PipelineProject(self, f'{repo_name}-deploy',
												environment=codebuild.BuildEnvironment(
													privileged=True,
													build_image=codebuild.LinuxBuildImage.STANDARD_7_0
												),
												build_spec=codebuild.BuildSpec.from_object({
													'version': '0.2',
													'phases': {
														'build': {
															'commands': [
																'aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin $REPOSITORY_URI',
																'aws eks update-kubeconfig --name $EKS_CLUSTER_NAME',
																'aws eks get-token --cluster-name istio --output json',
																'kubectl auth can-i "*" "*"',
																'kubectl apply -f kube-manifests/'
															]
														}
													},
													'artifacts': {
														'files': [
															'build.json',
															'kube-manifests/*'
														]
													}
												}),
												environment_variables={
													'REPOSITORY_URI': codebuild.BuildEnvironmentVariable(
														value=ecr_repo.repository_uri
													),
													'EKS_CLUSTER_NAME': codebuild.BuildEnvironmentVariable(
														#value='istio'
														value=self.node.try_get_context('eks_cluster_name')
													)
												},
											)
		
		ecr_repo.grant_pull(pod_project)
		git_repo.grant_pull(pod_project)
		pod_project.add_to_role_policy(iam.PolicyStatement(
			effect=iam.Effect.ALLOW,
			actions=['eks:Describe', 'sts:AssumeRole'],
			resources=['*']
		))

		source_output = codepipeline.Artifact()
		source_action = codepipeline_actions.CodeCommitSourceAction(
			action_name=f'{repo_name}-source_stage',
			repository=git_repo,
			output=source_output,
			code_build_clone_output=True
		)
		build_action = codepipeline_actions.CodeBuildAction(
			action_name=f'{repo_name}-build_stage',
			project=container_project,
			input=source_output,
			outputs=[codepipeline.Artifact('imagedefinitions')],
			execute_batch_build=False
		)
		deploy_action = codepipeline_actions.CodeBuildAction(
			action_name=f'{repo_name}_deploy-stage',
			project=pod_project,
			input=source_output,
			execute_batch_build=False
		)
		container_pipeline = codepipeline.Pipeline(self, f'{repo_name}-pipeline', 
													pipeline_name=repo_name,
													stages=[
														{
															'stageName': 'Source',
															'actions': [source_action]
														},
														{
															'stageName': 'Build',
															'actions': [build_action]
														},
														{
															'stageName': 'Deploy',
															'actions': [deploy_action]
														}
													]
												)