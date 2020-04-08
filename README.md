## Router deployment for Banana PI R64

It is assumed that [Armbian](https://github.com/muravjov/armbian-build) is used as underlying operating system.
Ansible is to run from non-root user with root rights via `sudo`, e.g. with name `sa`.

```
# router
ansible-playbook ./router.py -l hm-bananapi-1

# vpn
ansible-playbook ./router.py -l current-vpn

# monitoring
ansible-playbook ./monitoring.py
```
