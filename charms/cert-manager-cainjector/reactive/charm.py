import os

from charms import layer
from charms.reactive import clear_flag, hook, set_flag, when, when_any, when_not


@hook("upgrade-charm")
def upgrade_charm():
    clear_flag("charm.started")


@when("charm.started")
def charm_ready():
    layer.status.active("")


@when_any("layer.docker-resource.oci-image.changed", "config.changed")
def update_image():
    clear_flag("charm.started")


@when("layer.docker-resource.oci-image.available")
@when_not("charm.started")
def start_charm():
    layer.status.maintenance("configuring container")

    image_info = layer.docker_resource.get_info("oci-image")

    namespace = os.environ["JUJU_MODEL_NAME"]

    layer.caas_base.pod_spec_set(
        {
            "version": 2,
            "serviceAccount": {
                "global": True,
                "rules": [
                    {
                        "apiGroups": ["cert-manager.io"],
                        "resources": ["certificates"],
                        "verbs": ["get", "list", "watch"],
                    },
                    {
                        "apiGroups": [""],
                        "resources": ["secrets"],
                        "verbs": ["get", "list", "watch"],
                    },
                    {
                        "apiGroups": [""],
                        "resources": ["events"],
                        "verbs": ["get", "create", "update", "patch"],
                    },
                    {
                        "apiGroups": ["admissionregistration.k8s.io"],
                        "resources": [
                            "validatingwebhookconfigurations",
                            "mutatingwebhookconfigurations",
                        ],
                        "verbs": ["get", "list", "watch", "update"],
                    },
                    {
                        "apiGroups": ["apiregistration.k8s.io"],
                        "resources": ["apiservices"],
                        "verbs": ["get", "list", "watch", "update"],
                    },
                    {
                        "apiGroups": ["apiextensions.k8s.io"],
                        "resources": ["customresourcedefinitions"],
                        "verbs": ["get", "list", "watch", "update"],
                    },
                ],
            },
            "containers": [
                {
                    "name": "cert-manager-cainjector",
                    "imageDetails": {
                        "imagePath": image_info.registry_path,
                        "username": image_info.username,
                        "password": image_info.password,
                    },
                    "args": ["--v=2", f"--leader-election-namespace={namespace}"],
                    "config": {"POD_NAMESPACE": namespace},
                }
            ],
        }
    )

    layer.status.maintenance("creating container")
    set_flag("charm.started")
