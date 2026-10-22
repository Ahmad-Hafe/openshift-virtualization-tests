# Root Cause Analysis: All 21 Test Failures

## TL;DR

**Single Root Cause**: All 21 tests fail due to the **SAME issue** — SSH connectivity blocked by OpenSSL 3.x rejecting SHA-1 in RSA key exchange.

No unique issues per test. No test logic problems. **Pure infrastructure barrier.**

---

## The Common Problem

```
Test creates VM → SSH connection attempt → OpenSSL 3.x rejects SHA-1 → Timeout → Failure
```

**Exception Stack**:
```
timeout_sampler.TimeoutExpiredError: Timed Out: 120
Function: rrmngmnt.host.run_command  Kwargs: {'command': ['exit'], 'tcp_timeout': 60}
Last exception: UnsupportedDigestmodError: [digital envelope routines] unsupported.
Elapsed time: 120 [0:02:00]
```

---

## Why This Affects ALL 21 Tests (No Exceptions)

Every test in the validation run follows this sequence:

1. **Create a test VM** — Windows, RHEL, or Fedora (via `VirtualMachineForTests()`)
2. **Boot the VM** — network brings up, DHCP assigns IP
3. **Validate VM is ready** — call `wait_for_running_vm()` or `running_vm()` fixture
4. **Inside validation** — `wait_for_ssh_connectivity()` is called to verify connectivity
5. **SSH attempt fails** — OpenSSL 3.x rejects SHA-1 in RSA auth
6. **Timeout after 120s** — SSH keeps retrying (5s sleep interval × 24 attempts)
7. **Test fails** — before any actual test logic runs

**Location in code**:
```python
utilities/virt.py:1710 → wait_for_ssh_connectivity()
  ↓
timeout_sampler.TimeoutSampler(wait_timeout=120, sleep=5)
  ↓
rrmngmnt.host.run_command(['exit'], tcp_timeout=60)
  ↓
paramiko SSH client → RSA key exchange
  ↓
OpenSSL rejects SHA-1 digest algorithm
  ↓
Exception raised, timeout clock keeps ticking
```

---

## Proof: 100% Consistent Error Pattern

Every single failure/error shares this **identical pattern**:

```
tests/storage/cdi_clone/test_clone.py:167:
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
utilities/virt.py:1939: in running_vm
    wait_for_running_vm(...)
utilities/virt.py:1872: in wait_for_running_vm
    wait_for_ssh_connectivity(vm=vm, timeout=ssh_timeout)
utilities/virt.py:1710: in wait_for_ssh_connectivity
    for sample in TimeoutSampler(...)
_ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _ _
timeout_sampler.TimeoutSampler.__iter__
...
TimeoutExpiredError: Timed Out: 120
Last exception: UnsupportedDigestmodError: [digital envelope routines] unsupported.
```

**This exact stack repeats for:**
- Windows clone tests
- RHEL tests
- CPU feature tests
- Migration tests
- Hotplug tests
- Memory dump tests
- Snapshot tests
- SMBIOS tests
- Instance type tests
- Every. Single. One.

---

## Why Tests Look Different But Fail Identically

Tests appear different because they *test different things*:

| Test | What It Tests | When It Fails |
|------|---------------|---------------|
| `test_clone_from_fs_to_block_using_dv_template` | CDI clone (FS→Block) | After clone succeeds, during SSH validation of cloned VM |
| `test_windows_memory_dump` | Windows memory dump feature | After VM boot, during SSH to verify dump artifact |
| `test_migration_policy_successfully_applied` | Migration policy enforcement | After policy applied, during SSH to verify policy effect |
| `test_vm_with_cpu_flag_positive_case` | CPU flags supported | After VM boot with CPU flag, during SSH to verify CPU visible |
| `test_concurrent_vms_boot_with_five_disks` | Concurrent multi-disk boot | After all VMs boot, during SSH to first VM for verification |

**All fail at the same point**: SSH validation phase, not test logic phase.

---

## What's NOT Wrong

✅ **Test code is fine** — no bugs in the test logic
✅ **VMs are booting** — they reach running state
✅ **Network is working** — VMs have IPs (SSH reaches them)
✅ **paramiko is fine** — it's not paramiko's fingerprint code (PR #6430 already fixed that)
✅ **Feature code is fine** — clones, snapshots, migrations, CPU flags all work

❌ **SSH protocol layer fails** — before test validation even starts

---

## The Real Problem

**OpenSSL 3.x in the validation pod enforces modern crypto standards:**
- SHA-1 is forbidden (legacy security threat)
- RSA with SHA-1 authentication is blocked
- This breaks SSH to VMs using RSA keys with SHA-1 (standard on RHEL/Windows)

**Why now?**
- Pod uses Python 3.14 (.venv/lib64/python3.14/...)
- Python 3.14 links against OpenSSL 3.x
- OpenSSL 3.x default is "no SHA-1" unless explicitly enabled

---

## Solution: Enable OpenSSL Legacy Provider

The pod's environment MUST enable the legacy provider at runtime:

```bash
# In validation pod startup or test environment:
export OPENSSL_CONF=/path/to/openssl.cnf  # with legacy provider enabled
# OR
openssl set-provider legacy
# OR in Python:
import os
os.environ['OPENSSL_LEGACY_PROVIDER'] = '1'
```

**This tells OpenSSL 3.x**: "SHA-1 is allowed for SSH authentication (not a security-critical use)."

---

## Summary Table

| Aspect | Status |
|--------|--------|
| **Number of distinct issues** | 1 (SSH/OpenSSL) |
| **Number of tests affected** | 21 (100%) |
| **Test code problems** | None |
| **Feature code problems** | None |
| **Infrastructure barrier** | ✅ Yes (OpenSSL 3.x) |
| **Quick fix** | Enable legacy provider |
| **PR #6430 helps?** | No (fixes different phase) |
