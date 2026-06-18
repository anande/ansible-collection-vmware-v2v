# anande.vmware_v2v Ansible Collection

Custom Ansible module for converting VMware (VxRail/vCenter) guests to KVM using `virt-v2v`, targeting libvirt storage pools backed by Red Hat Ceph RBD on RHEL KVM conversion hosts.

## Install

From Ansible Galaxy:

```bash
ansible-galaxy collection install anande.vmware_v2v
```

From this directory (development):

```bash
ansible-galaxy collection install -p ./collections .
export ANSIBLE_COLLECTIONS_PATHS="$(pwd)/collections:${ANSIBLE_COLLECTIONS_PATHS}"
```

Or add to `ansible.cfg`:

```ini
[defaults]
collections_paths = ./collections
```

## Architecture

```text
  vCenter / VxRail                    RHEL KVM conversion host
  (powered-off VM)                    (virt-v2v + libvirt + qemu-kvm)
        |                                      |
        |  VDDK read (443)                       |
        +--------------------------------------->|
        |                                      v
        |                              libvirt pool "vms"
        |                                      |
        |                                      v
        |                         Red Hat Ceph 9 RBD pool (rbd)
        +<------------------------- Ceph MON/OSD network
```

Conversion writes disks directly into an RBD-backed libvirt storage pool. The guest is registered in libvirt on the conversion host and can be started there or migrated to other KVM hosts that share the same Ceph pool.

## Conversion host prerequisites

Target platform: **RHEL 9.6+** (or RHEL 10) KVM hypervisor with access to a **Red Hat Ceph Storage 9** cluster.

### Packages

```bash
sudo dnf install -y virt-v2v libguestfs-tools qemu-kvm libvirt ceph-common
sudo systemctl enable --now libvirtd
```

### VMware VDDK

Install the VMware Virtual Disk Development Kit on the conversion host and note the library path (commonly `/usr/lib/vmware-vix-disklib`). VDDK transport is strongly recommended for large migrations.

### Red Hat Ceph 9 RBD pool for libvirt

On the conversion host, configure Ceph client access and a libvirt RBD storage pool. Example using a Ceph pool named `vms` and user `client.libvirt`:

```bash
# /etc/ceph/ceph.conf — use your Ceph 9 cluster MON addresses
sudo tee /etc/ceph/ceph.conf <<'EOF'
[global]
mon_host = 10.0.1.11,10.0.1.12,10.0.1.13
auth_client_required = cephx
auth_cluster_required = cephx
auth_service_required = cephx
EOF

sudo chmod 600 /etc/ceph/ceph.conf
sudo chown root:root /etc/ceph/ceph.conf

# Ceph keyring for libvirt (created on the Ceph cluster)
sudo tee /etc/ceph/ceph.client.libvirt.keyring <<'EOF'
[client.libvirt]
key = AQD...your-key...
caps mds = "allow r"
caps mon = "allow r"
caps osd = "allow class-read object_prefix rbd_children, allow rwx pool=vms"
EOF

sudo chmod 600 /etc/ceph/ceph.client.libvirt.keyring

# Verify RBD access before defining the libvirt pool
sudo rbd --id libvirt -m "$(awk -F= '/mon_host/{print $2}' /etc/ceph/ceph.conf)" ls vms
```

Define the libvirt storage pool (pool name `vms` matches the module default `libvirt_pool`):

```bash
sudo virsh pool-define /dev/stdin <<'EOF'
<pool type='rbd'>
  <name>vms</name>
  <source>
    <name>vms</name>
    <host name='10.0.1.11' port='6789'/>
    <host name='10.0.1.12' port='6789'/>
    <host name='10.0.1.13' port='6789'/>
    <auth type='ceph' username='client.libvirt'>
      <secret uuid='PUT-SECRET-UUID-HERE'/>
    </auth>
  </source>
</pool>
EOF

# Store the key in a libvirt secret, then start the pool
sudo virsh pool-start vms
sudo virsh pool-autostart vms
sudo virsh pool-info vms
```

Use `raw` disk format (the module default) for RBD-backed pools; `qcow2` on RBD is usually unnecessary.

### Network bridges

Map VMware port groups to Linux bridges on the conversion host before conversion, for example `br-tenant` and `br-mgmt`. The module passes mappings to `virt-v2v --network`.

### Other requirements

- Network access from the conversion host to vCenter (443) and Ceph MONs (6789)
- Target VMs must be **powered off** before conversion
- Sufficient local `/var/tmp` or `LIBGUESTFS_TMPDIR` space for virt-v2v scratch data

## Module

`anande.vmware_v2v.virt_v2v`

