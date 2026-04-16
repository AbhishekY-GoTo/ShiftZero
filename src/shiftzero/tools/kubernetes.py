"""Kubernetes tool integration"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from kubernetes import client, config
from kubernetes.client.rest import ApiException

logger = logging.getLogger(__name__)


class KubernetesTool:
    """Tool for interacting with Kubernetes clusters"""

    def __init__(self, kubeconfig_path: Optional[str] = None):
        """
        Initialize Kubernetes client

        Args:
            kubeconfig_path: Path to kubeconfig file (None = use default)
        """
        self.enabled = False
        self.core_v1 = None
        self.apps_v1 = None

        try:
            if kubeconfig_path:
                config.load_kube_config(config_file=kubeconfig_path)
            else:
                # Try in-cluster config first, then default kubeconfig
                try:
                    config.load_incluster_config()
                except config.ConfigException:
                    config.load_kube_config()

            self.core_v1 = client.CoreV1Api()
            self.apps_v1 = client.AppsV1Api()
            self.enabled = True
            logger.info("Kubernetes client initialized successfully")

        except Exception as e:
            logger.warning(f"Kubernetes client not available: {e}")
            logger.warning("K8s tools will return errors (this is OK for testing without K8s)")

    async def get_pod_status(
        self,
        namespace: str,
        pod_name: Optional[str] = None,
        deployment_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get pod status, health, and recent events

        Args:
            namespace: Kubernetes namespace
            pod_name: Specific pod name (optional)
            deployment_name: Get pods from deployment (optional)

        Returns:
            Pod status information
        """
        if not self.enabled:
            return {"error": "Kubernetes client not configured. Set KUBECONFIG in .env"}

        try:
            pods = []

            if pod_name:
                # Get specific pod
                pod = self.core_v1.read_namespaced_pod(pod_name, namespace)
                pods = [pod]
            elif deployment_name:
                # Get pods from deployment
                deployment = self.apps_v1.read_namespaced_deployment(
                    deployment_name, namespace
                )
                label_selector = ",".join(
                    f"{k}={v}" for k, v in deployment.spec.selector.match_labels.items()
                )
                pod_list = self.core_v1.list_namespaced_pod(
                    namespace, label_selector=label_selector
                )
                pods = pod_list.items
            else:
                return {"error": "Must provide either pod_name or deployment_name"}

            if not pods:
                return {
                    "status": "not_found",
                    "message": f"No pods found in namespace {namespace}"
                }

            # Analyze pods
            pod_statuses = []
            for pod in pods:
                container_statuses = []
                restart_count = 0

                if pod.status.container_statuses:
                    for container in pod.status.container_statuses:
                        restart_count += container.restart_count

                        state_info = {}
                        if container.state.running:
                            state_info = {"state": "running"}
                        elif container.state.waiting:
                            state_info = {
                                "state": "waiting",
                                "reason": container.state.waiting.reason,
                                "message": container.state.waiting.message
                            }
                        elif container.state.terminated:
                            state_info = {
                                "state": "terminated",
                                "reason": container.state.terminated.reason,
                                "exit_code": container.state.terminated.exit_code
                            }

                        container_statuses.append({
                            "name": container.name,
                            "ready": container.ready,
                            "restart_count": container.restart_count,
                            **state_info
                        })

                # Get recent events for this pod
                events = self.core_v1.list_namespaced_event(
                    namespace,
                    field_selector=f"involvedObject.name={pod.metadata.name}"
                )
                recent_events = [
                    {
                        "reason": event.reason,
                        "message": event.message,
                        "count": event.count,
                        "last_seen": event.last_timestamp.isoformat() if event.last_timestamp else None
                    }
                    for event in sorted(
                        events.items,
                        key=lambda e: e.last_timestamp or datetime.min.replace(tzinfo=timezone.utc),
                        reverse=True
                    )[:5]  # Last 5 events
                ]

                pod_statuses.append({
                    "pod_name": pod.metadata.name,
                    "status": pod.status.phase,
                    "restart_count": restart_count,
                    "containers": container_statuses,
                    "events": recent_events,
                    "node": pod.spec.node_name,
                    "created_at": pod.metadata.creation_timestamp.isoformat()
                })

            return {
                "namespace": namespace,
                "pods": pod_statuses,
                "total_pods": len(pod_statuses),
                "unhealthy_pods": len([
                    p for p in pod_statuses
                    if p["status"] != "Running" or p["restart_count"] > 0
                ])
            }

        except ApiException as e:
            logger.error(f"Kubernetes API error: {e}")
            return {"error": f"Kubernetes API error: {e.status} - {e.reason}"}
        except Exception as e:
            logger.error(f"Error getting pod status: {e}")
            return {"error": str(e)}

    async def get_pod_logs(
        self,
        namespace: str,
        pod_name: str,
        container: Optional[str] = None,
        lines: int = 100
    ) -> str:
        """
        Get recent logs from a pod

        Args:
            namespace: Kubernetes namespace
            pod_name: Pod name
            container: Container name (optional, defaults to first container)
            lines: Number of log lines to retrieve

        Returns:
            Log content as string
        """
        if not self.enabled:
            return "Error: Kubernetes client not configured. Set KUBECONFIG in .env"

        try:
            logs = self.core_v1.read_namespaced_pod_log(
                pod_name,
                namespace,
                container=container,
                tail_lines=lines
            )
            return logs

        except ApiException as e:
            logger.error(f"Error getting pod logs: {e}")
            return f"Error: {e.status} - {e.reason}"
        except Exception as e:
            logger.error(f"Error getting pod logs: {e}")
            return f"Error: {str(e)}"

    async def restart_deployment(
        self,
        namespace: str,
        deployment_name: str,
        reason: str
    ) -> Dict[str, Any]:
        """
        Perform rolling restart of a deployment

        Args:
            namespace: Kubernetes namespace
            deployment_name: Deployment name
            reason: Reason for restart (for audit)

        Returns:
            Restart operation result
        """
        if not self.enabled:
            return {"status": "error", "error": "Kubernetes client not configured. Set KUBECONFIG in .env"}

        try:
            # Read current deployment
            deployment = self.apps_v1.read_namespaced_deployment(
                deployment_name, namespace
            )

            # Trigger rolling restart by updating pod template annotation
            if deployment.spec.template.metadata.annotations is None:
                deployment.spec.template.metadata.annotations = {}

            deployment.spec.template.metadata.annotations["shiftzero.io/restartedAt"] = \
                datetime.utcnow().isoformat()
            deployment.spec.template.metadata.annotations["shiftzero.io/restartReason"] = \
                reason

            # Patch the deployment
            self.apps_v1.patch_namespaced_deployment(
                deployment_name,
                namespace,
                deployment
            )

            logger.info(
                f"Initiated rolling restart of deployment {deployment_name} "
                f"in namespace {namespace}. Reason: {reason}"
            )

            return {
                "status": "success",
                "deployment": deployment_name,
                "namespace": namespace,
                "reason": reason,
                "timestamp": datetime.utcnow().isoformat(),
                "message": "Rolling restart initiated successfully"
            }

        except ApiException as e:
            logger.error(f"Error restarting deployment: {e}")
            return {
                "status": "error",
                "error": f"{e.status} - {e.reason}"
            }
        except Exception as e:
            logger.error(f"Error restarting deployment: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    async def check_deployment_history(
        self,
        namespace: str,
        deployment_name: str
    ) -> Dict[str, Any]:
        """
        Check recent deployment history

        Args:
            namespace: Kubernetes namespace
            deployment_name: Deployment name

        Returns:
            Deployment history information
        """
        if not self.enabled:
            return {"error": "Kubernetes client not configured. Set KUBECONFIG in .env"}

        try:
            # Get deployment
            deployment = self.apps_v1.read_namespaced_deployment(
                deployment_name, namespace
            )

            # Get replica sets for this deployment
            label_selector = ",".join(
                f"{k}={v}" for k, v in deployment.spec.selector.match_labels.items()
            )
            rs_list = self.apps_v1.list_namespaced_replica_set(
                namespace, label_selector=label_selector
            )

            # Sort by creation time
            replica_sets = sorted(
                rs_list.items,
                key=lambda rs: rs.metadata.creation_timestamp,
                reverse=True
            )

            history = []
            for rs in replica_sets[:5]:  # Last 5 replica sets
                history.append({
                    "name": rs.metadata.name,
                    "revision": rs.metadata.annotations.get("deployment.kubernetes.io/revision"),
                    "replicas": rs.status.replicas or 0,
                    "ready_replicas": rs.status.ready_replicas or 0,
                    "created_at": rs.metadata.creation_timestamp.isoformat(),
                    "image": rs.spec.template.spec.containers[0].image if rs.spec.template.spec.containers else None
                })

            return {
                "deployment": deployment_name,
                "namespace": namespace,
                "current_replicas": deployment.status.replicas,
                "ready_replicas": deployment.status.ready_replicas,
                "history": history
            }

        except ApiException as e:
            logger.error(f"Error checking deployment history: {e}")
            return {"error": f"{e.status} - {e.reason}"}
        except Exception as e:
            logger.error(f"Error checking deployment history: {e}")
            return {"error": str(e)}
