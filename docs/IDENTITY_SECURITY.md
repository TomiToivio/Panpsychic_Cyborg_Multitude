# PCM identity key security

PCM node identity is rooted in an Ed25519 private key stored at:

```text
<rhizome-dir>/identity/pcm_identity.json
```

This file contains `secret_seed_b64`, the raw 32-byte Ed25519 secret seed encoded as base64. Anyone who obtains that seed can impersonate the node, sign PCM envelopes as its DID, and potentially exercise capabilities granted to that identity.

## Filesystem protections

On POSIX systems PCM creates:

- the `identity/` directory with mode `0700`;
- `pcm_identity.json` with mode `0600`.

Identity writes use a private temporary file created atomically in the same directory and then `os.replace()` it into place. The secret seed is therefore never intentionally written first through a broadly readable default-mode file.

When loading an older identity file, PCM emits a `RuntimeWarning` if group or other permission bits are present. Existing identities remain loadable so upgrades do not unexpectedly strand a node, but operators should correct the permissions immediately, for example:

```bash
chmod 700 <rhizome-dir>/identity
chmod 600 <rhizome-dir>/identity/pcm_identity.json
```

Windows does not expose POSIX mode-bit semantics in the same way. Use the operating system's account and ACL controls to ensure that only the intended user or service account can read the identity file.

## Backup and recovery

Treat `pcm_identity.json` as cryptographic key material, not ordinary application data.

- Back it up only to storage with access controls at least as restrictive as the original.
- Do not put it in Git, shared folders, tickets, chat messages, telemetry, or event logs.
- Encrypt off-host backups where practical.
- Losing the file means losing the node's current signing identity.
- Leaking the file means the identity must be considered compromised.

The public DID can be shared freely. The `secret_seed_b64` value cannot.

## Rotation

`generate_identity(..., force=True)` replaces the current key and DID. This is useful for local resets, but it is not by itself a complete trust-preserving rotation mechanism because peers may still recognize or authorize the previous DID. Protocol-level successor credentials remain the appropriate mechanism for durable identity rotation.