### Key parameters

| Parameter | Purpose |
|-----------|---------|
| `name` | VMware / libvirt guest name |
| `vcenter` | Nested dict: hostname, username, password, datacenter, compute_path, … |
| `vcenter_hostname` (aliases: `vcenter_fqdn`, `vcenter_host`) | vCenter FQDN |
| `vcenter_username` (alias: `vcenter_user`) | vCenter account |
| `vcenter_password` / `vcenter_password_file` | vCenter credentials for virt-v2v |
| `datacenter`, `compute_path` | Input URI path (`Datacenter/Cluster/esxi`) |
| `vddk` | Nested dict: libdir, thumbprint, transport |
| `vddk_libdir`, `vddk_thumbprint` | Fast VDDK transport |
| `libvirt` | Nested dict: uri, pool, output_format |
| `libvirt_pool` (alias: `pool`) | Target RBD-backed pool (default `vms`) |
| `networks` | `--network source:target` mappings |
| `force` | Re-convert even if domain exists |
| `timeout` | virt-v2v timeout in seconds (default 14400) |

Flat module options override nested dict values. Several settings can also be supplied via environment variables on the conversion host: `VCENTER_HOSTNAME`, `VCENTER_USERNAME`, `VCENTER_PASSWORD`, `VCENTER_PASSWORD_FILE`, `VCENTER_DATACENTER`, `VCENTER_COMPUTE_PATH`.

## Using variables

Three common patterns:

### 1. Nested dicts in `group_vars` (recommended for batch migrations)

Define shared connection and target settings once; the playbook only loops over guest names and network maps.

`group_vars/conversion_hosts.yml`:

```yaml
vcenter:
  hostname: vcenter.example.com
  username: "VCENTER.LOCAL\\migration"
  password: "{{ vault_vcenter_password }}"
  datacenter: Datacenter
  compute_path: Cluster1/esxi-01.example.com

vddk:
  libdir: /usr/lib/vmware-vix-disklib
  thumbprint: "{{ vcenter_thumbprint }}"

libvirt:
  pool: vms
  output_format: raw

migration_vms:
  - name: app-server-01
    networks:
      - src: "VM Network"
        dest: br-tenant
  - name: db-server-01
    networks:
      - src: "VM Network"
        dest: br-tenant
      - src: "Management"
        dest: br-mgmt
```

Playbook task:

```yaml
- anande.vmware_v2v.virt_v2v:
    name: "{{ item.name }}"
    networks: "{{ item.networks }}"
  loop: "{{ migration_vms }}"
```

The module merges `vcenter`, `vddk`, and `libvirt` from host/group vars automatically.

### 2. Flat variable aliases

Use names that match your existing inventory conventions:

```yaml
vcenter_fqdn: vcenter.example.com
vcenter_user: "VCENTER.LOCAL\\migration"
datacenter: Datacenter
cluster: Cluster1
esxi_host: esxi-01.example.com
libvirt_pool: vms
```

```yaml
- anande.vmware_v2v.virt_v2v:
    name: app-server-01
    vcenter_fqdn: "{{ vcenter_fqdn }}"
    vcenter_user: "{{ vcenter_user }}"
    vcenter_password: "{{ vault_vcenter_password }}"
    datacenter: "{{ datacenter }}"
    compute_path: "{{ cluster }}/{{ esxi_host }}"
    vddk_libdir: /usr/lib/vmware-vix-disklib
    vddk_thumbprint: "{{ vcenter_thumbprint }}"
    pool: "{{ libvirt_pool }}"
    networks:
      - src: "VM Network"
        dest: br-tenant
```

### 3. Environment variables on the conversion host

Useful when the same host runs ad hoc conversions outside Ansible:

```bash
export VCENTER_HOSTNAME=vcenter.example.com
export VCENTER_USERNAME='VCENTER.LOCAL\migration'
export VCENTER_PASSWORD_FILE=/run/virt-v2v/vcenter.password
export VCENTER_DATACENTER=Datacenter
export VCENTER_COMPUTE_PATH=Cluster1/esxi-01.example.com
```

```yaml
- anande.vmware_v2v.virt_v2v:
    name: app-server-01
    vddk:
      libdir: /usr/lib/vmware-vix-disklib
      thumbprint: "{{ vcenter_thumbprint }}"
    libvirt:
      pool: vms
    networks:
      - src: "VM Network"
        dest: br-tenant
```

## Examples

### Single VM — flat options

