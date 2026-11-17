# Updater setup

1. Use a private GitHub release repository by default. The source repository may also host its own releases.
2. Generate a dedicated Ed25519 key pair in a trusted environment. Export the 32-byte raw private key and 32-byte raw public key separately in Base64. Store the private value only in a secure backup and the protected GitHub environment secret `PDF_TOOLBOX_SIGNING_KEY`.
3. Set the repository variables `PDF_TOOLBOX_UPDATE_PUBLIC_KEY` and `PDF_TOOLBOX_RELEASE_REPOSITORY`. The release repository defaults to the source repository. Set `PDF_TOOLBOX_RELEASE_PRIVATE=false` only for an authorized public distribution repository.
4. On a separate release repo, configure a narrowly scoped write credential as `PDF_TOOLBOX_RELEASE_TOKEN` in the protected release environment. Same-repo publication uses the workflow token. Enable `PDF_TOOLBOX_PUBLISH=true` only when ready to authorize automatic releases.
5. In each private installation, open Settings and store a fine-grained read-only token scoped to Contents on the release repository. Windows Credential Manager stores the token for that Windows user. To replace it, enter the new token. An empty entry removes it.
6. In Settings, run a manual update check and choose whether to enable background checks. A local unconfigured build can be upgraded by running an installer acquired through an authorized distribution channel.

Set `PDF_TOOLBOX_REQUIRE_AUTHENTICODE=true` for builds that require Windows publisher verification. Authenticode-sign the installer before manifest signing. The app uses the local Windows trust cache for the publisher check.

To rotate verification keys, distribute a fresh installer carrying the new public key through an independent authorized channel. Verify its checksum and publisher separately. Protect the new key in the release environment, then sign subsequent releases with it. Suspend publishing immediately if a signing key is compromised.
