# Security and privacy review

PDF processing uses local libraries. It does not instantiate a server or provide active PDF links, scripts or embedded executable actions in the viewer. File operations create a new destination and refuse collisions. Passphrases live in job or workspace references and are omitted from their string representations. File decoding uses resource limits for output images and editor image dimensions.

The isolated updater is opt-in, checks TLS, enforces an asset host allowlist, and keeps private credentials in Windows Credential Manager. Signed manifests and verified bytes are required before installer execution. Signatures authenticate the updater artifact relative to the configured public key. Authenticode can be applied during release packaging to supply Windows publisher trust.

PDF decoding uses a native PDFium wheel. Malformed and resource-intensive documents can still stress the native decoder, and cancellation takes effect between PDF engine operations. Keep the pinned library versions under review and verify clean Windows and real signed upgrade scenarios before stable distribution.
