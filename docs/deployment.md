# Kubernetes Deployment

AMIE ships with a Helm chart at `deploy/helm/usps-amie/`. It works on any conformant Kubernetes distribution, including kind, minikube, vanilla k8s, OpenShift, Rancher RKE2, EKS, AKS, and GKE.

## Prerequisites

* `kubectl` configured against your target cluster
* `helm` 3.x
* An image registry accessible from the cluster (skip this for kind, we load images directly)
* For production: an ingress controller already installed, and optionally cert-manager for TLS

## One Command Install (kind, local)

```
./scripts/kind-up.sh
```

That script creates a kind cluster called `amie`, builds both images, loads them into the cluster, and installs the Helm chart.

## Manual Install

Build and push images:

```
export REGISTRY=ghcr.io/your-org
export TAG=0.1.0

docker build -t $REGISTRY/usps-amie-backend:$TAG -f deploy/docker/backend.Dockerfile .
docker build -t $REGISTRY/usps-amie-frontend:$TAG -f deploy/docker/frontend.Dockerfile --target prod .
docker push $REGISTRY/usps-amie-backend:$TAG
docker push $REGISTRY/usps-amie-frontend:$TAG
```

Install the chart:

```
helm upgrade --install amie deploy/helm/usps-amie \
  --namespace amie --create-namespace \
  --set backend.image.repository=$REGISTRY/usps-amie-backend \
  --set backend.image.tag=$TAG \
  --set frontend.image.repository=$REGISTRY/usps-amie-frontend \
  --set frontend.image.tag=$TAG \
  --set ingress.hosts[0].host=amie.example.com \
  --set llm.provider=anthropic \
  --set llm.anthropicApiKey=$ANTHROPIC_API_KEY \
  --wait
```

Or use a values file:

```yaml
# my-values.yaml
backend:
  image:
    repository: ghcr.io/your-org/usps-amie-backend
    tag: "0.1.0"
frontend:
  image:
    repository: ghcr.io/your-org/usps-amie-frontend
    tag: "0.1.0"

llm:
  provider: ollama

ollama:
  enabled: true
  persistence:
    size: 50Gi
    storageClassName: fast-ssd

ingress:
  enabled: true
  className: nginx
  annotations:
    nginx.ingress.kubernetes.io/proxy-read-timeout: "300"
    nginx.ingress.kubernetes.io/proxy-buffering: "off"
  hosts:
    - host: amie.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: amie-tls
      hosts:
        - amie.example.com

auth:
  enabled: true
  jwtIssuer: https://idp.example.com/realms/usps
  jwtAudience: usps-amie
```

```
helm upgrade --install amie deploy/helm/usps-amie -n amie --create-namespace -f my-values.yaml
```

## Provider Profiles

### Mock (no external calls)

```
helm upgrade --install amie deploy/helm/usps-amie -n amie --create-namespace \
  --set llm.provider=mock
```

Ship this for demo environments where you do not want an LLM footprint.

### Anthropic

```
kubectl create secret generic amie-anthropic -n amie \
  --from-literal=ANTHROPIC_API_KEY=sk-ant-...

helm upgrade --install amie deploy/helm/usps-amie -n amie \
  --set llm.provider=anthropic \
  --set llm.existingSecretName=amie-anthropic
```

### Ollama (in-cluster)

```
helm upgrade --install amie deploy/helm/usps-amie -n amie --create-namespace \
  --set llm.provider=ollama \
  --set ollama.enabled=true

# Pull a model after the pod is ready
kubectl exec -n amie deploy/amie-ollama -- ollama pull llama3.1
```

## Updating the Knowledge Base

1. Edit or add files under `backend/data/knowledge_base/*.json` or `*.md`.
2. Rebuild and push the backend image with a new tag.
3. `helm upgrade ... --set backend.image.tag=NEWTAG`
4. The new pods will detect an existing `vectors` collection in MongoDB and skip bootstrap. To force a rebuild, run `scripts/build-index.sh` inside one backend pod.

## OpenShift Notes

OpenShift refuses containers that run as root. Both AMIE images already run non-root, and the nginx image is `nginx-unprivileged`, so no SCC tuning is required beyond the default `restricted-v2` SCC.

If the default `ingress.className` is `openshift-default`, use a Route instead:

```
oc create route edge --service=amie-frontend --hostname=amie.apps.example.com
oc create route edge --service=amie-backend --hostname=amie-api.apps.example.com --path=/api
```

Or set `ingress.className: openshift-default` and rely on the Ingress -> Route translation.

## Upgrades

```
helm upgrade amie deploy/helm/usps-amie -n amie -f my-values.yaml
```

`checksum/config` is computed against the ConfigMap so env changes trigger rolling restarts.

## Uninstall

```
helm uninstall amie -n amie
kubectl delete pvc -n amie -l app.kubernetes.io/instance=amie
kubectl delete namespace amie
```

## Production Checklist

* [ ] External secrets (`llm.existingSecretName`, `addressVerifier.uspsApi.existingSecretName`, `mongo.existingSecretName`)
* [ ] TLS on ingress via cert-manager or your CA
* [ ] Backup the MongoDB PV (snapshots, a replica-set with delayed member, or MongoDB Atlas with cross-region backup)
* [ ] Alerting on liveness and readiness probe failures
* [ ] Log forwarding to your SIEM
* [ ] Network policies enforced by a CNI that supports them (Calico, Cilium, etc.)
* [ ] Resource quotas on the namespace
* [ ] Pod Security Standards set to `restricted` on the namespace
