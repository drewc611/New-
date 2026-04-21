{{/*
Expand the name of the chart.
*/}}
{{- define "amie.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "amie.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{/*
Common labels
*/}}
{{- define "amie.labels" -}}
app.kubernetes.io/name: {{ include "amie.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version | replace "+" "_" }}
{{- end -}}

{{/*
Selector labels for a specific component
*/}}
{{- define "amie.selectorLabels" -}}
app.kubernetes.io/name: {{ include "amie.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
{{- end -}}

{{/*
Service account name
*/}}
{{- define "amie.serviceAccountName" -}}
{{- if .Values.serviceAccount.create -}}
{{- default (include "amie.fullname" .) .Values.serviceAccount.name -}}
{{- else -}}
{{- default "default" .Values.serviceAccount.name -}}
{{- end -}}
{{- end -}}

{{/*
Backend service name (stable, used in env)
*/}}
{{- define "amie.backendServiceName" -}}
{{- printf "%s-backend" (include "amie.fullname" .) -}}
{{- end -}}

{{/*
Frontend service name
*/}}
{{- define "amie.frontendServiceName" -}}
{{- printf "%s-frontend" (include "amie.fullname" .) -}}
{{- end -}}

{{/*
Redis service name
*/}}
{{- define "amie.redisServiceName" -}}
{{- printf "%s-redis" (include "amie.fullname" .) -}}
{{- end -}}

{{/*
Ollama service name
*/}}
{{- define "amie.ollamaServiceName" -}}
{{- printf "%s-ollama" (include "amie.fullname" .) -}}
{{- end -}}

{{/*
Compute the Redis URL consumed by the backend. Uses the in-cluster service
name when Redis is enabled. If auth is set, password is embedded via env from
the managed or external secret (see secret.yaml).
*/}}
{{- define "amie.redisUrl" -}}
redis://{{ include "amie.redisServiceName" . }}:{{ .Values.redis.service.port }}/0
{{- end -}}

{{/*
Compute the Ollama base URL
*/}}
{{- define "amie.ollamaBaseUrl" -}}
{{- if .Values.llm.ollamaBaseUrl -}}
{{ .Values.llm.ollamaBaseUrl }}
{{- else if .Values.ollama.enabled -}}
http://{{ include "amie.ollamaServiceName" . }}:{{ .Values.ollama.service.port }}
{{- else -}}
http://ollama:11434
{{- end -}}
{{- end -}}
