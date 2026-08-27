import logging

import pytest
from kubernetes.client.rest import ApiException
from ocp_resources.datavolume import DataVolume
from ocp_resources.virtual_machine_cluster_instancetype import VirtualMachineClusterInstancetype
from ocp_resources.virtual_machine_cluster_preference import VirtualMachineClusterPreference
from ocp_resources.virtual_machine_snapshot import VirtualMachineSnapshot
from pytest_testconfig import config as py_config

from tests.storage.snapshots.constants import BLANK_DV_SIZE, ERROR_MSG_USER_CANNOT_CREATE_VM_SNAPSHOTS, NUM_BLANK_DISKS
from utilities.constants.architecture import AMD_64
from utilities.constants.images import OS_FLAVOR_FEDORA
from utilities.constants.instance_types import U1_SMALL
from utilities.constants.timeouts import TIMEOUT_10MIN
from utilities.storage import (
    add_dv_to_vm,
    construct_datavolume_source_dict,
    data_volume_template_with_source_ref_dict,
)
from utilities.virt import VirtualMachineForTests, running_vm

LOGGER = logging.getLogger(__name__)


def expected_output_after_restore(snapshot_number):
    """
    Returns a string representing the list of files that should exist in the VM (sorted)
    after a restore snapshot was performed

    Args:
        snapshot_number (int): The snapshot number that was restored

    Returns:
        string: the list of files that should exist on the VM after restore operation was performed
    """
    files = []
    for idx in range(snapshot_number - 1):
        files.append(f"before-snap-{idx + 1}.txt")
        files.append(f"after-snap-{idx + 1}.txt")
    files.append(f"before-snap-{snapshot_number}.txt ")
    files.sort()
    return " ".join(files)


def fail_to_create_snapshot_no_permissions(snapshot_name, namespace, vm_name, client):
    with pytest.raises(
        ApiException,
        match=ERROR_MSG_USER_CANNOT_CREATE_VM_SNAPSHOTS,
    ):
        with VirtualMachineSnapshot(
            name=snapshot_name,
            namespace=namespace,
            vm_name=vm_name,
            client=client,
        ):
            return


def start_windows_vm_after_restore(vm_restore, windows_vm):
    vm_restore.wait_restore_done(timeout=TIMEOUT_10MIN)
    running_vm(vm=windows_vm)


def create_vm_with_4_disks(vm_name, namespace_name, client, storage_class_name, data_source):
    """Create a Fedora VM with 1 boot disk from DataSource and 3 blank DVs.

    If deploy, disk attachment, or boot fails, the VM is cleaned up before re-raising.
    Cleanup failures are chained onto the original setup exception.

    Args:
        vm_name: Name for the VM.
        namespace_name: Namespace to deploy the VM into.
        client: Kubernetes client for resource operations.
        storage_class_name: Storage class for boot and blank PVCs.
        data_source: Fedora golden image DataSource for the boot volume.

    Returns:
        Running VirtualMachineForTests with 4 disk devices.
    """
    cpu_arch = py_config["cpu_arch"]
    preference_name = f"{OS_FLAVOR_FEDORA}.{cpu_arch}" if cpu_arch and cpu_arch != AMD_64 else OS_FLAVOR_FEDORA
    vm = VirtualMachineForTests(
        name=vm_name,
        namespace=namespace_name,
        client=client,
        os_flavor=OS_FLAVOR_FEDORA,
        vm_instance_type=VirtualMachineClusterInstancetype(name=U1_SMALL, client=client),
        vm_preference=VirtualMachineClusterPreference(name=preference_name, client=client),
        data_volume_template=data_volume_template_with_source_ref_dict(
            data_source=data_source,
            storage_class=storage_class_name,
        ),
    )
    try:
        vm.deploy(wait=True)
        for disk_index in range(NUM_BLANK_DISKS):
            blank_dv = DataVolume(
                name=f"{vm_name}-blank-{disk_index}",
                namespace=namespace_name,
                client=client,
                source_dict=construct_datavolume_source_dict(source="blank"),
                size=BLANK_DV_SIZE,
                storage_class=storage_class_name,
                api_name="storage",
            )
            blank_dv.to_dict()
            blank_dv.res["metadata"].pop("namespace", None)
            add_dv_to_vm(vm=vm, template_dv=blank_dv.res)
        running_vm(vm=vm)
    except Exception as error:
        LOGGER.error(f"Failed to set up VM {vm_name}, cleaning up: {error}")
        try:
            vm.clean_up()
        except Exception as cleanup_error:
            LOGGER.error(f"Failed to clean up VM {vm_name}: {cleanup_error}")
            raise error from cleanup_error
        raise
    return vm
