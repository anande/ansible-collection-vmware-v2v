---
# Copy this template into a new discussion at:
# https://github.com/ansible-collections/ansible-inclusion/discussions/new?category=new-collection-reviews

title: "New collection: anande.vmware_v2v"

body: |
  - Ansible Galaxy: https://galaxy.ansible.com/anande/vmware_v2v
  - Source repo: https://github.com/anande/ansible-collection-vmware-v2v
  - Issues tracker: https://github.com/anande/ansible-collection-vmware-v2v/issues
  - GitHub handles: @anande
  - Is the collection part of Automation Hub: No
  - We meet [Collection Requirements](https://docs.ansible.com/ansible/devel/community/collection_contributors/collection_requirements.html): Yes

  ## Summary

  Ansible collection providing `virt_v2v` module to convert powered-off VMware guests
  to libvirt-managed KVM on RHEL conversion hosts with Red Hat Ceph RBD-backed storage pools.

  ## Checklist self-review

  - [x] Published on Ansible Galaxy (v1.0.0)
  - [x] Public GitHub repository with tagged releases
  - [x] Code of Conduct linked (Ansible community CoC)
  - [x] Public issue tracker
  - [x] `meta/runtime.yml` with `requires_ansible`
  - [x] Changelog (`changelogs/changelog.yaml`)
  - [x] CI with `ansible-test sanity` and unit tests
  - [x] Module documentation follows Ansible standards
  - [x] FQCN `anande.vmware_v2v.virt_v2v` used in examples
