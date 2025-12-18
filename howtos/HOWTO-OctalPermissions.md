# Octal representation of permissions

As Ansible uses octal values for file permissions, you may want to look at current permissions by issuing:

```bash
stat -c "%a %n" *
```

Instead of the asterisk you may also specify a file or folder name
