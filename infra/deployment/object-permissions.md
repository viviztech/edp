# Private object and key permissions

Files remain disabled in the initial staging topology. Enable them only after the
separate collection, retention, scanner and storage acceptance gates. Map these
implemented operations to the chosen S3-compatible provider; these are capabilities,
not an invented provider policy document.

| Identity | Allowed | Denied |
| --- | --- | --- |
| API private-file adapter | Put object with configured encryption; head/get the exact version beneath the application-owned private prefix | Public ACLs, bucket policy changes, listing unrelated prefixes, unversioned evidence substitution |
| Worker scanner | Head/get exact private object versions; encrypted temporary bytes in private bounded process storage | Public access, unrelated prefixes, key policy changes |
| Worker disposal | Delete the specifically authorized object version after current retention/hold checks | Bucket deletion, lifecycle changes, deleting held/frozen versions |
| Backup/recovery operator | Separate restricted inventory and recovery access to all retained referenced versions and required decryption key references | Public access, silent mutation of pinned evidence or production restore during a drill |
| Browser/mobile/web | Domain API gateways only | Object-store credentials, bucket access, KMS access |

KMS use is restricted to the selected encryption context/bucket and the minimum
encrypt/decrypt/data-key operations required by the actual provider. Keys have
independent custody and audited rotation. Preserve old decrypt keys while retained
objects or backups reference them. Deny public bucket access and ACLs, require TLS
and encryption, enable versioning, and preserve versions referenced by immutable
application evidence. Lifecycle expiration cannot override legal holds or the
application's retained evidence. No wildcard provider credentials or live account
policy is created by this repository.
