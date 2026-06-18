#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: Contributors
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

DOCUMENTATION = r"""
---
module: virt_v2v
short_description: Convert VMware guests to KVM using virt-v2v
description:
  - Wraps the C(virt-v2v) command to convert powered-off VMware guests into libvirt-managed KVM domains.
  - Targets RHEL KVM conversion hosts writing disks into libvirt storage pools backed by Red Hat Ceph RBD.
  - When O(state=present) and the libvirt domain already exists, conversion is skipped unless O(force=true).
  - VMware guests must be powered off before conversion; use M(community.vmware.vmware_guest_powerstate) in the same play.
  - Connection and target settings can be supplied as flat module options, nested dicts
    (O(vcenter), O(vddk), O(libvirt)), or environment variables on the conversion host.
author:
  - Anand Nande (@anande)
requirements:
  - The below requirements are needed on the host that executes this module (the RHEL KVM conversion host).
  - virt-v2v
  - virsh
  - libvirt
  - libguestfs (pulled in by virt-v2v)
  - VMware VDDK installed on the conversion host when O(input_transport=vddk) (recommended).
  - A configured libvirt storage pool (for example an RBD-backed C(vms) pool on Red Hat Ceph Storage 9).
options:
  name:
    description:
      - Name of the VMware guest to convert.
      - Also used as the libvirt domain name after a successful conversion.
      - Passed as the final argument to C(virt-v2v).
    type: str
    required: true
  state:
    description:
      - V(present) converts the guest when it does not already exist in libvirt.
      - V(absent) undefines the libvirt domain with C(virsh undefine).
      - When V(absent), vCenter and virt-v2v input options are not required.
    type: str
    choices: [present, absent]
    default: present
  vcenter:
    description:
      - Nested vCenter connection settings.
      - Values from this dict are applied when the matching flat option is omitted.
      - Useful in C(group_vars) or C(host_vars) so playbooks only pass O(name) and per-VM overrides.
      - Flat module options always override values from O(vcenter).
    type: dict
    suboptions:
      hostname:
        description:
          - VMware vCenter or ESXi hostname or IP.
          - Maps to O(vcenter_hostname).
        type: str
      username:
        description:
          - VMware username for the input URI.
          - Use C(DOMAIN\\user) form for Active Directory-backed accounts.
          - Maps to O(vcenter_username).
        type: str
      password:
        description:
          - VMware password passed to C(virt-v2v -ip).
          - Maps to O(vcenter_password).
        type: str
      password_file:
        description:
          - Path to a file containing the VMware password for C(virt-v2v -ip).
          - Maps to O(vcenter_password_file).
        type: path
      datacenter:
        description:
          - vCenter datacenter name used in the C(vpx://) input URI path.
          - Maps to O(datacenter).
        type: str
      compute_path:
        description:
          - Cluster or ESXi host path segment after the datacenter in the input URI.
          - Example C(esxi-01.example.com) or C(Cluster1/esxi-01.example.com).
          - Maps to O(compute_path).
        type: str
      verify_ssl:
        description:
          - Verify the vCenter TLS certificate.
          - Maps to O(vcenter_verify_ssl).
        type: bool
  vcenter_hostname:
    description:
      - VMware vCenter or ESXi hostname or IP used in the C(vpx://) input URI.
      - Required when O(state=present) unless supplied via O(vcenter) or C(VCENTER_HOSTNAME).
    type: str
    aliases: [vcenter_host, vcenter_fqdn]
  vcenter_username:
    description:
      - VMware username for the input URI.
      - Backslashes in domain accounts are URL-encoded in the URI (C(\\) becomes C(%5c)).
      - Required when O(state=present) unless supplied via O(vcenter) or C(VCENTER_USERNAME).
    type: str
    aliases: [vcenter_user]
  vcenter_password:
    description:
      - VMware password for C(virt-v2v -ip).
      - Written to a temporary file when O(vcenter_password_file) is not set; the file is removed after conversion.
      - Mutually exclusive with O(vcenter_password_file).
      - One of O(vcenter_password) or O(vcenter_password_file) is required when O(state=present).
    type: str
  vcenter_password_file:
    description:
      - Path to a file containing the VMware password for C(virt-v2v -ip).
      - Preferred over O(vcenter_password) for batch migrations on shared conversion hosts.
      - Mutually exclusive with O(vcenter_password).
    type: path
  datacenter:
    description:
      - vCenter datacenter name used in the C(vpx://) input URI path.
      - Required when O(state=present) unless supplied via O(vcenter) or C(VCENTER_DATACENTER).
    type: str
  compute_path:
    description:
      - Cluster or ESXi host path segment after the datacenter in the input URI.
      - Example C(esxi-01.example.com) for a standalone host or C(Cluster1/esxi-01.example.com) for a cluster member.
      - Required when O(state=present) unless supplied via O(vcenter) or C(VCENTER_COMPUTE_PATH).
    type: str
  vcenter_verify_ssl:
    description:
      - Verify the vCenter TLS certificate when building the input URI.
      - When V(false), C(?no_verify=1) is appended to the URI (the module default).
    type: bool
    default: false
  vddk:
    description:
      - Nested VMware VDDK transport settings.
      - Values from this dict are applied when the matching flat option is omitted.
      - Flat module options always override values from O(vddk).
    type: dict
    suboptions:
      transport:
        description:
          - Input transport passed to C(virt-v2v -it).
          - Maps to O(input_transport).
        type: str
        choices: [vddk, vpx]
      libdir:
        description:
          - Directory containing the VMware VDDK libraries.
          - Passed as C(vddk-libdir=...) to C(virt-v2v -io).
          - Maps to O(vddk_libdir).
        type: path
      thumbprint:
        description:
          - SHA-1 TLS thumbprint of the vCenter or ESXi endpoint.
          - Passed as C(vddk-thumbprint=...) to C(virt-v2v -io).
          - Maps to O(vddk_thumbprint).
        type: str
  input_transport:
    description:
      - Input transport for reading the source VM.
      - V(vddk) uses the VMware Virtual Disk Development Kit (recommended for production migrations).
      - V(vpx) uses the VPX API transport and does not require VDDK libraries.
      - Passed to C(virt-v2v -it).
    type: str
    choices: [vddk, vpx]
    default: vddk
  vddk_libdir:
    description:
      - Directory containing the VMware VDDK libraries (commonly C(/usr/lib/vmware-vix-disklib)).
      - Required when O(input_transport=vddk).
      - Passed to C(virt-v2v -io vddk-libdir=...).
    type: path
  vddk_thumbprint:
    description:
      - SHA-1 TLS thumbprint of the vCenter or ESXi endpoint.
      - Required when O(input_transport=vddk).
      - Obtain with C(openssl s_client) against vCenter port 443.
      - Passed to C(virt-v2v -io vddk-thumbprint=...).
    type: str
  libvirt:
    description:
      - Nested libvirt target settings for the converted guest.
      - Values from this dict are applied when the matching flat option is omitted.
      - Flat module options always override values from O(libvirt).
    type: dict
    suboptions:
      uri:
        description:
          - libvirt connection URI used for idempotency checks and C(virt-v2v -o libvirt).
          - Maps to O(libvirt_uri).
        type: str
      pool:
        description:
          - Target libvirt storage pool name.
          - Maps to O(libvirt_pool).
        type: str
      output_format:
        description:
          - Disk format for converted images.
          - Maps to O(output_format).
        type: str
        choices: [raw, qcow2]
  libvirt_uri:
    description:
      - libvirt connection URI used for C(virsh dominfo) idempotency checks and C(virt-v2v -o libvirt).
      - Also used by C(virsh undefine) when O(state=absent).
    type: str
    default: qemu:///system
  libvirt_pool:
    description:
      - Target libvirt storage pool name, typically an RBD-backed pool such as C(vms) on Red Hat Ceph Storage 9.
      - Passed to C(virt-v2v -os) and C(-oo pool=...).
      - Use V(raw) output format for RBD-backed pools.
    type: str
    default: vms
    aliases: [pool]
  output_format:
    description:
      - Disk format for converted images, passed to C(virt-v2v -of).
      - V(raw) is recommended for RBD-backed libvirt pools.
    type: str
    choices: [raw, qcow2]
    default: raw
  networks:
    description:
      - Network mappings passed to C(virt-v2v --network).
      - Maps VMware port groups or network names to Linux bridge or libvirt network names on the conversion host.
      - Each list item is a string in C(source:target) form, or a dict with C(src)/C(source) and C(dest)/C(target) keys.
    type: list
    elements: raw
    default: []
  bridges:
    description:
      - Bridge mappings passed to C(virt-v2v --bridge).
      - Each list item is a string in C(source:target) form, or a dict with C(src)/C(source) and C(dest)/C(target) keys.
    type: list
    elements: raw
    default: []
  macs:
    description:
      - MAC address mappings passed to C(virt-v2v --mac).
      - Use to preserve guest MAC addresses after conversion.
      - Each list item is a string in C(source:target) form, or a dict with C(src)/C(source) and C(dest)/C(target) keys.
    type: list
    elements: raw
    default: []
  extra_args:
    description:
      - Additional arguments appended to the C(virt-v2v) command before the guest name.
      - Use for options not wrapped by this module.
    type: list
    elements: str
    default: []
  force:
    description:
      - When O(state=present), re-run conversion even if the libvirt domain already exists.
      - When O(state=absent), pass C(--remove-all-storage) to C(virsh undefine) and delete pool volumes (including RBD images).
      - Setting O(force=true) for conversion is destructive and overwrites an existing domain definition.
    type: bool
    default: false
  timeout:
    description:
      - Maximum seconds to wait for C(virt-v2v) to complete.
      - Large multi-disk guests on busy Ceph clusters may require several hours; increase as needed.
    type: int
    default: 14400
  libguestfs_backend:
    description:
      - Value exported as C(LIBGUESTFS_BACKEND) when running C(virt-v2v).
      - V(direct) runs QEMU directly and is the usual setting on RHEL KVM conversion hosts.
    type: str
    default: direct
  virt_v2v_path:
    description: Path to the C(virt-v2v) binary.
    type: path
    default: virt-v2v
attributes:
  check_mode:
    description:
      - Can run in C(check_mode) and return changed status prediction without modifying target.
    support: none
  diff_mode:
    description:
      - Will return details on what has changed when run with C(--diff).
    support: none
  platform:
    description:
      - Target OS/families that can be operated against.
    support: partial
    platforms:
      - Red Hat Enterprise Linux 9
      - Red Hat Enterprise Linux 10
notes:
  - >-
    This module must run on the RHEL KVM conversion host (typically with C(connection=local)),
    not on the Ansible control node unless it is also the conversion host.
  - Flat module options override nested O(vcenter)/O(vddk)/O(libvirt) dict values.
  - When used with C(loop:), each guest is converted individually.
  - >-
    Put shared settings in O(vcenter), O(vddk), and O(libvirt) via C(group_vars) so loop items
    only carry O(name) and network mappings.
  - >-
    O(vcenter_hostname), O(vcenter_username), O(datacenter), and O(compute_path) can also be set
    with the C(VCENTER_HOSTNAME), C(VCENTER_USERNAME), C(VCENTER_DATACENTER), and
    C(VCENTER_COMPUTE_PATH) environment variables.
  - >-
    O(vcenter_password) and O(vcenter_password_file) can be set with C(VCENTER_PASSWORD) and
    C(VCENTER_PASSWORD_FILE) respectively.
  - The source VMware guest must be powered off before conversion. Running C(virt-v2v) against a powered-on guest fails or produces inconsistent results.
  - For RBD-backed libvirt pools on Red Hat Ceph Storage 9, verify pool access with C(virsh pool-info) and C(rbd ls) before running conversions.
  - VDDK transport requires network access from the conversion host to vCenter on TCP 443 and a valid O(vddk_thumbprint).
  - See U(https://libguestfs.org/virt-v2v.1.html) and U(https://access.redhat.com/articles/1353223) for virt-v2v references.
  - See U(https://docs.redhat.com/en/documentation/red_hat_ceph_storage/9) for Red Hat Ceph Storage 9 documentation.
seealso:
  - module: community.vmware.vmware_guest_powerstate
    description: Power off VMware guests before conversion.
"""

