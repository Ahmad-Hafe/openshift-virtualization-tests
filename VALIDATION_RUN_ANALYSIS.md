# Validation Pod Log Analysis - 2026-10-22

**Pod**: `ocp-virt-self-validation-amber-turtle-29-205-twltg` (Age: 7d21h, Status: Completed)
**Cluster**: `iuo-dualrhcos` (dual RHCOS configuration)
**Python Version**: 3.14 (inferred from `.venv/lib64/python3.14/site-packages/`)

---

## Summary

**Total Tests Failed/Errored**: 21 tests

| Status | Count |
|--------|-------|
| FAILED | 4     |
| ERROR  | 17    |

---

## Root Cause: OpenSSL 3.x SHA-1 Digest Issue

**Primary Issue**: `UnsupportedDigestmodError: [digital envelope routines] unsupported.`

This error occurs during SSH connectivity attempts to VMs. The timeout happens when trying to run a simple SSH command (`['exit']`) with a 60-second TCP timeout, but the connection hangs due to OpenSSL 3.x restrictions on SHA-1 digests.

**Source**: OpenSSL 3.x disabled SHA-1 by default as a security measure. RSA authentication during SSH key exchange uses SHA-1, which is now blocked.

**Impact**: Any test that requires SSH connectivity to a VM fails with timeout (120s wait → UnsupportedDigestmodError).

---

## Failing Tests by Category

### Storage Tests (Heaviest Impact - 13 tests)

#### Windows Clone/CDI Tests (4 tests)
- `tests/storage/cdi_clone/test_clone.py::TestWindowsClonedDv::test_vm_from_cloned_dv_windows`
- `tests/storage/cdi_clone/test_clone.py::test_clone_from_fs_to_block_using_dv_template` ⚠️ FAILED
- `tests/storage/cdi_clone/test_clone.py::test_clone_from_block_to_fs_using_dv_template` ⚠️ FAILED
- `tests/storage/cdi_clone/test_clone.py::test_clone_vm_with_4_disks`

**Pattern**: Windows VM boot → SSH → Timeout → Digest error

#### Windows-Specific Tests (5 tests)
- `tests/storage/memory_dump/test_memory_dump.py::test_windows_memory_dump`
- `tests/storage/snapshots/test_snapshots.py::test_online_windows_vm_successful_restore`
- `tests/storage/snapshots/test_snapshots.py::test_write_to_file_while_snapshot`
- `tests/storage/test_hotplug.py::TestHotPlugWindows::test_windows_hotplug`
- (Snapshot test with Windows VM)

**Pattern**: All require Windows VM SSH connectivity

#### Storage Migration/Hotplug (4 tests)
- `tests/storage/online_resize/test_sequential_disk_expand`
- `tests/storage/online_resize/test_disk_expand_then_clone_success`
- `tests/storage/storage_migration/test_storage_class_migration.py::TestStorageClassMigrationWithVolumeHotplug::test_vm_storage_class_migration_with_hotplugged_volume`
- `tests/storage/test_hotplug.py::TestHotPlugWithPersist` (2 variants: virtio-bus, scsi-bus)
- `tests/storage/test_hotplug.py::TestHotPlugWithSerialPersist`

**Pattern**: RHEL VM verification post-hotplug/migration → SSH → Timeout

### Infrastructure Tests (1 test)
- `tests/infrastructure/instance_types/supported_os/test_rhel_os.py::TestVMCreationAndValidation::test_start_vm[#rhel.10#-#ocs-storagecluster-ceph-rbd-virtualization#]` ⚠️ FAILED

**Pattern**: RHEL 10 VM boot test → SSH timeout

### Virtualization/Node Tests (4 tests)
- `tests/virt/cluster/migration_and_maintenance/test_migration_policy.py::TestMigrationPolicies::test_migration_policy_successfully_applied` (2 variants)
- `tests/virt/node/cpu_sockets_threads/test_cpu_support_sockets_threads.py::test_vm_with_cpu_support`
- `tests/virt/node/node_labeller/cpu_features/test_vm_with_cpu_flag.py::test_vm_with_cpu_flag_positive_case`
- `tests/virt/cluster/general/test_smbios.py::test_vm_smbios_default_values`

**Pattern**: VM creation → SSH connectivity → Timeout

### Concurrent VM Boot (1 test)
- `tests/storage/concurrent_vm_boot/test_concurrent_vm_boot.py::TestConcurrentVMBoot::test_concurrent_vms_boot_with_five_disks`

---

## Stack Trace Pattern

All failures follow this pattern:

```
test tries to run SSH command
  ↓
utilities/virt.py:1710 → wait_for_ssh_connectivity()
  ↓
TimeoutSampler(wait_timeout=120s, sleep=5s)
  ↓
rrmngmnt.host.run_command(['exit'], tcp_timeout=60)
  ↓
OpenSSL 3.x rejects SHA-1 in RSA key exchange
  ↓
TimeoutExpiredError: Timed Out: 120
  Last exception: UnsupportedDigestmodError: [digital envelope routines] unsupported.
```

---

## Solution Options

### Option 1: Enable Legacy Provider (Temporary, Quick Fix)
In the validation pod's SSH environment, enable the OpenSSL legacy provider for RSA:

```python
# In SSH client initialization or ENV:
export OPENSSL_CONF=/path/to/openssl.cnf  # with legacy provider enabled
```

Or in Python:
```python
os.environ['OPENSSL_LEGACY_PROVIDER'] = '1'
```

**Status**: ✅ Likely already attempted in a prior commit (per your memory: "OpenSSL SHA-1 Fix")

### Option 2: Force Stronger Auth in SSH Config
Update the validation pod's SSH configuration to prefer newer digest algorithms:
```
Host *
    HostKeyAlgorithms ssh-rsa,rsa-sha2-256,rsa-sha2-512
    PubkeyAcceptedAlgorithms ssh-rsa,rsa-sha2-256,rsa-sha2-512
```

### Option 3: Regenerate SSH Keys (Long-term)
Replace RSA keys with Ed25519 or ECDSA keys in the Windows/RHEL golden images.

---

## Impact Assessment

- **21 tests blocked** — all unable to validate functionality because SSH fails before test logic runs
- **Windows tests hardest hit** — 5+ Windows-specific tests blocked
- **RHEL tests affected** — 5+ RHEL boot/config tests blocked
- **No test logic issues** — the tests themselves are fine; infrastructure barrier (OpenSSL/SSH) is the blocker

---

## Recommendations

1. **Immediate**: Verify the OpenSSL legacy provider fix is enabled in the validation pod
2. **Check**: Run a simple SSH connectivity diagnostic on the pod
3. **Fallback**: If legacy provider doesn't work, consider using Ed25519 keys for test VMs
4. **Monitor**: This affects Python 3.14 validation runs — check if 3.11/3.12 runs show the same issue

---

## Related Memory/Issues

Per your project memory:
- **PR #6522**: HCO TaintedConfiguration blocks cluster sanity (possibly related)
- **Python 3.14 Validation Failure** (2026-09-30): Prior similar issue with 16 tests failing on UnsupportedDigestmodError
- **OpenSSL SHA-1 Fix**: Prior fix already committed — verify it's active in current pod
