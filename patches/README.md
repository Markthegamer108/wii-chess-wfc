# Patch file

The converter expects `wii_chess_europe.ips` in this directory. That IPS is intentionally not distributed with this source because it contains replacement game code. Obtain an authorized copy separately if you are entitled to use it.

The converter checks the file's SHA-256 before use. It must be:

```text
42791c7093e26943b1e02c436c891acb78e2722133725de2fc5857f7182e927a
```

Without the file, the app and build script stop with an explicit error. Do not put a game image or executable in this repository.