EXAMPLES = r"""
- name: Convert a powered-off VMware guest to an RBD-backed libvirt pool (state=present is optional)
  anande.vmware_v2v.virt_v2v:
    name: app-server-01
    vcenter_hostname: vcenter.example.com
    vcenter_username: "VCENTER.LOCAL\\migration"
    vcenter_password: "{{ vault_vcenter_password }}"
    datacenter: Datacenter
    compute_path: Cluster1/esxi-01.example.com
    vddk_libdir: /usr/lib/vmware-vix-disklib
    vddk_thumbprint: "AA:BB:CC:DD:EE:FF:00:11:22:33:44:55:66:77:88:99:AA:BB:CC:DD"
    libvirt_pool: vms
    networks:
      - src: "VM Network"
        dest: br-tenant

- name: Convert with raw disks to a Red Hat Ceph 9 RBD libvirt pool on RHEL KVM
  anande.vmware_v2v.virt_v2v:
    name: db-server-01
    vcenter_hostname: vcenter.example.com
    vcenter_username: "VCENTER.LOCAL\\migration"
    vcenter_password: "{{ vault_vcenter_password }}"
    datacenter: Datacenter
    compute_path: Cluster1/esxi-02.example.com
    vddk_libdir: /usr/lib/vmware-vix-disklib
    vddk_thumbprint: "{{ vcenter_thumbprint }}"
    libvirt_pool: vms
    output_format: raw
    networks:
      - src: "VM Network"
        dest: br-tenant
      - src: "Management"
        dest: br-mgmt

- name: Undefine a converted libvirt domain
  anande.vmware_v2v.virt_v2v:
    name: app-server-01
    state: absent

- name: Undefine a domain and remove RBD volumes from the libvirt pool
  anande.vmware_v2v.virt_v2v:
    name: app-server-01
    state: absent
    force: true

- name: Convert a batch of guests with shared settings in group_vars (loop passes only per-VM values)
  anande.vmware_v2v.virt_v2v:
    name: "{{ item.name }}"
    networks: "{{ item.networks }}"
  loop: "{{ migration_vms }}"

- name: Convert using nested vcenter/vddk/libvirt dicts inline
  anande.vmware_v2v.virt_v2v:
    name: app-server-01
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
    networks:
      - "VM Network:br-tenant"

- name: Convert using variable aliases from group_vars
  anande.vmware_v2v.virt_v2v:
    name: app-server-01
    vcenter_fqdn: "{{ vcenter_fqdn }}"
    vcenter_user: "{{ vcenter_user }}"
    vcenter_password_file: /run/virt-v2v/vcenter.password
    datacenter: "{{ datacenter }}"
    compute_path: "{{ cluster }}/{{ esxi_host }}"
    pool: "{{ libvirt_pool }}"
    networks: "{{ app_networks }}"

- name: Override compute_path per guest when VMs span multiple ESXi hosts
  anande.vmware_v2v.virt_v2v:
    name: "{{ item.name }}"
    compute_path: "{{ item.compute_path }}"
    networks: "{{ item.networks }}"
  loop: "{{ migration_vms }}"

- name: Preserve MAC addresses during conversion
  anande.vmware_v2v.virt_v2v:
    name: app-server-01
    vcenter_hostname: vcenter.example.com
    vcenter_username: "VCENTER.LOCAL\\migration"
    vcenter_password: "{{ vault_vcenter_password }}"
    datacenter: Datacenter
    compute_path: Cluster1/esxi-01.example.com
    vddk_libdir: /usr/lib/vmware-vix-disklib
    vddk_thumbprint: "{{ vcenter_thumbprint }}"
    libvirt_pool: vms
    macs:
      - src: "00:50:56:01:02:03"
        dest: "00:50:56:01:02:03"
    networks:
      - src: "VM Network"
        dest: br-tenant

- name: Re-convert a guest even when the libvirt domain already exists
  anande.vmware_v2v.virt_v2v:
    name: app-server-01
    vcenter_hostname: vcenter.example.com
    vcenter_username: "VCENTER.LOCAL\\migration"
    vcenter_password: "{{ vault_vcenter_password }}"
    datacenter: Datacenter
    compute_path: Cluster1/esxi-01.example.com
    vddk_libdir: /usr/lib/vmware-vix-disklib
    vddk_thumbprint: "{{ vcenter_thumbprint }}"
    libvirt_pool: vms
    force: true

- name: Convert using VPX transport when VDDK is not installed
  anande.vmware_v2v.virt_v2v:
    name: app-server-01
    vcenter_hostname: vcenter.example.com
    vcenter_username: "VCENTER.LOCAL\\migration"
    vcenter_password: "{{ vault_vcenter_password }}"
    datacenter: Datacenter
    compute_path: Cluster1/esxi-01.example.com
    input_transport: vpx
    libvirt_pool: vms
    networks:
      - src: "VM Network"
        dest: br-tenant

- name: Increase conversion timeout for a large multi-disk guest
  anande.vmware_v2v.virt_v2v:
    name: large-file-server
    vcenter_hostname: vcenter.example.com
    vcenter_username: "VCENTER.LOCAL\\migration"
    vcenter_password: "{{ vault_vcenter_password }}"
    datacenter: Datacenter
    compute_path: Cluster1/esxi-01.example.com
    vddk_libdir: /usr/lib/vmware-vix-disklib
    vddk_thumbprint: "{{ vcenter_thumbprint }}"
    libvirt_pool: vms
    timeout: 28800
    networks:
      - src: "VM Network"
        dest: br-tenant

- name: Pass additional virt-v2v arguments not wrapped by the module
  anande.vmware_v2v.virt_v2v:
    name: app-server-01
    vcenter_hostname: vcenter.example.com
    vcenter_username: "VCENTER.LOCAL\\migration"
    vcenter_password: "{{ vault_vcenter_password }}"
    datacenter: Datacenter
    compute_path: Cluster1/esxi-01.example.com
    vddk_libdir: /usr/lib/vmware-vix-disklib
    vddk_thumbprint: "{{ vcenter_thumbprint }}"
    libvirt_pool: vms
    extra_args:
      - --root
      - /dev/sda2
    networks:
      - src: "VM Network"
        dest: br-tenant
"""

