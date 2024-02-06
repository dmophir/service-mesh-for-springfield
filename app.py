import aws_cdk as cdk
from service_mesh.container_pipeline.pipeline_stack import ContainerPipelineStack
from service_mesh.istio_eks.istio_cluster_stack import IstioClusterStack

app = cdk.App()
#IstioClusterStack(app, 'IstioClusterStack')

container_names = app.node.try_get_context('container_names')
for name in container_names:
    ContainerPipelineStack(app, f'{name}-PipelineStack', name)

app.synth()