```yaml
- anande.vmware_v2v.virt_v2v:
    name: app-server-01
    vcenter_hostname: vcenter.example.com
    vcenter_username: "VCENTER.LOCAL\\migration"
    vcenter_password: "{{ vault_vcenter_password }}"
    datacenter: Datacenter
    compute_path: Cluster1/esxi-01.example.com
    vddk_libdir: /usr/lib/vmware-vix-disklib
    vddk_thumbprint: "AA:BB:CC:..."
    libvirt_pool: vms
    output_format: raw
    networks:
      - src: "VM Network"
        dest: br-tenant
```

### Batch migration to RHEL KVM on Ceph 9 RBD

Full playbook: [examples/convert_vm.yml](examples/convert_vm.yml)

Sample variables: [examples/group_vars/conversion_hosts.yml](examples/group_vars/conversion_hosts.yml)

Run on the conversion host:

```bash
ansible-galaxy collection install -p ./collections .
ansible-playbook -i conversion_host, -c local examples/convert_vm.yml -e @examples/vars/secrets.yml.example
```

Replace `secrets.yml.example` with a vault-encrypted file containing `vault_vcenter_password` and your thumbprint.

### Per-VM compute path override

When VMs live on different ESXi hosts, override `compute_path` in the loop item or pass it flat:

```yaml
migration_vms:
  - name: app-server-01
    compute_path: Cluster1/esxi-01.example.com
    networks:
      - src: "VM Network"
        dest: br-tenant
  - name: app-server-02
    compute_path: Cluster1/esxi-02.example.com
    networks:
      - src: "VM Network"
        dest: br-tenant

- anande.vmware_v2v.virt_v2v:
    name: "{{ item.name }}"
    compute_path: "{{ item.compute_path }}"
    networks: "{{ item.networks }}"
  loop: "{{ migration_vms }}"
```

### Preserve MAC addresses

```yaml
- anande.vmware_v2v.virt_v2v:
    name: app-server-01
    macs:
      - src: "00:50:56:01:02:03"
        dest: "00:50:56:01:02:03"
    networks:
      - src: "VM Network"
        dest: br-tenant
```

### Remove a converted domain

```yaml
- anande.vmware_v2v.virt_v2v:
    name: app-server-01
    state: absent
    force: true   # also remove RBD volumes from the pool
```

## Get vCenter thumbprint

Required for VDDK transport:

```bash
openssl s_client -connect vcenter.example.com:443 </dev/null 2>/dev/null \
  | openssl x509 -fingerprint -sha1 -noout -in /dev/stdin
```

## Idempotency

When `state=present` and the libvirt domain already exists, conversion is skipped unless `force=true`.

## Troubleshooting

| Symptom | Check |
|---------|-------|
| `virt-v2v not found` | Install `virt-v2v` / `libguestfs-tools` on the conversion host |
| RBD pool errors | `virsh pool-info vms`, `rbd --id libvirt ls vms`, Ceph keyring caps |
| VDDK failures | VDDK path, thumbprint, vCenter 443 reachability |
| Network not found after boot | Bridge names in `--network` mappings exist on the host (`ip link`) |
| Conversion timeout | Increase `timeout` (large VMs can exceed 4 hours) |

## Communication

* Join the Ansible forum and ask about this collection in the [Get Help](https://forum.ansible.com/c/help/6) category with the `vmware` tag.
* Open issues in the [GitHub issue tracker](https://github.com/anande/ansible-collection-vmware-v2v/issues).
* See the [Ansible communication guide](https://docs.ansible.com/ansible/latest/community/communication.html) for more ways to reach the community.

## Publishing and upstream inclusion

This collection is published to [Ansible Galaxy](https://galaxy.ansible.com/anande/vmware_v2v) as `anande.vmware_v2v`.

To request inclusion in the Ansible community package (`ansible` PyPI), open a [new collection review discussion](https://github.com/ansible-collections/ansible-inclusion/discussions/new?category=new-collection-reviews) in [ansible-collections/ansible-inclusion](https://github.com/ansible-collections/ansible-inclusion) after the collection meets the [collection requirements checklist](https://github.com/ansible-collections/ansible-inclusion/blob/main/collection_checklist.md).

Maintainers: build and publish a release with:

```bash
ansible-galaxy collection build
ansible-galaxy collection publish anande-vmware_v2v-*.tar.gz --token "$ANSIBLE_GALAXY_API_KEY"
git tag v1.0.0 && git push origin v1.0.0
```

## References

- [Red Hat virt-v2v VMware guide](https://access.redhat.com/articles/1353223)
- [virt-v2v man page](https://libguestfs.org/virt-v2v.1.html)
- [Red Hat Ceph Storage 9 — RBD libvirt integration](https://docs.redhat.com/en/documentation/red_hat_ceph_storage/9)
