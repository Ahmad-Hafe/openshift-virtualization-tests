"""Utilities for concurrent VM boot tests."""

import logging
from typing import Any

from ocp_resources.data_source import DataSource
from ocp_resources.datavolume import DataVolume

from tests.storage.concurrent_vm_boot.constants import BLANK_DV_SIZE, NUM_BLANK_DISKS_PER_VM
from utilities.storage import add_dv_to_vm, construct_datavolume_source_dict, data_volume_template_with_source_ref_dict
from utilities.virt import VirtualMachineForTests

LOGGER = logging.getLogger(__name__)


def blank_dv_template(name: str, namespace: str, storage_class: str) -> dict[str, Any]:
    """Build a blank DataVolume template dict suitable for dataVolumeTemplates."""
    dv = DataVolume(
        name=name,
        namespace=namespace,
        source_dict=construct_datavolume_source_dict(source="blank"),
        size=BLANK_DV_SIZE,
        storage_class=storage_class,
        api_name="storage",
    )
    dv.to_dict()
    dv.res["metadata"].pop("namespace", None)
    return dv.res


def create_vm_with_disks(
    vm_index: int,
    namespace_name: str,
    client: Any,
    data_source: DataSource,
    storage_class: str,
) -> VirtualMachineForTests:
    """Create a VM with 1 boot disk cloned from data_source and NUM_BLANK_DISKS_PER_VM blank disks."""
    vm_name = f"concurrent-vm-{vm_index}"
    LOGGER.info(f"Creating VM {vm_name}")
    vm = VirtualMachineForTests(
        name=vm_name,
        namespace=namespace_name,
        client=client,
        vm_instance_type_infer=True,
        vm_preference_infer=True,
        data_volume_template=data_volume_template_with_source_ref_dict(
            data_source=data_source,
            storage_class=storage_class,
        ),
    )
    vm.deploy(wait=True)

    for disk_index in range(NUM_BLANK_DISKS_PER_VM):
        add_dv_to_vm(
            vm=vm,
            template_dv=blank_dv_template(
                name=f"{vm_name}-blank-{disk_index}",
                namespace=namespace_name,
                storage_class=storage_class,
            ),
        )
    LOGGER.info(f"VM {vm_name} created with {1 + NUM_BLANK_DISKS_PER_VM} disks")
    return vm


def wait_for_vm_running(vm: VirtualMachineForTests, timeout: int) -> None:
    """Wait for a VM to reach Running state."""
    LOGGER.info(f"Waiting for VM {vm.name} to be running")
    vm.wait_for_ready_status(status=True, timeout=timeout)
