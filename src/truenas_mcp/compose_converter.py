"""Docker Compose to TrueNAS Custom App converter."""

from typing import Any, Dict

import structlog
import yaml

logger = structlog.get_logger(__name__)


class DockerComposeConverter:
    """Converts Docker Compose YAML to TrueNAS Custom App format."""

    async def convert(self, compose_yaml: str, app_name: str) -> Dict[str, Any]:
        """Convert Docker Compose to TrueNAS Custom App configuration."""
        logger.info("Converting Docker Compose to TrueNAS format", app=app_name)
        
        try:
            compose_data = yaml.safe_load(compose_yaml)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML: {e}")
        
        # Basic conversion - this is a simplified implementation
        # Full implementation would handle all Docker Compose features
        
        services = compose_data.get("services", {})
        if not services:
            raise ValueError("No services found in Docker Compose")
        
        # Take the first service as the main service (simplified)
        service_name, service_config = next(iter(services.items()))
        
        truenas_config = {
            "name": app_name,
            "image": {
                "repository": service_config.get("image", "").split(":")[0],
                "tag": service_config.get("image", "").split(":")[-1] if ":" in service_config.get("image", "") else "latest",
            },
            "network": self._convert_network(service_config),
            "storage": self._convert_storage(service_config),
            "environment": self._convert_environment(service_config),
            "restart_policy": "unless-stopped",
        }
        
        return truenas_config
    
    def _convert_network(self, service_config: Dict[str, Any]) -> Dict[str, Any]:
        """Convert network configuration."""
        network_config = {"type": "bridge"}
        
        ports = service_config.get("ports", [])
        if ports:
            port_forwards = []
            for port in ports:
                if isinstance(port, str):
                    if ":" in port:
                        host_port, container_port = port.split(":")
                        port_forwards.append({
                            "host_port": int(host_port),
                            "container_port": int(container_port),
                            "protocol": "tcp",
                        })
            
            if port_forwards:
                network_config["port_forwards"] = port_forwards
        
        return network_config
    
    def _convert_storage(self, service_config: Dict[str, Any]) -> Dict[str, Any]:
        """Convert storage/volumes configuration."""
        storage_config = {}
        
        volumes = service_config.get("volumes", [])
        for i, volume in enumerate(volumes):
            if isinstance(volume, str):
                if ":" in volume:
                    host_path, container_path = volume.split(":")[:2]
                    read_only = ":ro" in volume
                    
                    storage_key = f"volume_{i}"
                    if host_path.startswith("/mnt/"):
                        # Host path volume
                        storage_config[storage_key] = {
                            "type": "host_path",
                            "host_path": host_path,
                            "mount_path": container_path,
                            "read_only": read_only,
                        }
                    else:
                        # Named volume -> IX volume
                        storage_config[storage_key] = {
                            "type": "ix_volume",
                            "ix_volume_config": {
                                "dataset_name": host_path.replace("/", "_"),
                                "acl_enable": False,
                            },
                            "mount_path": container_path,
                        }
        
        return storage_config
    
    def _convert_environment(self, service_config: Dict[str, Any]) -> Dict[str, Any]:
        """Convert environment variables."""
        env_config = {}
        
        environment = service_config.get("environment", [])
        if isinstance(environment, list):
            for env_var in environment:
                if "=" in env_var:
                    key, value = env_var.split("=", 1)
                    env_config[key] = value
        elif isinstance(environment, dict):
            env_config = environment
        
        return env_config