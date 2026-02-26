---
title: Setting Up a Kubernetes Cluster from Scratch
tags: kubernetes,containers,orchestration
category: infrastructure
concepts: kubernetes,cluster,kubectl,pods,kubeadm
---

## Prerequisites and Node Preparation

Before initializing a Kubernetes cluster, every node needs a few things sorted out. Disable swap permanently by commenting out swap entries in `/etc/fstab` and running `swapoff -a`. The kubelet will refuse to start if swap is active, and there is no workaround worth pursuing.

Install the container runtime first. containerd is the standard choice these days since Docker's CRI shim was removed in Kubernetes 1.24. Configure containerd to use the systemd cgroup driver by setting `SystemdCgroup = true` in `/etc/containerd/config.toml`, then restart the service. Mismatched cgroup drivers between the kubelet and the runtime cause silent pod failures that are genuinely painful to debug.

Load the required kernel modules (`overlay` and `br_netfilter`) and set `net.bridge.bridge-nf-call-iptables = 1` in sysctl. These are not optional. Without them, pod-to-pod traffic across nodes will be silently dropped.

Install kubeadm, kubelet, and kubectl from the official Kubernetes apt or yum repository. Pin the versions to avoid surprise upgrades: `apt-mark hold kubelet kubeadm kubectl`.

## Initializing the Control Plane

Run `kubeadm init` on the node designated as the control plane. Pass `--pod-network-cidr=10.244.0.0/16` if you plan to use Flannel, or `--pod-network-cidr=192.168.0.0/16` for Calico. The CIDR must match whatever CNI plugin you deploy later.

```bash
kubeadm init --pod-network-cidr=10.244.0.0/16 --apiserver-advertise-address=192.168.1.10
```

After initialization completes, copy the admin kubeconfig into your home directory:

```bash
mkdir -p $HOME/.kube
cp /etc/kubernetes/admin.conf $HOME/.kube/config
chown $(id -u):$(id -g) $HOME/.kube/config
```

Save the `kubeadm join` command printed at the end of the output. It contains a token valid for 24 hours and the CA cert hash. If you lose it, generate a new token with `kubeadm token create --print-join-command`.

Deploy the CNI plugin immediately. Without a network plugin, all pods will stay in `Pending` state and CoreDNS will never come up. For Flannel: `kubectl apply -f https://raw.githubusercontent.com/flannel-io/flannel/master/Documentation/kube-flannel.yml`. See [the Flannel documentation](https://github.com/flannel-io/flannel) for advanced configuration.

## Joining Worker Nodes and Verification

On each worker node, run the join command from the init output:

```bash
kubeadm join 192.168.1.10:6443 --token <token> --discovery-token-ca-cert-hash sha256:<hash>
```

Back on the control plane, verify all nodes are Ready:

```bash
kubectl get nodes -o wide
```

If a node stays `NotReady`, check the kubelet logs with `journalctl -u kubelet -f`. The most common causes are the CNI plugin not deploying to that node yet, or a firewall blocking port 10250.

For a production setup, consider running multiple control plane nodes for high availability. That requires an external load balancer or kube-vip in front of the API servers, which is covered in [the HA cluster guide](./traefik-routing.md). Test your cluster by deploying a simple nginx pod and exposing it with a NodePort service to confirm end-to-end networking works.