RETURN = r"""
changed:
  description: Whether conversion or undefine was performed.
  type: bool
  returned: always
  sample: true
cmd:
  description: Command executed by the module. The password file path after C(-ip) is redacted.
  type: list
  returned: when O(state=present) and conversion ran or failed
  sample:
    - virt-v2v
    - -ic
    - vpx://VCENTER.LOCAL%5cmigration@vcenter.example.com/Datacenter/Cluster1/esxi-01.example.com?no_verify=1
    - -ip
    - '***'
    - -o
    - libvirt
    - -os
    - vms
    - app-server-01
stdout:
  description: Standard output from C(virt-v2v).
  type: str
  returned: when O(state=present) and conversion ran or failed
  sample: |
    virt-v2v: app-server-01 was copied to the libvirt hypervisor
stderr:
  description: Standard error from C(virt-v2v) or C(virsh).
  type: str
  returned: when O(state=present) and conversion ran or failed, or when O(state=absent) and undefine ran
  sample: ''
domain:
  description: Libvirt domain name affected by the task.
  type: str
  returned: always
  sample: app-server-01
skipped:
  description: True when conversion was skipped because the libvirt domain already exists and O(force=false).
  type: bool
  returned: when O(state=present)
  sample: false
msg:
  description: Human-readable status when the task made no change.
  type: str
  returned: when O(state=present) and conversion was skipped, or when O(state=absent) and the domain did not exist
  sample: libvirt domain already exists; conversion skipped
"""

