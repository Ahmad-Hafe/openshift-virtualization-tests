"""Constants for concurrent VM boot tests."""

NUM_CONCURRENT_VMS = 20
# Each VM gets 4 disks total: 1 boot volume (cloned from golden image) + 3 blank data volumes.
NUM_BLANK_DISKS_PER_VM = 3
BLANK_DV_SIZE = "1Gi"
