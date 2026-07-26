"""
Concurrent VM boot with multiple disks — fixtures.
"""

import gc
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest
from timeout_sampler import TimeoutExpiredError

from tests.storage.concurrent_vm_boot.constants import NUM_CONCURRENT_VMS
from tests.storage.concurrent_vm_boot.utils import create_vm_with_disks, wait_for_vm_running
from utilities.constants.timeouts import TIMEOUT_30MIN

LOGGER = logging.getLogger(__name__)


@pytest.fixture(scope="class")
def concurrent_vms_with_four_disks(
    unprivileged_client,
    namespace,
    fedora_data_source_scope_module,
    storage_class_name_scope_class,
):
    """
    Create NUM_CONCURRENT_VMS VMs in parallel, each with 4 disks (1 boot + 3 blank).

    The boot disk is cloned from the Fedora golden image DataSource.
    Instance type and preference are inferred from the golden image.
    Three additional blank DataVolumes are attached via dataVolumeTemplates.
    All VMs are created in parallel, then started simultaneously before yielding.
    """
    vms = []
    try:
        LOGGER.info(f"Creating {NUM_CONCURRENT_VMS} VMs in parallel")
        with ThreadPoolExecutor(max_workers=NUM_CONCURRENT_VMS) as executor:
            futures = {
                executor.submit(
                    create_vm_with_disks,
                    vm_index=vm_index,
                    namespace_name=namespace.name,
                    client=unprivileged_client,
                    data_source=fedora_data_source_scope_module,
                    storage_class=storage_class_name_scope_class,
                ): vm_index
                for vm_index in range(NUM_CONCURRENT_VMS)
            }
            for future in as_completed(futures):
                vms.append(future.result())

        LOGGER.info(f"Starting {len(vms)} VMs simultaneously")
        with ThreadPoolExecutor(max_workers=len(vms)) as executor:
            start_futures = {executor.submit(vm.start): vm for vm in vms}
            for future in as_completed(start_futures):
                future.result()

        yield vms
    finally:
        for vm in vms:
            vm.clean_up()
        # Force garbage collection to prevent memory leaks due to paramiko/paramiko#2568
        gc.collect()


@pytest.fixture(scope="class")
def booted_concurrent_vms(concurrent_vms_with_four_disks):
    """Wait for all concurrent VMs to reach Running state in parallel."""
    failed = []
    with ThreadPoolExecutor(max_workers=len(concurrent_vms_with_four_disks)) as executor:
        futures = {
            executor.submit(wait_for_vm_running, vm=vm, timeout=TIMEOUT_30MIN): vm
            for vm in concurrent_vms_with_four_disks
        }
        for future in as_completed(futures):
            vm = futures[future]
            try:
                future.result()
            except TimeoutExpiredError:
                LOGGER.error(f"VM {vm.name} failed to reach Running state")
                failed.append(vm.name)

    if failed:
        pytest.fail(f"{len(failed)}/{len(concurrent_vms_with_four_disks)} VMs failed to boot: {failed}")

    yield concurrent_vms_with_four_disks