import os
import shutil
import tempfile

from ansible.module_utils.basic import AnsibleModule, env_fallback


NESTED_VCENTER_MAP = {
    "hostname": "vcenter_hostname",
    "username": "vcenter_username",
    "password": "vcenter_password",
    "password_file": "vcenter_password_file",
    "datacenter": "datacenter",
    "compute_path": "compute_path",
    "verify_ssl": "vcenter_verify_ssl",
}

NESTED_VDDK_MAP = {
    "transport": "input_transport",
    "libdir": "vddk_libdir",
    "thumbprint": "vddk_thumbprint",
}

NESTED_LIBVIRT_MAP = {
    "uri": "libvirt_uri",
    "pool": "libvirt_pool",
    "output_format": "output_format",
}

MODULE_DEFAULTS = {
    "vcenter_verify_ssl": False,
    "input_transport": "vddk",
    "libvirt_uri": "qemu:///system",
    "libvirt_pool": "vms",
    "output_format": "raw",
}


def _merge_nested_dict(params, nested_key, field_map):
    nested = params.get(nested_key) or {}
    if not isinstance(nested, dict):
        return nested
    for nested_field, flat_key in field_map.items():
        nested_value = nested.get(nested_field)
        if nested_value is None:
            continue
        current = params.get(flat_key)
        default_value = MODULE_DEFAULTS.get(flat_key)
        if current is None or (default_value is not None and current == default_value):
            params[flat_key] = nested_value
    return None


