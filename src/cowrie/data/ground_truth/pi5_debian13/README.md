# Pi 5 / Debian 13 (trixie) ground truth blobs

Text captures used when ` [shell] ground_truth = pi5_debian13` in `etc/cowrie.cfg`.

**Regenerate on a reference system** (as root or the target user, from this repo’s root):

```bash
OUT=src/cowrie/data/ground_truth/pi5_debian13
mkdir -p "$OUT"
{
  hostname; uname -a; uname -r; uname -i; uname -m; uname -p
} > "$OUT/hostname_uname.txt"
cat /etc/os-release > "$OUT/os-release.txt"
cat /etc/debian_version > "$OUT/debian_version.txt"
lsb_release -a > "$OUT/lsb_release_a.txt" 2>&1
hostnamectl > "$OUT/hostnamectl.txt" 2>&1
vcgencmd version > "$OUT/vcgencmd_version.txt" 2>&1
vcgencmd measure_temp > "$OUT/vcgencmd_temp.txt" 2>&1
cat /proc/cpuinfo > "$OUT/proc_cpuinfo.txt"
cat /proc/meminfo > "$OUT/proc_meminfo.txt"
cat /proc/version > "$OUT/proc_version.txt"
lscpu > "$OUT/lscpu.txt" 2>&1
ip addr show > "$OUT/ip_addr_show.txt" 2>&1
ip link show > "$OUT/ip_link_show.txt" 2>&1
ip route show > "$OUT/ip_route_show.txt" 2>&1
ifconfig -a > "$OUT/ifconfig_a.txt" 2>&1
cat /proc/net/dev > "$OUT/proc_net_dev.txt" 2>&1
ss -tulnp > "$OUT/ss_tulnp.txt" 2>&1
netstat -rn > "$OUT/netstat_rn.txt" 2>&1
ps aux > "$OUT/ps_aux.txt" 2>&1
ps -ef > "$OUT/ps_ef.txt" 2>&1
top -bn1 > "$OUT/top_bn1.txt" 2>&1
systemctl list-units --type=service --state=running > "$OUT/systemctl_running.txt" 2>&1
service --status-all > "$OUT/service_status_all.txt" 2>&1
cat /etc/passwd > "$OUT/passwd.txt"
cat /etc/group > "$OUT/group.txt"
id pi > "$OUT/id_pi.txt" 2>&1
# … plus error-case captures (insmod, make kernel modules, wget flag, etc.)
```

DHCP- and time-varying fields (IPs, load, PIDs) are snapshots: refresh these files if you need a new baseline.

A single transcript can also be split into this directory or kept alongside as `~/cowrie-capture-YYYY-MM-DD.txt` for audit.
