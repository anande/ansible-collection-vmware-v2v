# Copyright: Contributors
# GNU General Public License v3.0+ (see LICENSE or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type

import pytest

from ansible_collections.anande.vmware_v2v.plugins.modules import virt_v2v


@pytest.mark.parametrize(
    "item,expected",
    [
        ("VM Network:br-tenant", "VM Network:br-tenant"),
        ({"src": "VM Network", "dest": "br-tenant"}, "VM Network:br-tenant"),
        ({"source": "VM Network", "target": "br-tenant"}, "VM Network:br-tenant"),
        ({"src": "VM Network"}, "VM Network"),
    ],
)
def test_format_mapping(item, expected):
    assert virt_v2v._format_mapping(item) == expected


def test_format_mapping_requires_source():
    with pytest.raises(ValueError, match="mapping dict requires src or source"):
        virt_v2v._format_mapping({"dest": "br-tenant"})


def test_quote_uri_user():
    assert virt_v2v._quote_uri_user(r"VCENTER.LOCAL\migration") == r"VCENTER.LOCAL%5cmigration"


def test_build_input_uri():
    params = {
        "vcenter_username": r"VCENTER.LOCAL\migration",
        "vcenter_hostname": "vcenter.example.com",
        "datacenter": "Datacenter",
        "compute_path": "Cluster1/esxi-01.example.com",
        "vcenter_verify_ssl": False,
    }
    module = type("Module", (), {"params": params})()
    uri = virt_v2v._build_input_uri(module)
    assert uri == (
        "vpx://VCENTER.LOCAL%5cmigration@vcenter.example.com/"
        "Datacenter/Cluster1/esxi-01.example.com?no_verify=1"
    )


def test_merge_nested_dict_applies_vcenter_settings():
    params = {
        "vcenter": {
            "hostname": "vcenter.example.com",
            "username": "user",
            "datacenter": "Datacenter",
            "compute_path": "Cluster1/esxi-01.example.com",
        },
        "vcenter_hostname": None,
        "vcenter_username": None,
        "datacenter": None,
        "compute_path": None,
    }
    virt_v2v._merge_nested_dict(params, "vcenter", virt_v2v.NESTED_VCENTER_MAP)
    assert params["vcenter_hostname"] == "vcenter.example.com"
    assert params["compute_path"] == "Cluster1/esxi-01.example.com"


def test_flat_params_override_nested_dict():
    params = {
        "vcenter": {"hostname": "nested.example.com"},
        "vcenter_hostname": "flat.example.com",
    }
    virt_v2v._merge_nested_dict(params, "vcenter", virt_v2v.NESTED_VCENTER_MAP)
    assert params["vcenter_hostname"] == "flat.example.com"


def test_merge_nested_overrides_defaults():
    params = {
        "libvirt": {"pool": "ceph_vms"},
        "libvirt_pool": "vms",
    }
    virt_v2v._merge_nested_dict(params, "libvirt", virt_v2v.NESTED_LIBVIRT_MAP)
    assert params["libvirt_pool"] == "ceph_vms"


def test_merge_nested_does_not_override_explicit_flat_value():
    params = {
        "libvirt": {"pool": "ceph_vms"},
        "libvirt_pool": "custom_pool",
    }
    virt_v2v._merge_nested_dict(params, "libvirt", virt_v2v.NESTED_LIBVIRT_MAP)
    assert params["libvirt_pool"] == "custom_pool"


def test_main_skips_existing_domain(mocker):
    module = mocker.Mock()
    module.params = {
        "name": "app-server-01",
        "state": "present",
        "libvirt_uri": "qemu:///system",
        "virt_v2v_path": "virt-v2v",
        "force": False,
    }
    mocker.patch("ansible_collections.anande.vmware_v2v.plugins.modules.virt_v2v.shutil.which", return_value="/usr/bin/virt-v2v")
    module.run_command.return_value = (0, "", "")

    result = virt_v2v._virt_v2v_present(module)

    assert result["changed"] is False
    assert result["skipped"] is True
    module.run_command.assert_called_once_with(
        ["virsh", "-c", "qemu:///system", "dominfo", "app-server-01"],
        check_rc=False,
    )
