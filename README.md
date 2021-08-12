# Smokeping DEMO Charm for Kubernetes

## Description

This charm deploys Smokeping services that enables the administrator to use Juju to configure endpoints to be monitored and graphed.

## Usage


### Build and deploy

Build and deploy the charm:
```
charmcraft pack
juju deploy ./smokeping-k8s.charm --resource smokeping-image=linuxserver/smokeping:latest
```

### Configuration options


### Actions

| Name | Parameters | Description |
| --- | --- |
| restart | Restarts the smokeping services.

## Developing

Create and activate a virtualenv with the development requirements:

```
    virtualenv -p python3 venv
    source venv/bin/activate
    pip install -r requirements-dev.txt
```

## Testing

The Python operator framework includes a very nice harness for testing
operator behaviour without full deployment. Just `run_tests`:

```
    ./run_tests
```