def _resolve_params(module):
    params = module.params
    bad_nested = _merge_nested_dict(params, "vcenter", NESTED_VCENTER_MAP)
    if bad_nested is not None:
        module.fail_json(msg="vcenter must be a dictionary")
    bad_nested = _merge_nested_dict(params, "vddk", NESTED_VDDK_MAP)
    if bad_nested is not None:
        module.fail_json(msg="vddk must be a dictionary")
    bad_nested = _merge_nested_dict(params, "libvirt", NESTED_LIBVIRT_MAP)
    if bad_nested is not None:
        module.fail_json(msg="libvirt must be a dictionary")


def _validate_present_params(module):
    missing = []
    for key in ("vcenter_hostname", "vcenter_username", "datacenter", "compute_path"):
        if not module.params.get(key):
            missing.append(key)
    if missing:
        module.fail_json(
            msg="Missing required conversion settings: {0}. "
            "Set flat options, nested vcenter/vddk/libvirt dicts, or environment variables.".format(
                ", ".join(missing)
            )
        )
    if not module.params.get("vcenter_password") and not module.params.get("vcenter_password_file"):
        module.fail_json(
            msg="vcenter_password or vcenter_password_file is required for conversion"
        )


def _format_mapping(item):
    if isinstance(item, dict):
        src = item.get("src") or item.get("source")
        dest = item.get("dest") or item.get("target")
        if not src:
            raise ValueError("mapping dict requires src or source")
        if dest:
            return "{0}:{1}".format(src, dest)
        return src
    return str(item)


