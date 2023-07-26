### Install Helm

Install Helm in order to deploy a KubeRay operator and a RayCluster CRDs. Find instructions at the [Helm documentation](https://helm.sh/docs/intro/install/).

### Install KubeRay operator

```shell
helm install -f kuberay-values.yaml kuberay-operator kuberay/kuberay-operator --version 0.5.0
```

### Install Raycluster

```shell
helm install -f raycluster-values.yaml more-ray-cluster kuberay/ray-cluster --version 0.5.0
```

### Install NFS local provisioner

```shell
helm install -f nfs-values.yaml nfs-provisioning nfs-subdir-external-provisioner/nfs-subdir-external-provisioner
```

### Optional: In order to see stats, install metrics-server.

```shell
kubectl create -f metrics-server.yaml
```