def _quote_uri_user(username):
    return username.replace("\\", "%5c")


def _build_input_uri(module):
    username = _quote_uri_user(module.params["vcenter_username"])
    host = module.params["vcenter_hostname"]
    datacenter = module.params["datacenter"]
    compute_path = module.params["compute_path"].strip("/")
    query = "" if module.params["vcenter_verify_ssl"] else "?no_verify=1"
    return "vpx://{user}@{host}/{dc}/{compute}{query}".format(
        user=username,
        host=host,
        dc=datacenter,
        compute=compute_path,
        query=query,
    )


def _virt_v2v_present(module):
    name = module.params["name"]
    uri = module.params["libvirt_uri"]

    if not shutil.which(module.params["virt_v2v_path"]):
        module.fail_json(msg="virt-v2v not found in PATH")
    if not shutil.which("virsh"):
        module.fail_json(msg="virsh not found in PATH")

    rc, dominfo_out, dominfo_err = module.run_command(["virsh", "-c", uri, "dominfo", name], check_rc=False)
    if rc == 0 and not module.params["force"]:
        return {
            "changed": False,
            "domain": name,
            "skipped": True,
            "msg": "libvirt domain already exists; conversion skipped",
        }

    password_file = module.params["vcenter_password_file"]
    temp_password_file = None
    if not password_file:
        handle, temp_password_file = tempfile.mkstemp(prefix="virt-v2v-", text=True)
        os.close(handle)
        with open(temp_password_file, "w") as password_handle:
            password_handle.write(module.params["vcenter_password"])
        password_file = temp_password_file

    argv = [
        module.params["virt_v2v_path"],
        "-ic",
        _build_input_uri(module),
        "-ip",
        password_file,
        "-o",
        "libvirt",
        "-os",
        module.params["libvirt_pool"],
        "-oo",
        "pool={0}".format(module.params["libvirt_pool"]),
        "-of",
        module.params["output_format"],
    ]

    if module.params["input_transport"] == "vddk":
        if not module.params["vddk_libdir"]:
            module.fail_json(msg="vddk_libdir is required when input_transport=vddk")
        if not module.params["vddk_thumbprint"]:
            module.fail_json(msg="vddk_thumbprint is required when input_transport=vddk")
        argv.extend(["-it", "vddk"])
        argv.extend(["-io", "vddk-libdir={0}".format(module.params["vddk_libdir"])])
        argv.extend(["-io", "vddk-thumbprint={0}".format(module.params["vddk_thumbprint"])])
    else:
        argv.extend(["-it", "vpx"])

    for option, values in (
        ("--network", module.params["networks"]),
        ("--bridge", module.params["bridges"]),
        ("--mac", module.params["macs"]),
    ):
        for value in values:
            try:
                argv.extend([option, _format_mapping(value)])
            except ValueError as exc:
                module.fail_json(msg=str(exc))

    argv.extend(module.params["extra_args"])
    argv.append(name)

    env = os.environ.copy()
    env["LIBGUESTFS_BACKEND"] = module.params["libguestfs_backend"]

    try:
        rc, stdout, stderr = module.run_command(
            argv,
            environ_update=env,
            timeout=module.params["timeout"],
        )
    finally:
        if temp_password_file:
            try:
                os.remove(temp_password_file)
            except OSError:
                pass

    redacted_cmd = []
    skip_next = False
    for arg in argv:
        if skip_next:
            redacted_cmd.append("***")
            skip_next = False
            continue
        if arg == "-ip":
            redacted_cmd.append(arg)
            skip_next = True
            continue
        redacted_cmd.append(arg)

    if rc != 0:
        module.fail_json(
            msg="virt-v2v failed with return code {0}".format(rc),
            cmd=redacted_cmd,
            stdout=stdout,
            stderr=stderr,
            domain=name,
        )

    rc, dominfo_out, stderr = module.run_command(["virsh", "-c", uri, "dominfo", name], check_rc=False)
    if rc != 0:
        module.fail_json(
            msg="virt-v2v completed but libvirt domain was not found",
            cmd=redacted_cmd,
            stdout=stdout,
            stderr=stderr,
            domain=name,
        )

    return {
        "changed": True,
        "domain": name,
        "skipped": False,
        "cmd": redacted_cmd,
        "stdout": stdout,
        "stderr": stderr,
    }


def _virt_v2v_absent(module):
    name = module.params["name"]
    uri = module.params["libvirt_uri"]

    if not shutil.which("virsh"):
        module.fail_json(msg="virsh not found in PATH")

    rc, dominfo_out, dominfo_err = module.run_command(["virsh", "-c", uri, "dominfo", name], check_rc=False)
    if rc != 0:
        return {"changed": False, "domain": name, "msg": "libvirt domain does not exist"}

    undefine_argv = ["virsh", "-c", uri, "undefine", name]
    if module.params["force"]:
        undefine_argv.append("--remove-all-storage")

    rc, stdout, stderr = module.run_command(undefine_argv, check_rc=False)
    if rc != 0:
        module.fail_json(
            msg="failed to undefine libvirt domain {0}".format(name),
            stdout=stdout,
            stderr=stderr,
            domain=name,
        )

    return {
        "changed": True,
        "domain": name,
        "stdout": stdout,
        "stderr": stderr,
    }


def main():
    module = AnsibleModule(
        argument_spec=dict(
            name=dict(type="str", required=True),
            state=dict(type="str", default="present", choices=["present", "absent"]),
            vcenter=dict(
                type="dict",
                options=dict(
                    hostname=dict(type="str"),
                    username=dict(type="str"),
                    password=dict(type="str", no_log=True),
                    password_file=dict(type="path"),
                    datacenter=dict(type="str"),
                    compute_path=dict(type="str"),
                    verify_ssl=dict(type="bool"),
                ),
            ),
            vcenter_hostname=dict(
                type="str",
                aliases=["vcenter_host", "vcenter_fqdn"],
                fallback=(env_fallback, ["VCENTER_HOSTNAME", "VCENTER_HOST"]),
            ),
            vcenter_username=dict(
                type="str",
                aliases=["vcenter_user"],
                fallback=(env_fallback, ["VCENTER_USERNAME"]),
            ),
            vcenter_password=dict(
                type="str",
                no_log=True,
                fallback=(env_fallback, ["VCENTER_PASSWORD"]),
            ),
            vcenter_password_file=dict(
                type="path",
                fallback=(env_fallback, ["VCENTER_PASSWORD_FILE"]),
            ),
            datacenter=dict(
                type="str",
                fallback=(env_fallback, ["VCENTER_DATACENTER"]),
            ),
            compute_path=dict(
                type="str",
                fallback=(env_fallback, ["VCENTER_COMPUTE_PATH"]),
            ),
            vcenter_verify_ssl=dict(type="bool", default=False),
            vddk=dict(
                type="dict",
                options=dict(
                    transport=dict(type="str", choices=["vddk", "vpx"]),
                    libdir=dict(type="path"),
                    thumbprint=dict(type="str"),
                ),
            ),
            input_transport=dict(type="str", default="vddk", choices=["vddk", "vpx"]),
            vddk_libdir=dict(type="path"),
            vddk_thumbprint=dict(type="str"),
            libvirt=dict(
                type="dict",
                options=dict(
                    uri=dict(type="str"),
                    pool=dict(type="str"),
                    output_format=dict(type="str", choices=["raw", "qcow2"]),
                ),
            ),
            libvirt_uri=dict(type="str", default="qemu:///system"),
            libvirt_pool=dict(type="str", default="vms", aliases=["pool"]),
            output_format=dict(type="str", default="raw", choices=["raw", "qcow2"]),
            networks=dict(type="list", elements="raw", default=[]),
            bridges=dict(type="list", elements="raw", default=[]),
            macs=dict(type="list", elements="raw", default=[]),
            extra_args=dict(type="list", elements="str", default=[]),
            force=dict(type="bool", default=False),
            timeout=dict(type="int", default=14400),
            libguestfs_backend=dict(type="str", default="direct"),
            virt_v2v_path=dict(type="path", default="virt-v2v"),
        ),
        supports_check_mode=False,
        mutually_exclusive=[["vcenter_password", "vcenter_password_file"]],
    )

    _resolve_params(module)

    if module.params["state"] == "present":
        _validate_present_params(module)
        result = _virt_v2v_present(module)
    else:
        result = _virt_v2v_absent(module)

    module.exit_json(**result)


if __name__ == "__main__":
    main()
